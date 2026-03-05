"""Fetch external URLs and save as markdown files."""

import re
from pathlib import Path
from urllib.parse import urlparse

import html2text
import requests

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def url_to_filename(url: str) -> str:
    """Convert a URL to a safe filename: reading_{domain}_{path-slug}.md"""
    parsed = urlparse(url)
    domain = parsed.netloc.lstrip("www.")
    path = re.sub(r"[^a-zA-Z0-9]+", "-", parsed.path.strip("/")).strip("-")
    name = f"{domain}_{path}" if path else domain
    name = name[:120]
    return f"reading_{name}.md"


def fetch_url_to_file(url: str, dest_path: Path) -> bool:
    """
    Fetch a URL and save its content as markdown to dest_path.

    Returns True on success (including cache hit), False on any error.
    """
    if dest_path.exists():
        return True

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=(5, 15))
        resp.raise_for_status()
    except requests.RequestException:
        return False

    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = True
    converter.body_width = 0

    markdown = converter.handle(resp.text).strip()
    if not markdown:
        return False

    dest_path.write_text(markdown, encoding="utf-8")
    return True
