"""H2-based Markdown section splitter with SHA256 hash-based change detection.

Usage:
    sections = split_sections(page_id, markdown_body)
    changed, removed = diff_sections(new_sections, old_sections_by_id)
"""
import hashlib
import re
from dataclasses import dataclass


@dataclass
class SectionData:
    section_id: str       # "{page_id}::{slug}"
    page_id: str
    heading: str          # Original heading text
    body_md: str          # Markdown body of this section
    content_hash: str     # SHA256 of body_md


_H2_RE = re.compile(r"^## (.+)$", re.MULTILINE)
_SLUG_RE = re.compile(r"[^a-z0-9\-]")


def _slugify(heading: str) -> str:
    return _SLUG_RE.sub("", heading.lower().replace(" ", "-"))


def split_sections(page_id: str, body_md: str) -> list[SectionData]:
    """Split Markdown body at H2 headings into SectionData records.

    Pages with no H2 headings return a single section with heading '_body'.
    Empty pages return an empty list.
    """
    if not body_md.strip():
        return []

    matches = list(_H2_RE.finditer(body_md))
    if not matches:
        content = body_md.strip()
        return [_make_section(page_id, "_body", content)]

    sections = []
    for i, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body_md)
        content = body_md[start:end].strip()
        sections.append(_make_section(page_id, heading, content))
    return sections


def _make_section(page_id: str, heading: str, body_md: str) -> SectionData:
    # Use literal "_body" for the sentinel heading to avoid collision with
    # a real "## Body" heading (slugify strips underscores: "_body" → "body").
    slug = heading if heading == "_body" else _slugify(heading)
    section_id = f"{page_id}::{slug}"
    content_hash = hashlib.sha256(body_md.encode()).hexdigest()
    return SectionData(
        section_id=section_id,
        page_id=page_id,
        heading=heading,
        body_md=body_md,
        content_hash=content_hash,
    )


def diff_sections(
    new_sections: list[SectionData],
    old_by_id: dict[str, SectionData],
) -> tuple[list[SectionData], list[str]]:
    """Compare new sections against stored sections.

    Returns:
        changed: Sections that are new or have a different content_hash.
        removed: section_ids present in old_by_id but not in new_sections.
    """
    new_by_id = {s.section_id: s for s in new_sections}
    changed = [
        s for s in new_sections
        if s.section_id not in old_by_id
        or old_by_id[s.section_id].content_hash != s.content_hash
    ]
    removed = [sid for sid in old_by_id if sid not in new_by_id]
    return changed, removed
