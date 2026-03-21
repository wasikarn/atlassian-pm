"""Tests for atlassian_cache.confluence_cache — 100% coverage."""
import pytest

from .conftest import make_page


class TestPutAndGetPage:
    def test_put_and_get_fresh(self, confluence_cache, sample_page):
        confluence_cache.put_page(sample_page)
        result = confluence_cache.get_page("12345", max_age_hours=24)
        assert result is not None
        assert result["id"] == "12345"
        assert result["title"] == "Test Page"

    def test_get_returns_none_when_stale(self, confluence_cache, sample_page):
        confluence_cache.put_page(sample_page)
        result = confluence_cache.get_page("12345", max_age_hours=-1)
        assert result is None

    def test_get_returns_none_when_not_cached(self, confluence_cache):
        assert confluence_cache.get_page("nonexistent", max_age_hours=24) is None

    def test_put_updates_existing(self, confluence_cache, sample_page):
        confluence_cache.put_page(sample_page)
        updated = make_page(page_id="12345", title="Updated Title", version_num=2)
        confluence_cache.put_page(updated)
        result = confluence_cache.get_page("12345", max_age_hours=24)
        assert result["title"] == "Updated Title"


class TestFtsSearch:
    def test_fts_finds_by_title(self, confluence_cache):
        confluence_cache.put_page(make_page(page_id="A", title="Sprint Planning Guide"))
        results = confluence_cache.fts_search("Sprint Planning", limit=5)
        assert any(r["page_id"] == "A" for r in results)

    def test_fts_returns_empty_when_no_match(self, confluence_cache):
        confluence_cache.put_page(make_page(page_id="B", title="Unrelated Page"))
        results = confluence_cache.fts_search("quantum physics", limit=5)
        assert results == []

    def test_fts_porter_stemming(self, confluence_cache):
        """Porter tokenizer: 'plan' should match 'planning'."""
        confluence_cache.put_page(make_page(page_id="C", title="Sprint Planning"))
        results = confluence_cache.fts_search("plan", limit=5)
        assert any(r["page_id"] == "C" for r in results)


class TestSectionStorage:
    def test_store_and_get_sections(self, confluence_cache, sample_page):
        from atlassian_cache.sections import split_sections
        confluence_cache.put_page(sample_page)
        sections = split_sections("12345", sample_page["_body_md"])
        confluence_cache.put_sections(sections)
        stored = confluence_cache.get_sections("12345")
        assert len(stored) == len(sections)

    def test_partial_invalidation_only_re_embeds_changed(self, confluence_cache):
        """put_sections replaces only changed sections."""
        from atlassian_cache.sections import split_sections, SectionData
        confluence_cache.put_page(make_page(page_id="D", body_md="## A\n\nSame.\n\n## B\n\nOld B.\n"))
        old_secs = split_sections("D", "## A\n\nSame.\n\n## B\n\nOld B.\n")
        confluence_cache.put_sections(old_secs)
        new_secs = split_sections("D", "## A\n\nSame.\n\n## B\n\nNew B.\n")
        changed, removed = confluence_cache.update_sections("D", new_secs)
        assert len(changed) == 1   # only B changed
        assert changed[0].heading == "B"
        assert len(removed) == 0


class TestInvalidate:
    def test_invalidate_removes_page(self, confluence_cache, sample_page):
        confluence_cache.put_page(sample_page)
        confluence_cache.invalidate("12345")
        assert confluence_cache.get_page("12345", max_age_hours=24) is None

    def test_invalidate_nonexistent_is_noop(self, confluence_cache):
        confluence_cache.invalidate("ghost")  # should not raise


class TestPutAndGetChildren:
    def test_put_children_stores_links(self, confluence_cache):
        """put_children stores parent→child links in confluence_links."""
        confluence_cache.put_page(make_page(page_id="parent", title="Parent"))
        confluence_cache.put_page(make_page(page_id="child1", title="Child 1"))
        confluence_cache.put_page(make_page(page_id="child2", title="Child 2"))
        confluence_cache.put_children("parent", [{"id": "child1"}, {"id": "child2"}])
        children = confluence_cache.get_children("parent")
        assert len(children) == 2
        ids = {c["page_id"] for c in children}
        assert ids == {"child1", "child2"}

    def test_put_children_replaces_existing(self, confluence_cache):
        """put_children replaces previous child links for the same parent."""
        confluence_cache.put_page(make_page(page_id="parent", title="Parent"))
        confluence_cache.put_page(make_page(page_id="old", title="Old Child"))
        confluence_cache.put_page(make_page(page_id="new", title="New Child"))
        confluence_cache.put_children("parent", [{"id": "old"}])
        confluence_cache.put_children("parent", [{"id": "new"}])
        children = confluence_cache.get_children("parent")
        assert len(children) == 1
        assert children[0]["page_id"] == "new"

    def test_put_children_skips_missing_id(self, confluence_cache):
        """put_children skips child dicts with no 'id' key."""
        confluence_cache.put_page(make_page(page_id="parent", title="Parent"))
        confluence_cache.put_page(make_page(page_id="valid", title="Valid"))
        confluence_cache.put_children("parent", [{"id": "valid"}, {"title": "no id here"}])
        children = confluence_cache.get_children("parent")
        assert len(children) == 1

    def test_get_children_returns_empty_when_none(self, confluence_cache):
        assert confluence_cache.get_children("nonexistent") == []


class TestGetAllPages:
    def test_returns_empty_when_no_pages(self, confluence_cache):
        assert confluence_cache.get_all_pages() == []

    def test_returns_page_metadata(self, confluence_cache):
        from tests.conftest import make_page
        confluence_cache.put_page(make_page(page_id="111", title="Coupon Design", labels=["design", "coupon"]))
        confluence_cache.put_page(make_page(page_id="222", title="Sprint Planning"))
        pages = confluence_cache.get_all_pages()
        assert len(pages) == 2
        ids = {p["page_id"] for p in pages}
        assert "111" in ids and "222" in ids

    def test_returns_labels_as_list(self, confluence_cache):
        from tests.conftest import make_page
        confluence_cache.put_page(make_page(page_id="333", title="Tagged Page", labels=["api", "backend"]))
        pages = confluence_cache.get_all_pages()
        page = next(p for p in pages if p["page_id"] == "333")
        assert isinstance(page["labels"], list)
        assert "api" in page["labels"]
        assert "backend" in page["labels"]

    def test_handles_null_labels(self, confluence_cache):
        from tests.conftest import make_page
        confluence_cache.put_page(make_page(page_id="444", title="No Labels"))
        pages = confluence_cache.get_all_pages()
        page = next(p for p in pages if p["page_id"] == "444")
        assert page["labels"] == []


class TestBodyTruncation:
    def test_confluence_body_truncated_at_500kb(self, confluence_cache):
        """put_page truncates body_md to 500KB to prevent DB bloat."""
        large_body = "## Section\n\n" + "x" * 600_000
        page = make_page(page_id="BIG", body_md=large_body)
        confluence_cache.put_page(page)
        result = confluence_cache.get_page("BIG", max_age_hours=24)
        assert len(result["body_md"]) <= 512_000  # 500KB max
