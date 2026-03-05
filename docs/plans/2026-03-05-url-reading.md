# URL Reading Support Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `--urls` flag to `generate_notes.py` that fetches external web pages, converts them to markdown, caches them in the session folder, and includes them as supplementary LLM context.

**Architecture:** New `src/url_fetcher.py` handles fetch + HTML→markdown conversion (requests + html2text). `generate_notes.py` gains a `--urls` flag; fetched files are saved to the session folder as `.md` files before `gather_supplementary_context()` runs, which is extended to also pick up `*.md` files.

**Tech Stack:** `requests` (already installed), `html2text` (new), `urllib.parse` (stdlib)

---

### Task 1: Add html2text dependency

**Files:**
- Modify: `requirements.txt`

**Step 1: Add html2text to requirements.txt**

In `requirements.txt`, add after the `openai` line in the Phase 3 block:

```
html2text>=2020.1.16
```

**Step 2: Install it**

```bash
pip install html2text
```

Expected: `Successfully installed html2text-...`

**Step 3: Verify import works**

```bash
python -c "import html2text; print(html2text.__version__)"
```

Expected: a version string printed, no error.

**Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add html2text dependency for URL-to-markdown conversion"
```

---

### Task 2: Create src/url_fetcher.py (TDD)

**Files:**
- Create: `tests/test_url_fetcher.py`
- Create: `src/url_fetcher.py`

**Step 1: Write the failing tests**

Create `tests/test_url_fetcher.py`:

```python
"""Tests for URL fetching and conversion module."""

import pytest
import requests as req
from pathlib import Path
from unittest.mock import patch, Mock

from src.url_fetcher import url_to_filename, fetch_url_to_file


class TestUrlToFilename:
    def test_ibm_article(self):
        url = "https://www.ibm.com/think/topics/olap-vs-oltp"
        result = url_to_filename(url)
        assert result.startswith("reading_")
        assert result.endswith(".md")
        assert "ibm" in result
        assert "olap" in result

    def test_strips_www(self):
        assert url_to_filename("https://www.example.com/article") == \
               url_to_filename("https://example.com/article")

    def test_simple_url(self):
        result = url_to_filename("https://example.com/article")
        assert result == "reading_example.com_article.md"

    def test_no_path(self):
        result = url_to_filename("https://example.com")
        assert result == "reading_example.com.md"

    def test_truncates_long_url(self):
        long_url = "https://example.com/" + "a" * 200
        result = url_to_filename(long_url)
        # reading_ (8) + name (<=120) + .md (3) = <=131
        assert len(result) <= 131

    def test_special_chars_replaced(self):
        result = url_to_filename("https://example.com/foo?bar=baz&x=1")
        assert " " not in result
        assert "?" not in result
        assert "=" not in result
        assert "&" not in result


class TestFetchUrlToFile:
    SAMPLE_HTML = "<html><body><h1>Hello World</h1><p>Some content here.</p></body></html>"

    def test_successful_fetch_writes_markdown(self, tmp_path):
        dest = tmp_path / "reading_test.md"
        mock_resp = Mock(text=self.SAMPLE_HTML)
        mock_resp.raise_for_status = Mock()

        with patch("requests.get", return_value=mock_resp):
            result = fetch_url_to_file("https://example.com", dest)

        assert result is True
        assert dest.exists()
        content = dest.read_text(encoding="utf-8")
        assert "Hello World" in content

    def test_cached_file_skips_network(self, tmp_path):
        dest = tmp_path / "reading_cached.md"
        dest.write_text("cached content", encoding="utf-8")

        with patch("requests.get") as mock_get:
            result = fetch_url_to_file("https://example.com", dest)

        assert result is True
        mock_get.assert_not_called()
        # cached content untouched
        assert dest.read_text(encoding="utf-8") == "cached content"

    def test_connection_error_returns_false(self, tmp_path):
        dest = tmp_path / "reading_fail.md"

        with patch("requests.get", side_effect=req.ConnectionError("offline")):
            result = fetch_url_to_file("https://example.com", dest)

        assert result is False
        assert not dest.exists()

    def test_http_error_returns_false(self, tmp_path):
        dest = tmp_path / "reading_404.md"
        mock_resp = Mock(text="")
        mock_resp.raise_for_status.side_effect = req.HTTPError("404 Not Found")

        with patch("requests.get", return_value=mock_resp):
            result = fetch_url_to_file("https://example.com/missing", dest)

        assert result is False
        assert not dest.exists()

    def test_empty_converted_content_returns_false(self, tmp_path):
        dest = tmp_path / "reading_empty.md"
        # HTML that produces empty markdown after conversion
        mock_resp = Mock(text="<html><body></body></html>")
        mock_resp.raise_for_status = Mock()

        with patch("requests.get", return_value=mock_resp):
            result = fetch_url_to_file("https://example.com/empty", dest)

        assert result is False
        assert not dest.exists()

    def test_timeout_returns_false(self, tmp_path):
        dest = tmp_path / "reading_timeout.md"

        with patch("requests.get", side_effect=req.Timeout("timed out")):
            result = fetch_url_to_file("https://example.com", dest)

        assert result is False
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_url_fetcher.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.url_fetcher'`

