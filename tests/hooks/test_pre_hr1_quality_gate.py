"""Tests for pre_hr1_quality_gate.py — HR1 quality gate before Jira writes."""
import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks" / "plugin" / "guards"))
import pre_hr1_quality_gate


def _run(tool_input: dict, tool_name: str = "Bash") -> dict | None:
    """Run main() with given input. Returns {} on allow, None on block (SystemExit)."""
    data = {"tool_name": tool_name, "tool_input": tool_input, "session_id": "test"}
    buf = io.StringIO()
    with (
        patch("sys.stdin.read", return_value=json.dumps(data)),
        redirect_stdout(buf),
    ):
        try:
            pre_hr1_quality_gate.main()
            raw = buf.getvalue().strip()
            return json.loads(raw) if raw else {}
        except SystemExit:
            return None  # blocked


def _make_passing_report():
    """Create a mock validation report that passes QG."""
    report = SimpleNamespace(score=95.0, passed=True, checks=[])
    return report


def _make_failing_report(score: float = 70.0):
    """Create a mock validation report that fails QG."""
    check = SimpleNamespace(
        check_id="C01",
        message="Missing acceptance criteria",
        status=SimpleNamespace(value="fail"),
    )
    return SimpleNamespace(score=score, passed=False, checks=[check])


# ── Non-matching cases (should always allow) ──────────────────────────────


def test_allows_non_bash_tool():
    """Non-Bash tools are not intercepted."""
    result = _run({"command": "acli jira workitem create --from-json /tmp/x.json"}, tool_name="Read")
    assert result == {}


def test_allows_non_acli_command():
    """Commands that are not acli write commands are passed through."""
    result = _run({"command": "git status"})
    assert result == {}


def test_allows_acli_list_command():
    """acli commands without --from-json are not intercepted."""
    result = _run({"command": "acli jira workitem list"})
    assert result == {}


def test_allows_on_empty_input():
    """Missing command field → allow."""
    result = _run({})
    assert result == {}


def test_allows_when_file_not_found():
    """File referenced in command does not exist → allow (let acli handle)."""
    result = _run({"command": "acli jira workitem create --from-json /nonexistent/path.json"})
    assert result == {}


# ── File-based tests using tempfiles ─────────────────────────────────────


def test_allows_when_json_is_invalid():
    """Malformed JSON file → allow (let acli handle)."""
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        f.write("not valid json {{{")
        tmp_path = f.name
    result = _run({"command": f"acli jira workitem create --from-json {tmp_path}"})
    assert result == {}


def test_allows_when_adf_not_detected():
    """JSON without ADF structure → allow (detect_format returns no adf)."""
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump({"some": "random", "data": 123}, f)
        tmp_path = f.name

    mock_detect = MagicMock(return_value=("unknown", None))
    with patch.dict("sys.modules", {"lib.adf_validator": MagicMock(
        AdfValidator=MagicMock(),
        detect_format=mock_detect,
    )}):
        result = _run({"command": f"acli jira workitem create --from-json {tmp_path}"})
    assert result == {}


def test_allows_when_validator_import_fails():
    """If AdfValidator cannot be imported → allow (graceful degradation)."""
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump({"type": "story", "description": {"version": 1, "type": "doc"}}, f)
        tmp_path = f.name

    # Simulate import failure by making sys.path not include scripts
    with patch.object(pre_hr1_quality_gate, "SCRIPTS_DIR", Path("/nonexistent")):
        result = _run({"command": f"acli jira workitem create --from-json {tmp_path}"})
    assert result == {}


def test_allows_when_qg_passes():
    """QG score >= 90 → allow."""
    with tempfile.NamedTemporaryFile(suffix="-story.json", mode="w", delete=False) as f:
        json.dump({"type": "Story", "description": {"version": 1, "type": "doc", "content": []}}, f)
        tmp_path = f.name

    mock_validator = MagicMock()
    mock_validator.return_value.validate.return_value = _make_passing_report()
    mock_detect = MagicMock(return_value=("create", {"version": 1, "type": "doc", "content": []}))

    mock_adf_module = MagicMock()
    mock_adf_module.AdfValidator = mock_validator
    mock_adf_module.detect_format = mock_detect

    with patch.dict("sys.modules", {"lib.adf_validator": mock_adf_module}):
        result = _run({"command": f"acli jira workitem create --from-json {tmp_path}"})
    assert result == {}


def test_blocks_when_qg_fails():
    """QG score < 90 → block (SystemExit 2)."""
    with tempfile.NamedTemporaryFile(suffix="-story.json", mode="w", delete=False) as f:
        json.dump({"type": "Story", "description": {"version": 1, "type": "doc", "content": []}}, f)
        tmp_path = f.name

    mock_validator = MagicMock()
    mock_validator.return_value.validate.return_value = _make_failing_report(score=65.0)
    mock_detect = MagicMock(return_value=("create", {"version": 1, "type": "doc", "content": []}))

    mock_adf_module = MagicMock()
    mock_adf_module.AdfValidator = mock_validator
    mock_adf_module.detect_format = mock_detect

    with patch.dict("sys.modules", {"lib.adf_validator": mock_adf_module}):
        result = _run({"command": f"acli jira workitem create --from-json {tmp_path}"})
    assert result is None  # blocked


def test_block_message_contains_score_and_filename():
    """Blocked message includes QG score and filename."""
    with tempfile.NamedTemporaryFile(suffix="-story.json", mode="w", delete=False) as f:
        json.dump({"type": "Story", "description": {"version": 1, "type": "doc", "content": []}}, f)
        tmp_path = f.name

    mock_validator = MagicMock()
    mock_validator.return_value.validate.return_value = _make_failing_report(score=72.5)
    mock_detect = MagicMock(return_value=("create", {"version": 1, "type": "doc", "content": []}))

    mock_adf_module = MagicMock()
    mock_adf_module.AdfValidator = mock_validator
    mock_adf_module.detect_format = mock_detect

    captured_stderr = io.StringIO()
    data = {
        "tool_name": "Bash",
        "tool_input": {"command": f"acli jira workitem edit --from-json {tmp_path}"},
        "session_id": "test",
    }
    with (
        patch("sys.stdin.read", return_value=json.dumps(data)),
        patch("sys.stderr", captured_stderr),
        patch.dict("sys.modules", {"lib.adf_validator": mock_adf_module}),
    ):
        try:
            pre_hr1_quality_gate.main()
        except SystemExit:
            pass

    err = captured_stderr.getvalue()
    assert "72.5" in err
    assert "HR1" in err


def test_allows_edit_command():
    """acli workitem edit --from-json is also intercepted."""
    with tempfile.NamedTemporaryFile(suffix="-story.json", mode="w", delete=False) as f:
        json.dump({"type": "Story", "description": {"version": 1, "type": "doc", "content": []}}, f)
        tmp_path = f.name

    mock_validator = MagicMock()
    mock_validator.return_value.validate.return_value = _make_passing_report()
    mock_detect = MagicMock(return_value=("edit", {"version": 1, "type": "doc", "content": []}))

    mock_adf_module = MagicMock()
    mock_adf_module.AdfValidator = mock_validator
    mock_adf_module.detect_format = mock_detect

    with patch.dict("sys.modules", {"lib.adf_validator": mock_adf_module}):
        result = _run({"command": f"acli jira workitem edit --from-json {tmp_path}"})
    assert result == {}
