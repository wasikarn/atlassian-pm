"""Content conversion utilities for Confluence.

This module provides content transformation functions:
- Markdown to Confluence storage format conversion
- Code block macro creation
- HTML code block fixing
- Inline markdown element conversion

Usage:
    from lib.converters import markdown_to_storage, create_code_macro, fix_code_blocks

    storage_html = markdown_to_storage("# Hello\\nThis is **bold**")
    macro = create_code_macro("python", "print('hello')")
    fixed = fix_code_blocks(html_content)
"""

import html
import logging
import re

from .exceptions import ContentConversionError

logger = logging.getLogger(__name__)

# Language aliases for code blocks
LANGUAGE_ALIASES: dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "sh": "bash",
    "shell": "bash",
    "yml": "yaml",
    "": "text",
}


def create_code_macro(language: str, content: str) -> str:
    """Create Confluence code macro in storage format.

    Args:
        language: Programming language for syntax highlighting.
        content: Code content to embed.

    Returns:
        Confluence storage format XML for code macro.

    Example:
        >>> create_code_macro("python", "print('hello')")
        '<ac:structured-macro ac:name="code" ac:schema-version="1">...'
    """
    # Normalize language alias
    normalized_lang = LANGUAGE_ALIASES.get(language, language)
    logger.debug("Creating code macro with language: %s", normalized_lang)

    return f"""<ac:structured-macro ac:name="code" ac:schema-version="1">
<ac:parameter ac:name="language">{normalized_lang}</ac:parameter>
<ac:plain-text-body><![CDATA[{content}]]></ac:plain-text-body>
</ac:structured-macro>"""


def convert_inline(text: str) -> str:
    """Convert inline markdown elements to HTML.

    Handles:
    - Bold: **text** -> <strong>text</strong>
    - Italic: *text* -> <em>text</em>
    - Inline code: `code` -> <code>code</code>
    - Links: [text](url) -> <a href="url">text</a>

    Args:
        text: Text containing inline markdown elements.

    Returns:
        Text with markdown converted to HTML.
    """
    # Bold **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)

    # Italic *text* (but not inside **)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)

    # Inline code `code`
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    # Links [text](url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)

    return text


def _create_table(rows: list[str]) -> str:
    """Create HTML table from markdown table rows.

    Args:
        rows: List of markdown table row strings (e.g., "| cell1 | cell2 |").

    Returns:
        HTML table string.
    """
    if not rows:
        return ""

    result = ["<table>"]

    for idx, row in enumerate(rows):
        cells = [c.strip() for c in row.split("|")[1:-1]]  # Remove empty first/last

        result.append("<tr>")
        for cell in cells:
            tag = "th" if idx == 0 else "td"
            cell_content = convert_inline(cell)
            result.append(f"<{tag}>{cell_content}</{tag}>")
        result.append("</tr>")

    result.append("</table>")
    return "\n".join(result)


