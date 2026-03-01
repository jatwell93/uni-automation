# Phase 1: Foundation - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a Python CLI that loads configuration from a YAML file, authenticates with Panopto using stored browser cookies, downloads video and transcript files with integrity validation, and logs all actions with clear error messages. The foundation enables all downstream phases (media processing, LLM integration, Obsidian output).

</domain>

<decisions>
## Implementation Decisions

### Configuration Management
- Config format: YAML (human-readable, standard for Python, supports comments)
- Required fields: Panopto URL, slide path, cookie file path, output folder
- Optional fields: course name, week number, lecturer name, timestamp, custom notes (with sensible defaults)
- Validation: Check all fields at startup before any downloads begin; fail fast with clear error message
- Cookie storage: Separate file (not inline in config); config contains path to cookie file
- Cookie format: Browser JSON export (e.g., from Chrome DevTools or Cookie Editor extension)

### Cookie Authentication Flow
- Cookie extraction: User exports cookies from browser as JSON file
- Validation strategy: Test API call to Panopto before video download (verify session is fresh, not just check expiry)
- Expiry handling: If cookies invalid/expired, fail immediately with clear instructions ("Cookies expired. Refresh from browser: [instructions or script]")
- Security: File permissions only (store in .gitignore, rely on Windows NTFS ACL; no encryption, no OS keyring)

### Error Handling & Logging
- Log location: Local file in project (e.g., `.planning/logs/week_XX.log`)
- Log level: Standard (errors, successes, major steps like "Download started/ended", validation pass/fail)
- Log format: Timestamped entries for later review and debugging
- Error messages: Clear and actionable (e.g., "Cookie expired. Run: python extract_cookies.py" or direct browser instructions)
- Console output: Simple progress ("Downloading video...", "Downloaded transcript", final summary with file sizes and log location)

### CLI Invocation & Output
- Command syntax: `python run_week.py <config_file>` (simple, everything else from config)
- Output directory: Config file specifies where downloads go (output_dir field)
- Exit codes: 0 on success, non-zero on errors (supports CI/automation)
- Console summary: Success summary showing files downloaded with sizes + log file location (e.g., "✓ Downloaded video_05.mp4 (450 MB)\n✓ Downloaded transcript_05.vtt\n✓ Logs: .planning/logs/week_05.log")

### Panopto Integration
- Build approach: Custom (build from scratch using requests library + cookie authentication; provides control and robustness)
- Video download: Direct download via requests library (pass authenticated cookie session; stream download; validate file integrity after)
- Transcript fetch: Use Panopto API via authenticated cookies to fetch transcript (JSON or VTT format); not web scraping
- Fallback strategy: If API unavailable, skip transcript with clear message (don't fail entire pipeline; Phase 2 can handle missing transcript)

### OpenCode's Discretion
- Exact cookie JSON parsing format (minor variations in schema)
- ffprobe validation details (specific checks for codec, duration, file size thresholds)
- Download streaming implementation (chunk size, buffer management)
- Logging format details (exact timestamp format, log line structure)
- Progress bar implementation on Windows console
- Exact error message wording (as long as it's clear + actionable)

</decisions>

<specifics>
## Specific Ideas

- Instructions for extracting cookies should be included in README or error message (link to Chrome DevTools or Cookie Editor extension)
- Test the cookie validation API call early; if it fails, don't waste time downloading video
- Log file should be human-readable and parseable (useful for debugging + understanding what happened)
- Output summary should be visible even if user doesn't read logs ("you succeeded, here's where files are")

</specifics>

<deferred>
## Deferred Ideas

- Batch processing multiple lectures in one run (Phase 3 or later)
- Scheduled/automated weekly runs via cron (Phase 4 or later)
- GUI for configuration instead of YAML files (Phase 4+ or separate effort)
- Support for other video platforms besides Panopto (out of scope)
- Integration with Canvas/Blackboard LMS (other LMS systems out of scope for v1)

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-03-02*
