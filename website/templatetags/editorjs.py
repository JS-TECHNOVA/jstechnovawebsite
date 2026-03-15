import json
from html import escape

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def _parse_payload(value):
    if not value:
        return None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {"blocks": [{"type": "paragraph", "data": {"text": value}}]}
    return value if isinstance(value, dict) else None


def _render_list(items, ordered=False):
    tag = "ol" if ordered else "ul"
    rendered_items = []
    for item in items or []:
        if isinstance(item, dict):
            text = escape(str(item.get("content", "")))
        else:
            text = escape(str(item))
        rendered_items.append(f"<li>{text}</li>")
    return f"<{tag}>" + "".join(rendered_items) + f"</{tag}>"


def _render_checklist(items):
    rendered_items = []
    for item in items or []:
        text = escape(str((item or {}).get("text", "")))
        checked = bool((item or {}).get("checked"))
        marker = "&#10003;" if checked else "&#8212;"
        rendered_items.append(
            f'<li><span aria-hidden="true">{marker}</span> <span>{text}</span></li>'
        )
    return "<ul>" + "".join(rendered_items) + "</ul>"


def _render_table(rows):
    rendered_rows = []
    for row in rows or []:
        cells = "".join(f"<td>{escape(str(cell))}</td>" for cell in row or [])
        rendered_rows.append(f"<tr>{cells}</tr>")
    return "<table><tbody>" + "".join(rendered_rows) + "</tbody></table>"


def _render_block(block):
    block_type = (block or {}).get("type")
    data = (block or {}).get("data", {}) or {}

    if block_type == "header":
        level = data.get("level", 2)
        if not isinstance(level, int) or level < 1 or level > 6:
            level = 2
        text = escape(str(data.get("text", "")))
        return f"<h{level}>{text}</h{level}>"

    if block_type == "paragraph":
        text = escape(str(data.get("text", "")))
        return f"<p>{text}</p>"

    if block_type == "list":
        style = data.get("style", "unordered")
        return _render_list(data.get("items", []), ordered=style == "ordered")

    if block_type == "quote":
        text = escape(str(data.get("text", "")))
        caption = escape(str(data.get("caption", "")))
        if caption:
            return f"<blockquote><p>{text}</p><cite>{caption}</cite></blockquote>"
        return f"<blockquote><p>{text}</p></blockquote>"

    if block_type == "delimiter":
        return "<hr />"

    if block_type == "code":
        code = escape(str(data.get("code", "")))
        return f"<pre><code>{code}</code></pre>"

    if block_type == "checklist":
        return _render_checklist(data.get("items", []))

    if block_type == "table":
        return _render_table(data.get("content", []))

    if block_type == "image":
        file_data = data.get("file") or {}
        url = file_data.get("url") or data.get("url") or ""
        caption = escape(str(data.get("caption", "")))
        if not url:
            return ""
        safe_url = escape(str(url), quote=True)
        return f'<figure><img src="{safe_url}" alt="{caption}" /><figcaption>{caption}</figcaption></figure>'

    if block_type == "embed":
        service = escape(str(data.get("service", "embed")))
        source = escape(str(data.get("source", "")))
        if source:
            return f'<p><a href="{source}" target="_blank" rel="noopener">Embedded content ({service})</a></p>'
        return ""

    # Unknown block fallback
    text = escape(str(data.get("text", "")))
    return f"<p>{text}</p>" if text else ""


def render_editorjs_html(value):
    payload = _parse_payload(value)
    if not payload:
        return ""
    return "".join(_render_block(block) for block in payload.get("blocks", []))


def editorjs_to_text(value):
    payload = _parse_payload(value)
    if not payload:
        return ""

    lines = []
    for block in payload.get("blocks", []):
        block_type = (block or {}).get("type")
        data = (block or {}).get("data", {}) or {}

        if block_type in {"header", "paragraph", "quote"}:
            text = str(data.get("text", "")).strip()
            if text:
                lines.append(text)
            caption = str(data.get("caption", "")).strip()
            if block_type == "quote" and caption:
                lines.append(f"- {caption}")
        elif block_type == "list":
            for item in data.get("items", []):
                content = item.get("content") if isinstance(item, dict) else item
                content = str(content or "").strip()
                if content:
                    lines.append(f"- {content}")
        elif block_type == "checklist":
            for item in data.get("items", []):
                text = str((item or {}).get("text", "")).strip()
                if text:
                    lines.append(f"- {text}")
        elif block_type == "table":
            for row in data.get("content", []):
                values = [str(cell).strip() for cell in row or [] if str(cell).strip()]
                if values:
                    lines.append(" | ".join(values))
        elif block_type == "code":
            code = str(data.get("code", "")).strip()
            if code:
                lines.append(code)
        elif block_type == "image":
            caption = str(data.get("caption", "")).strip()
            if caption:
                lines.append(caption)
        elif block_type == "embed":
            source = str(data.get("source", "")).strip() or str(data.get("embed", "")).strip()
            if source:
                lines.append(source)

    return "\n\n".join(lines)


@register.filter(name="render_editorjs")
def render_editorjs(value):
    return mark_safe(render_editorjs_html(value))
