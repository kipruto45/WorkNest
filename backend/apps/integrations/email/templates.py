from __future__ import annotations

import re
from html import unescape

from django.template.loader import render_to_string
from django.utils.html import strip_tags

from apps.integrations.email.base import RenderedEmailTemplate
from apps.integrations.email.exceptions import EmailTemplateRenderError


def render_email_template(*, template_name: str, context: dict) -> RenderedEmailTemplate:
    try:
        html_body = render_to_string(f"emails/{template_name}.html", context)
        text_body = _build_text_body_from_html(html_body)
    except Exception as exc:  # pragma: no cover
        raise EmailTemplateRenderError(f"Unable to render the '{template_name}' email template.") from exc

    return RenderedEmailTemplate(
        html_body=html_body,
        text_body=text_body.strip(),
    )


def _build_text_body_from_html(html_body: str) -> str:
    without_head = re.sub(r"<head\b.*?</head>", "", html_body, flags=re.IGNORECASE | re.DOTALL)
    without_style = re.sub(r"<style\b.*?</style>", "", without_head, flags=re.IGNORECASE | re.DOTALL)
    without_preheader = re.sub(
        r'<div[^>]*class="[^"]*\bpreheader\b[^"]*"[^>]*>.*?</div>',
        "",
        without_style,
        flags=re.IGNORECASE | re.DOTALL,
    )

    def anchor_replacer(match: re.Match) -> str:
        href = match.group("href").strip()
        label = strip_tags(match.group("label")).strip()
        if label and href:
            return f"{label}\n{href}"
        return label or href

    with_links = re.sub(
        r'<a[^>]*href=["\'](?P<href>[^"\']+)["\'][^>]*>(?P<label>.*?)</a>',
        anchor_replacer,
        without_preheader,
        flags=re.IGNORECASE | re.DOTALL,
    )
    with_breaks = re.sub(r"</(p|div|h1|h2|h3|li|tr|br)>", "\n", with_links, flags=re.IGNORECASE)
    collapsed = strip_tags(with_breaks)
    unescaped = unescape(collapsed)
    normalized_lines = [line.strip() for line in unescaped.splitlines()]
    meaningful_lines = [line for line in normalized_lines if line]
    return "\n".join(meaningful_lines)