**Step 3: Implement src/url_fetcher.py**

Create `src/url_fetcher.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_url_fetcher.py -v
```

Expected: all tests PASS.

**Step 5: Commit**

```bash
git add src/url_fetcher.py tests/test_url_fetcher.py
git commit -m "feat: add url_fetcher module with fetch and filename utilities"
```

---

### Task 3: Extend gather_supplementary_context to handle .md files (TDD)

**Files:**
- Create: `tests/test_generate_notes.py`
- Modify: `generate_notes.py` (lines 85–113, the `gather_supplementary_context` function)

**Step 1: Write the failing test**

Create `tests/test_generate_notes.py`:

```python
"""Tests for generate_notes helper functions."""

import pytest
from pathlib import Path

from generate_notes import gather_supplementary_context


class TestGatherSupplementaryContext:
    def test_picks_up_md_file(self, tmp_path):
        md_file = tmp_path / "reading_ibm.com_olap-vs-oltp.md"
        md_file.write_text("# OLAP vs OLTP\nSome content.", encoding="utf-8")

        context, found = gather_supplementary_context(tmp_path)

        assert "reading_ibm.com_olap-vs-oltp.md" in found
        assert "READING: reading_ibm.com_olap-vs-oltp.md" in context
        assert "OLAP vs OLTP" in context

    def test_md_file_labelled_as_reading(self, tmp_path):
        (tmp_path / "reading_example.md").write_text("Content", encoding="utf-8")

        context, _ = gather_supplementary_context(tmp_path)

        assert context.startswith("--- READING:")

    def test_empty_folder_returns_empty(self, tmp_path):
        context, found = gather_supplementary_context(tmp_path)
        assert context == ""
        assert found == []

    def test_transcript_txt_skipped(self, tmp_path):
        (tmp_path / "transcript.txt").write_text("raw transcript", encoding="utf-8")

        context, found = gather_supplementary_context(tmp_path)

        assert found == []
        assert context == ""

    def test_md_and_txt_both_included(self, tmp_path):
        (tmp_path / "notes.txt").write_text("Extra notes", encoding="utf-8")
        (tmp_path / "reading_example.md").write_text("Web reading", encoding="utf-8")

        context, found = gather_supplementary_context(tmp_path)

        assert len(found) == 2
        assert "Extra notes" in context
        assert "Web reading" in context
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_generate_notes.py -v
```

Expected: `FAILED test_picks_up_md_file` — `.md` files not yet returned.

**Step 3: Extend gather_supplementary_context in generate_notes.py**

Find the end of `gather_supplementary_context` (after the `.txt` loop, before `return`). Add a `.md` file loop:

Old code (lines 101–113):
```python
    # Extra .txt files (not transcript)
    for txt in sorted(session_dir.glob("*.txt")):
        if txt.name.lower() in SKIP_NAMES:
            continue
        try:
            content = txt.read_text(encoding="utf-8", errors="replace").strip()
            if content:
                sections.append(f"--- NOTES: {txt.name} ---\n{content}")
                found.append(txt.name)
        except OSError:
            found.append(f"{txt.name} (unreadable — skipped)")

    return "\n\n".join(sections), found
```

New code:
```python
    # Extra .txt files (not transcript)
    for txt in sorted(session_dir.glob("*.txt")):
        if txt.name.lower() in SKIP_NAMES:
            continue
        try:
            content = txt.read_text(encoding="utf-8", errors="replace").strip()
            if content:
                sections.append(f"--- NOTES: {txt.name} ---\n{content}")
                found.append(txt.name)
        except OSError:
            found.append(f"{txt.name} (unreadable — skipped)")

    # Fetched URL content saved as .md files by url_fetcher
    for md in sorted(session_dir.glob("*.md")):
        try:
            content = md.read_text(encoding="utf-8", errors="replace").strip()
            if content:
                sections.append(f"--- READING: {md.name} ---\n{content}")
                found.append(md.name)
        except OSError:
            found.append(f"{md.name} (unreadable — skipped)")

    return "\n\n".join(sections), found
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_generate_notes.py -v
```