def markdown_to_storage(markdown_content: str) -> str:
    """Convert markdown to Confluence storage format.

    Handles:
    - Headings (# ## ###)
    - Bold (**text**)
    - Italic (*text*)
    - Code blocks (```language)
    - Inline code (`code`)
    - Links [text](url)
    - Lists (- item)
    - Horizontal rules (---)
    - Tables
    - Blockquotes (>)

    Args:
        markdown_content: Markdown text to convert.

    Returns:
        Confluence storage format HTML.

    Raises:
        ContentConversionError: If conversion fails.

    Example:
        >>> markdown_to_storage("# Hello\\n**Bold** text")
        '<h1>Hello</h1>\\n<p><strong>Bold</strong> text</p>'
    """
    logger.debug("Converting markdown to storage format (%d chars)", len(markdown_content))

    try:
        lines = markdown_content.split("\n")
        result: list[str] = []
        in_code_block = False
        code_language = "text"
        code_content: list[str] = []
        in_list = False
        in_table = False
        table_rows: list[str] = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # Code block start/end
            if line.startswith("```"):
                if not in_code_block:
                    # Start code block
                    in_code_block = True
                    code_language = line[3:].strip() or "text"
                    code_content = []
                else:
                    # End code block
                    in_code_block = False
                    code_text = "\n".join(code_content)
                    result.append(create_code_macro(code_language, code_text))
                i += 1
                continue

            if in_code_block:
                code_content.append(line)
                i += 1
                continue

            # Table handling
            if "|" in line and line.strip().startswith("|"):
                if not in_table:
                    in_table = True
                    table_rows = []
                # Skip separator row (|---|---|)
                if re.match(r"^\|[\s\-:|]+\|$", line.strip()):
                    i += 1
                    continue
                table_rows.append(line)
                i += 1
                continue
            elif in_table:
                # End of table
                in_table = False
                result.append(_create_table(table_rows))
                table_rows = []
                # Don't increment i, process this line normally

            # Empty line
            if not line.strip():
                if in_list:
                    in_list = False
                    result.append("</ul>")
                result.append("")
                i += 1
                continue

            # Horizontal rule
            if line.strip() in ["---", "***", "___"]:
                if in_list:
                    in_list = False
                    result.append("</ul>")
                result.append("<hr/>")
                i += 1
                continue

            # Headings
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                if in_list:
                    in_list = False
                    result.append("</ul>")
                level = len(heading_match.group(1))
                text = convert_inline(heading_match.group(2))
                result.append(f"<h{level}>{text}</h{level}>")
                i += 1
                continue

            # Blockquote
            if line.startswith(">"):
                if in_list:
                    in_list = False
                    result.append("</ul>")
                quote_text = convert_inline(line[1:].strip())
                result.append(f"<blockquote><p>{quote_text}</p></blockquote>")
                i += 1
                continue

            # Unordered list
            list_match = re.match(r"^[\-\*]\s+(.+)$", line)
            if list_match:
                if not in_list:
                    in_list = True
                    result.append("<ul>")
                text = convert_inline(list_match.group(1))
                result.append(f"<li>{text}</li>")
                i += 1
                continue

            # Ordered list
            ordered_match = re.match(r"^\d+\.\s+(.+)$", line)
            if ordered_match:
                # For simplicity, treat as unordered
                if not in_list:
                    in_list = True
                    result.append("<ul>")
                text = convert_inline(ordered_match.group(1))
                result.append(f"<li>{text}</li>")
                i += 1
                continue

            # Regular paragraph
            if in_list:
                in_list = False
                result.append("</ul>")

            text = convert_inline(line)
            if text.strip():
                result.append(f"<p>{text}</p>")

            i += 1

        # Close any open elements
        if in_list:
            result.append("</ul>")
        if in_table and table_rows:
            result.append(_create_table(table_rows))

        storage_content = "\n".join(result)
        logger.debug("Conversion complete: %d chars output", len(storage_content))
        return storage_content

    except Exception as e:
        logger.error("Markdown conversion failed: %s", e)
        raise ContentConversionError(f"Failed to convert markdown: {e}") from e


def fix_code_blocks(content: str) -> str:
    """Fix HTML code blocks to Confluence macro format.

    Converts:
        <pre class="highlight"><code class="language-xxx">...</code></pre>
    To:
        <ac:structured-macro ac:name="code">...</ac:structured-macro>

    Args:
        content: HTML content with code blocks to fix.

    Returns:
        Content with code blocks converted to Confluence macros.

    Example:
        >>> content = '<pre class="highlight"><code class="language-python">print("hi")</code></pre>'
        >>> fix_code_blocks(content)
        '<ac:structured-macro ac:name="code" ac:schema-version="1">...'
    """

    def replace_code_block(match: re.Match[str]) -> str:
        lang_class = match.group(1) or ""
        code_content = match.group(2)

        # Extract language from class
        lang_match = re.search(r"language-(\w+)", lang_class)
        language = lang_match.group(1) if lang_match else "text"

        # Unescape HTML entities in code
        code_content = html.unescape(code_content)

        return create_code_macro(language, code_content)

    # Pattern to match <pre class="highlight"><code class="language-xxx">...</code></pre>
    pattern = r'<pre class="highlight"><code(?: class="([^"]*)")?>(.*?)</code></pre>'

    original_count = len(re.findall(pattern, content, flags=re.DOTALL))
    fixed_content = re.sub(pattern, replace_code_block, content, flags=re.DOTALL)

    if original_count > 0:
        logger.info("Fixed %d code blocks", original_count)
    else:
        logger.debug("No code blocks needed fixing")

    return fixed_content
