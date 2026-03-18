"""Tests for jira_cache.embeddings module — 100% coverage target."""

import sqlite3
import struct
from unittest.mock import MagicMock, patch

import jira_cache.embeddings as emb_module
import pytest
from jira_cache.embeddings import (
    EmbeddingStore,
    _get_model,
    _load_sqlite_vec,
    _serialize_f32,
)

# --- _serialize_f32 ---


class TestSerializeF32:
    def test_basic(self):
        vec = [1.0, 2.0, 3.0]
        result = _serialize_f32(vec)
        assert isinstance(result, bytes)
        assert len(result) == 12  # 3 floats × 4 bytes
        unpacked = struct.unpack("3f", result)
        assert unpacked == (1.0, 2.0, 3.0)

    def test_empty(self):
        assert _serialize_f32([]) == b""


# --- _load_sqlite_vec ---


class TestLoadSqliteVec:
    def setup_method(self):
        """Reset global state before each test."""
        emb_module._vec_loaded = False

    def test_already_loaded(self):
        emb_module._vec_loaded = True
        conn = MagicMock()
        assert _load_sqlite_vec(conn) is True
        conn.enable_load_extension.assert_not_called()

    def test_import_error(self):
        with patch.dict("sys.modules", {"sqlite_vec": None}):
            conn = MagicMock()
            result = _load_sqlite_vec(conn)
            assert result is False

    def test_success(self):
        mock_vec = MagicMock()
        conn = MagicMock()
        with patch.dict("sys.modules", {"sqlite_vec": mock_vec}):
            result = _load_sqlite_vec(conn)
            assert result is True
            conn.enable_load_extension.assert_any_call(True)
            mock_vec.load.assert_called_once_with(conn)
            conn.enable_load_extension.assert_any_call(False)
            assert emb_module._vec_loaded is True

    def test_operational_error(self):
        mock_vec = MagicMock()
        mock_vec.load.side_effect = sqlite3.OperationalError("extension error")
        conn = MagicMock()
        with patch.dict("sys.modules", {"sqlite_vec": mock_vec}):
            result = _load_sqlite_vec(conn)
            assert result is False

    def teardown_method(self):
        emb_module._vec_loaded = False


# --- _get_model ---


class TestGetModel:
    def setup_method(self):
        emb_module._model = None

    def test_already_loaded(self):
        sentinel = object()
        emb_module._model = sentinel
        assert _get_model() is sentinel

    def test_loads_model(self):
        mock_model = MagicMock()
        mock_st_module = MagicMock()
        mock_st_module.SentenceTransformer.return_value = mock_model

        # Remove sentence_transformers from sys.modules so `from X import Y` re-imports
        with patch.dict("sys.modules", {"sentence_transformers": mock_st_module}):
            result = _get_model()
            mock_st_module.SentenceTransformer.assert_called_once_with("all-MiniLM-L6-v2")
            assert result is mock_model
            assert emb_module._model is mock_model

    def test_import_error(self):
        with patch.dict("sys.modules", {"sentence_transformers": None}), pytest.raises(ImportError):
            _get_model()

    def teardown_method(self):
        emb_module._model = None


# --- EmbeddingStore ---


class TestEmbeddingStoreInit:
    def test_not_available(self):
        conn = MagicMock()
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=False):
            store = EmbeddingStore(conn)
            assert store.available is False

    def test_available(self):
        conn = MagicMock()
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=True):
            store = EmbeddingStore(conn)
            assert store.available is True
            conn.executescript.assert_called_once()
            conn.commit.assert_called_once()

    def test_schema_already_exists(self):
        conn = MagicMock()
        conn.executescript.side_effect = sqlite3.OperationalError("table already exists")
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=True):
            store = EmbeddingStore(conn)
            # "already exists" should be silently ignored
            assert store.available is True

    def test_schema_other_error(self):
        conn = MagicMock()
        conn.executescript.side_effect = sqlite3.OperationalError("disk I/O error")
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=True):
            store = EmbeddingStore(conn)
            assert store.available is False


class TestGenerateEmbedding:
    def test_calls_model(self):
        conn = MagicMock()
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=True):
            store = EmbeddingStore(conn)

        mock_model = MagicMock()
        mock_result = MagicMock()
        mock_result.tolist.return_value = [0.1] * 384
        mock_model.encode.return_value = mock_result

        with patch("jira_cache.embeddings._get_model", return_value=mock_model):
            result = store.generate_embedding("test text")
            assert len(result) == 384
            mock_model.encode.assert_called_once_with("test text", normalize_embeddings=True)


class TestGenerateEmbeddingsBatch:
    def test_empty_list(self):
        conn = MagicMock()
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=True):
            store = EmbeddingStore(conn)
        assert store.generate_embeddings_batch([]) == []

    def test_batch_encode(self):
        conn = MagicMock()
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=True):
            store = EmbeddingStore(conn)

        mock_model = MagicMock()
        mock_e1 = MagicMock()
        mock_e1.tolist.return_value = [0.1] * 384
        mock_e2 = MagicMock()
        mock_e2.tolist.return_value = [0.2] * 384
        mock_model.encode.return_value = [mock_e1, mock_e2]

        with patch("jira_cache.embeddings._get_model", return_value=mock_model):
            result = store.generate_embeddings_batch(["a", "b"])
            assert len(result) == 2
            mock_model.encode.assert_called_once_with(["a", "b"], batch_size=32, normalize_embeddings=True)