Expected: all 5 tests PASS.

**Step 5: Run full test suite to check for regressions**

```bash
pytest -x --ignore=tests/test_integration.py -q
```

Expected: all tests pass (or pre-existing failures only).

**Step 6: Commit**

```bash
git add generate_notes.py tests/test_generate_notes.py
git commit -m "feat: extend supplementary context to include fetched .md reading files"
```

---

### Task 4: Add --urls flag and wire URL fetching into process_lecture

**Files:**
- Modify: `generate_notes.py`

**Step 1: Add test for URL fetching in process_lecture**

Add to `tests/test_generate_notes.py`:

```python
from unittest.mock import patch, Mock
from pathlib import Path


class TestProcessLectureUrlFetching:
    """Verify that --urls causes fetch_url_to_file to be called."""

    def _make_transcript(self, tmp_path: Path) -> Path:
        transcript = tmp_path / "transcript.txt"
        transcript.write_text("Hello world lecture content here.", encoding="utf-8")
        return transcript

    def test_urls_fetched_before_context_gathering(self, tmp_path):
        transcript = self._make_transcript(tmp_path)

        with patch("generate_notes.CourseManager") as mock_cm, \
             patch("generate_notes.fetch_url_to_file") as mock_fetch, \
             patch("generate_notes.url_to_filename", return_value="reading_example.md"), \
             patch("generate_notes.TranscriptProcessor") as mock_tp, \
             patch("generate_notes.LLMGenerator") as mock_llm, \
             patch("generate_notes.CostTracker"), \
             patch("generate_notes.FrontmatterGenerator") as mock_fm, \
             patch("generate_notes.MarkdownValidator"):

            mock_cm.return_value.find_transcript.return_value = transcript
            mock_tp.return_value.process.return_value = Mock(
                status="success", error_message=None,
                cleaned_text="cleaned", word_count=10, original_word_count=15
            )
            mock_llm.return_value.generate_notes.return_value = Mock(
                status="success", content="# Notes",
                input_tokens=100, output_tokens=50, cost_aud=0.001,
                error_message=None
            )
            mock_fm.return_value.generate_frontmatter.return_value = "---\ntitle: test\n---\n"

            vault = tmp_path / "vault"
            vault.mkdir()

            from generate_notes import process_lecture
            process_lecture(
                course_code="MIS271", week=1, session="lecture",
                model="deepseek/deepseek-chat", api_key="key",
                vault_path=vault, estimate_only=False,
                urls=["https://example.com/article"],
            )

        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        assert call_args[0][0] == "https://example.com/article"

    def test_no_urls_skips_fetching(self, tmp_path):
        transcript = self._make_transcript(tmp_path)

        with patch("generate_notes.CourseManager") as mock_cm, \
             patch("generate_notes.fetch_url_to_file") as mock_fetch, \
             patch("generate_notes.TranscriptProcessor") as mock_tp, \
             patch("generate_notes.LLMGenerator") as mock_llm, \
             patch("generate_notes.CostTracker"), \
             patch("generate_notes.FrontmatterGenerator") as mock_fm, \
             patch("generate_notes.MarkdownValidator"):

            mock_cm.return_value.find_transcript.return_value = transcript
            mock_tp.return_value.process.return_value = Mock(
                status="success", error_message=None,
                cleaned_text="cleaned", word_count=10, original_word_count=15
            )
            mock_llm.return_value.generate_notes.return_value = Mock(
                status="success", content="# Notes",
                input_tokens=100, output_tokens=50, cost_aud=0.001,
                error_message=None
            )
            mock_fm.return_value.generate_frontmatter.return_value = "---\ntitle: test\n---\n"

            vault = tmp_path / "vault"
            vault.mkdir()

            from generate_notes import process_lecture
            process_lecture(
                course_code="MIS271", week=1, session="lecture",
                model="deepseek/deepseek-chat", api_key="key",
                vault_path=vault, estimate_only=False,
                urls=[],
            )

        mock_fetch.assert_not_called()
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_generate_notes.py::TestProcessLectureUrlFetching -v
```

Expected: FAIL — `process_lecture` doesn't accept `urls` yet.

**Step 3: Add imports to generate_notes.py**

At the top of `generate_notes.py`, add after the existing `from src.` imports:

```python
from src.url_fetcher import fetch_url_to_file, url_to_filename
```

**Step 4: Update process_lecture signature**

