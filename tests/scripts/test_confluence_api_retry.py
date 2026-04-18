"""Tests for ConfluenceAPI 409 version-conflict retry logic (lib/api.py)."""
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from lib.api import ConfluenceAPI
from lib.exceptions import APIError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_api(retry_on_conflict: bool = True) -> ConfluenceAPI:
    return ConfluenceAPI(
        base_url="https://example.atlassian.net/wiki",
        auth_header="Basic dXNlcjp0b2tlbg==",
        ssl_context=None,
        retry_on_conflict=retry_on_conflict,
    )


def _http_error(status: int, reason: str = "Conflict", body: str = "") -> urllib.error.HTTPError:
    err = urllib.error.HTTPError(
        url="https://example.atlassian.net/wiki/rest/api/content/123",
        code=status,
        msg=reason,
        hdrs=MagicMock(),  # type: ignore[arg-type]
        fp=None,
    )
    return err


# ---------------------------------------------------------------------------
# test_update_page_retries_on_409
# ---------------------------------------------------------------------------

class TestUpdatePageRetriesOn409:
    """Mock API returns 409 then 200 — assert retry happened."""

    def test_retry_fetches_current_version_and_succeeds(self) -> None:
        api = _make_api(retry_on_conflict=True)

        # First PUT → 409 conflict
        # get_page (re-fetch) → version 5
        # Second PUT → 200 success
        current_page_response = {
            "id": "123",
            "title": "My Page",
            "version": {"number": 5},
            "body": {"storage": {"value": "<p>old</p>"}},
            "type": "page",
            "space": {},
            "ancestors": [],
        }
        success_response = {
            "id": "123",
            "title": "My Page",
            "version": {"number": 6},
            "body": {"storage": {"value": "<p>new</p>"}},
            "type": "page",
            "space": {},
            "ancestors": [],
        }

        put_call_count = 0

        def mock_request(method: str, endpoint: str, data=None):
            nonlocal put_call_count
            if method == "GET":
                return current_page_response
            if method == "PUT":
                put_call_count += 1
                if put_call_count == 1:
                    raise APIError(409, "Conflict", "version conflict")
                return success_response
            raise AssertionError(f"Unexpected method: {method}")

        with patch.object(api, "_request", side_effect=mock_request):
            result = api.update_page("123", "My Page", "<p>new</p>", version=3)

        assert result["version"]["number"] == 6
        assert put_call_count == 2, "Expected exactly 2 PUT calls (initial + retry)"

    def test_retry_uses_current_version_plus_one(self) -> None:
        """Retry payload must use current_version + 1, not stale_version + 1."""
        api = _make_api(retry_on_conflict=True)

        captured_versions: list[int] = []

        current_page_response = {
            "id": "123",
            "title": "My Page",
            "version": {"number": 10},
            "body": {"storage": {"value": ""}},
            "type": "page",
            "space": {},
            "ancestors": [],
        }
        success_response = {
            "id": "123",
            "title": "My Page",
            "version": {"number": 11},
            "type": "page",
            "space": {},
            "ancestors": [],
        }

        put_call_count = 0

        def mock_request(method, endpoint, data=None):
            nonlocal put_call_count
            if method == "GET":
                return current_page_response
            if method == "PUT":
                put_call_count += 1
                captured_versions.append(data["version"]["number"])
                if put_call_count == 1:
                    raise APIError(409, "Conflict", "")
                return success_response
            raise AssertionError(f"Unexpected: {method}")

        with patch.object(api, "_request", side_effect=mock_request):
            api.update_page("123", "My Page", "<p>x</p>", version=3)

        assert captured_versions[1] == 11, (
            f"Retry should use current(10)+1=11, got {captured_versions[1]}"
        )


# ---------------------------------------------------------------------------
# test_update_page_raises_after_second_409
# ---------------------------------------------------------------------------

class TestUpdatePageRaisesAfterSecondConflict:
    """Mock returns 409 twice — assert final exception with version context."""

    def test_raises_api_error_with_version_info(self) -> None:
        api = _make_api(retry_on_conflict=True)

        current_page_response = {
            "id": "123",
            "title": "My Page",
            "version": {"number": 7},
            "body": {"storage": {"value": ""}},
            "type": "page",
            "space": {},
            "ancestors": [],
        }

        def mock_request(method, endpoint, data=None):
            if method == "GET":
                return current_page_response
            if method == "PUT":
                raise APIError(409, "Conflict", "still conflicted")
            raise AssertionError(f"Unexpected: {method}")

        with patch.object(api, "_request", side_effect=mock_request), pytest.raises(APIError) as exc_info:
            api.update_page("123", "My Page", "<p>x</p>", version=3)

        err = exc_info.value
        assert err.status_code == 409
        # Details must contain both stale and current version numbers
        assert "3" in err.details, "Stale version (3) should appear in error details"
        assert "7" in err.details, "Current version (7) should appear in error details"


# ---------------------------------------------------------------------------
# test_update_page_no_retry_when_flag_disabled
# ---------------------------------------------------------------------------

class TestUpdatePageNoRetryWhenFlagDisabled:
    """retry_on_conflict=False — 409 raises immediately without GET re-fetch."""

    def test_raises_immediately_on_409(self) -> None:
        api = _make_api(retry_on_conflict=False)

        get_called = False

        def mock_request(method, endpoint, data=None):
            nonlocal get_called
            if method == "GET":
                get_called = True
                return {}
            if method == "PUT":
                raise APIError(409, "Conflict", "version mismatch")
            raise AssertionError(f"Unexpected: {method}")

        with patch.object(api, "_request", side_effect=mock_request), pytest.raises(APIError) as exc_info:
            api.update_page("123", "My Page", "<p>x</p>", version=2)

        assert exc_info.value.status_code == 409
        assert not get_called, "GET (re-fetch) must NOT be called when retry_on_conflict=False"

    def test_non_409_errors_propagate_regardless_of_flag(self) -> None:
        """Non-409 errors are always re-raised, even with retry_on_conflict=True."""
        api = _make_api(retry_on_conflict=True)

        def mock_request(method, endpoint, data=None):
            if method == "PUT":
                raise APIError(500, "Internal Server Error", "boom")
            raise AssertionError(f"Unexpected: {method}")

        with patch.object(api, "_request", side_effect=mock_request), pytest.raises(APIError) as exc_info:
            api.update_page("123", "My Page", "<p>x</p>", version=1)

        assert exc_info.value.status_code == 500