class TestStoreEmbedding:
    def test_not_available(self):
        conn = MagicMock()
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=False):
            store = EmbeddingStore(conn)
        assert store.store_embedding("BEP-1", "text") is False

    def test_success(self):
        conn = MagicMock()
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=True):
            store = EmbeddingStore(conn)

        with patch.object(store, "generate_embedding", return_value=[0.1] * 384):
            result = store.store_embedding("BEP-1", "test text")
            assert result is True
            conn.execute.assert_called()
            conn.commit.assert_called()

    def test_error(self):
        conn = MagicMock()
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=True):
            store = EmbeddingStore(conn)

        with patch.object(store, "generate_embedding", side_effect=Exception("model error")):
            result = store.store_embedding("BEP-1", "text")
            assert result is False


class TestFindSimilar:
    def test_not_available(self):
        conn = MagicMock()
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=False):
            store = EmbeddingStore(conn)
        assert store.find_similar("query") == []

    def test_success(self):
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = [
            ("BEP-1", 0.1234),
            ("BEP-2", 0.5678),
        ]
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=True):
            store = EmbeddingStore(conn)

        with patch.object(store, "generate_embedding", return_value=[0.1] * 384):
            results = store.find_similar("test query", limit=5)
            assert len(results) == 2
            assert results[0]["issue_key"] == "BEP-1"
            assert results[0]["distance"] == 0.1234

    def test_with_excludes(self):
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = [
            ("BEP-1", 0.1),
            ("BEP-2", 0.2),
            ("BEP-3", 0.3),
        ]
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=True):
            store = EmbeddingStore(conn)

        with patch.object(store, "generate_embedding", return_value=[0.1] * 384):
            results = store.find_similar("test", exclude_keys=["BEP-2"])
            assert len(results) == 2
            keys = [r["issue_key"] for r in results]
            assert "BEP-2" not in keys

    def test_error(self):
        conn = MagicMock()
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=True):
            store = EmbeddingStore(conn)

        with patch.object(store, "generate_embedding", side_effect=Exception("fail")):
            assert store.find_similar("query") == []


class TestStoreBatch:
    def _make_store(self):
        conn = MagicMock()
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=True):
            store = EmbeddingStore(conn)
        return store, conn

    def test_not_available(self):
        conn = MagicMock()
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=False):
            store = EmbeddingStore(conn)
        assert store.store_batch([]) == 0

    def test_empty_issues(self):
        store, conn = self._make_store()
        assert store.store_batch([]) == 0

    def test_issues_with_no_key(self):
        store, conn = self._make_store()
        assert store.store_batch([{"fields": {"summary": "test"}}]) == 0

    def test_success_with_adf(self):
        store, conn = self._make_store()
        issues = [
            {
                "key": "BEP-1",
                "fields": {
                    "summary": "Test issue",
                    "description": {
                        "type": "doc",
                        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "desc"}]}],
                    },
                },
            }
        ]
        with patch.object(store, "generate_embeddings_batch", return_value=[[0.1] * 384]):
            result = store.store_batch(issues)
            assert result == 1
            conn.commit.assert_called()

    def test_success_with_string_description(self):
        store, conn = self._make_store()
        issues = [{"key": "BEP-1", "fields": {"summary": "Test", "description": "plain text"}}]
        with patch.object(store, "generate_embeddings_batch", return_value=[[0.1] * 384]):
            result = store.store_batch(issues)
            assert result == 1

    def test_encode_error(self):
        store, conn = self._make_store()
        issues = [{"key": "BEP-1", "fields": {"summary": "Test"}}]
        with patch.object(store, "generate_embeddings_batch", side_effect=Exception("fail")):
            assert store.store_batch(issues) == 0

    def test_store_error(self):
        store, conn = self._make_store()
        issues = [{"key": "BEP-1", "fields": {"summary": "Test"}}]
        conn.execute.side_effect = Exception("db error")
        with patch.object(store, "generate_embeddings_batch", return_value=[[0.1] * 384]):
            result = store.store_batch(issues)
            assert result == 0


class TestRemoveEmbedding:
    def test_not_available(self):
        conn = MagicMock()
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=False):
            store = EmbeddingStore(conn)
        assert store.remove_embedding("BEP-1") is False

    def test_success(self):
        conn = MagicMock()
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=True):
            store = EmbeddingStore(conn)
        assert store.remove_embedding("BEP-1") is True
        conn.execute.assert_called()

    def test_error(self):
        conn = MagicMock()
        conn.execute.side_effect = Exception("fail")
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=True):
            store = EmbeddingStore(conn)
        assert store.remove_embedding("BEP-1") is False


class TestCount:
    def test_not_available(self):
        conn = MagicMock()
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=False):
            store = EmbeddingStore(conn)
        assert store.count() == 0

    def test_success(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (42,)
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=True):
            store = EmbeddingStore(conn)
        assert store.count() == 42

    def test_none_row(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = None
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=True):
            store = EmbeddingStore(conn)
        assert store.count() == 0

    def test_error(self):
        conn = MagicMock()
        conn.execute.side_effect = Exception("fail")
        with patch("jira_cache.embeddings._load_sqlite_vec", return_value=True):
            store = EmbeddingStore(conn)
        assert store.count() == 0
