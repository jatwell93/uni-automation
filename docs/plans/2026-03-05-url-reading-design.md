# Design: External URL Reading Support

**Date:** 2026-03-05
**Status:** Approved

## Problem

Lectures sometimes reference external web articles as required readings (e.g. IBM blog posts, Wikipedia pages). Currently the pipeline only ingests local files (PDFs, txt). There is no way to pass a web URL and have its content included as LLM context.

## Goals

- Accept one or more URLs via `--urls` CLI flag on `generate_notes.py`
- Fetch and convert page content to clean markdown locally (no external API services)
- Cache fetched content in the session folder so re-runs use the saved file
- Surface URL content to the LLM with the same `READING:` label as other supplementary files

## Non-Goals

- No Brave API, no LLM web search
- No auto-detection of URLs from transcript text
- No browser/JS rendering (requests-only; JS-heavy SPAs will yield partial content)

## Design

### New module — `src/url_fetcher.py`

```python
fetch_url_to_file(url: str, dest_path: Path) -> bool
```

- Fetches `url` with `requests` (5 s connect / 15 s read timeout)
- Sets a realistic `User-Agent` header to avoid basic bot blocks
- Converts HTML → markdown via `html2text` (strips nav, scripts, styles automatically)
- Writes result to `dest_path`
- Returns `True` on success, `False` on any network/HTTP error (non-fatal — run continues)

```python
url_to_filename(url: str) -> str
```

- Converts a URL to a safe filename: `reading_{domain}_{path-slug}.md`
- Example: `https://ibm.com/think/topics/olap-vs-oltp` → `reading_ibm.com_olap-vs-oltp.md`
- Truncated to 120 chars to stay well within filesystem limits

### `generate_notes.py` changes

1. Add `--urls URL [URL ...]` argument (`nargs='*'`), default empty list
2. Pass `urls` into `process_lecture()`
3. In `process_lecture()`, before gathering supplementary context:
   - For each URL, derive filename via `url_to_filename()`
   - If file already exists in session folder → log "cached, skipping re-fetch"
   - Otherwise call `fetch_url_to_file()` → log success/failure
4. Extend `gather_supplementary_context()` to also glob `*.md` files, labelled `READING: <filename>`

### Caching

Fetched content is saved as a `.md` file in the session folder alongside `transcript.txt`. On subsequent runs the file is detected by `gather_supplementary_context` as a regular file — no re-fetch occurs. To force a refresh, delete the cached `.md` file.

### Dependencies

Add to `requirements.txt`:
```
html2text>=2024.2.26
```

`requests` is already present.

## File Changes

| File | Change |
|------|--------|
| `src/url_fetcher.py` | New module |
| `generate_notes.py` | Add `--urls` flag; fetch URLs before context gathering; pass urls into process_lecture |
| `gather_supplementary_context()` | Extend to glob `*.md` files |
| `requirements.txt` | Add `html2text` |
| `CHEATSHEET.md` | Document `--urls` flag |

## Error Handling

- Network error / timeout → print warning, skip that URL, continue with other sources
- HTTP 4xx/5xx → same (warn + skip)
- Empty page after conversion → warn + skip
- All failures are non-fatal; the run proceeds with whatever context was successfully gathered