Change the function signature from:
```python
def process_lecture(
    course_code: str,
    week: int,
    session: str,
    model: str,
    api_key: str,
    vault_path: Path,
    estimate_only: bool,
) -> bool:
```

To:
```python
def process_lecture(
    course_code: str,
    week: int,
    session: str,
    model: str,
    api_key: str,
    vault_path: Path,
    estimate_only: bool,
    urls: list[str] | None = None,
) -> bool:
```

**Step 5: Add URL fetching block in process_lecture**

After the transcript is found (after `_print("✓", f"Transcript: {transcript_path}")`), and before the `# 2. Gather supplementary context` comment, insert:

```python
    # 2. Fetch external URLs into session folder (if provided)
    session_dir = transcript_path.parent
    if urls:
        for url in urls:
            filename = url_to_filename(url)
            dest = session_dir / filename
            if dest.exists():
                _print("✓", f"URL cached: {filename}")
            else:
                _print("→", f"Fetching {url} ...")
                ok = fetch_url_to_file(url, dest)
                if ok:
                    _print("✓", f"Saved: {filename}")
                else:
                    _print("~", f"Could not fetch {url} — skipped")

```

Then update the existing `# 2. Gather supplementary context` block to use the `session_dir` already set above — **remove** the `session_dir = transcript_path.parent` line that currently sits inside step 2, since it's now defined above:

Old:
```python
    # 2. Gather supplementary context (slides, readings) from the session folder
    session_dir = transcript_path.parent
    supplementary_context, found_files = gather_supplementary_context(session_dir)
```

New (renumber to step 3):
```python
    # 3. Gather supplementary context (slides, readings, fetched URLs) from the session folder
    supplementary_context, found_files = gather_supplementary_context(session_dir)
```

Also renumber all subsequent steps (3→4, 4→5, etc.) in comments.

**Step 6: Add --urls argument to main()**

In `main()`, after the `--estimate-only` argument block, add:

```python
    parser.add_argument(
        "--urls",
        nargs="*",
        default=[],
        metavar="URL",
        help="External URLs to fetch and include as reading context (space-separated)",
    )
```

**Step 7: Pass urls into process_lecture call**

In `main()`, update the `process_lecture(...)` call to include `urls=args.urls`.

Old:
```python
        ok = process_lecture(
            course_code=args.course,
            week=week,
            session=args.session,
            model=model,
            api_key=api_key,
            vault_path=vault_path,
            estimate_only=args.estimate_only,
        )
```

New:
```python
        ok = process_lecture(
            course_code=args.course,
            week=week,
            session=args.session,
            model=model,
            api_key=api_key,
            vault_path=vault_path,
            estimate_only=args.estimate_only,
            urls=args.urls,
        )
```

**Step 8: Run tests to verify they pass**

```bash
pytest tests/test_generate_notes.py -v
```

Expected: all tests PASS.

**Step 9: Smoke-test the CLI flag parses correctly**

```bash
python generate_notes.py --help
```

Expected: `--urls` appears in the help output under optional arguments.

**Step 10: Commit**

```bash
git add generate_notes.py
git commit -m "feat: add --urls flag to fetch external reading URLs into session folder"
```

---

### Task 5: Update CHEATSHEET.md

**Files:**
- Modify: `CHEATSHEET.md`

**Step 1: Add --urls example to the Generate Notes section**

In `CHEATSHEET.md`, in the `generate_notes.py` bash block, add a new example after the `--model` example:

```bash
# Include external reading URLs as additional context
python generate_notes.py --course MIS271 --week 3 --urls https://ibm.com/think/topics/olap-vs-oltp

# Multiple URLs
python generate_notes.py --course MIS271 --week 3 --urls https://example.com/article1 https://example.com/article2
```

Also add a note under the folder structure block explaining that fetched URLs are cached as `.md` files:

```
└── MIS271_week_03_lecture/week_03_lecture/
    ├── transcript.txt
    ├── slides.pdf                        ← optional
    └── reading_ibm.com_olap-vs-oltp.md  ← auto-saved when --urls used
```

**Step 2: Commit**

```bash
git add CHEATSHEET.md
git commit -m "docs: document --urls flag in cheatsheet"
```

---

## Quick Verification

After all tasks, run this to confirm everything works end-to-end:

```bash
# Confirm tests pass
pytest tests/test_url_fetcher.py tests/test_generate_notes.py -v

# Confirm CLI help shows --urls
python generate_notes.py --help

# Confirm cost estimate works with a URL (no API call, real HTTP fetch)
python generate_notes.py --course MIS271 --week 1 --estimate-only --urls https://www.ibm.com/think/topics/olap-vs-oltp
```
