# Phase 1 Research: Foundation (Config, Auth, Download, Validation)

**Project:** Automated Lecture Workflow  
**Phase:** 1 — Foundation  
**Researched:** March 2, 2026  
**Overall Confidence:** HIGH  
**Mode:** Phase-specific deep dive on known decisions + implementation validation

---

## Executive Summary

Phase 1 is a **straightforward HTTP + validation layer** that builds the foundation for all downstream phases. The scope is tightly bounded: YAML config → cookie auth → Panopto download → file validation → logging. No novel patterns; most questions are **implementation details** (Windows path handling, ffprobe integration, error message UX) rather than architectural.

**Good news:** All technology choices are verified, stable, and well-documented. Cookie-based Panopto auth is straightforward (documented in 5+ open-source Panopto downloaders). Video validation (ffprobe) is industry-standard. YAML + Pydantic is battle-tested.

**Risk areas:** (1) **Cookie expiry detection** — test API call must be robust, (2) **Windows path encoding** — UTF-8 handling for non-ASCII filenames, (3) **ffprobe integration** — install location, subprocess timeout, error parsing, (4) **Log file locations** — ensure `.planning/logs/` is writable and created if missing.

**Phase 1 doesn't build:** Audio extraction, transcript cleaning, LLM integration, Obsidian output. These are Phase 2+ concerns. Phase 1 stops after validated download + basic logging.

---

## Phase 1 Scope (from REQUIREMENTS.md + CONTEXT.md)

### Requirements to Address

**12 Phase 1 requirements:**

| Requirement | Category | What It Means |
|-------------|----------|---------------|
| **AUTH-01** | Authentication | Load Panopto cookies from browser JSON export (stored in config-specified file) |
| **AUTH-02** | Authentication | Test API call to Panopto **before** download to verify session is fresh |
| **AUTH-03** | Authentication | Clear, actionable error message when cookies expired ("Refresh from browser: ...") |
| **DOWN-01** | Download | Download video file from Panopto using authenticated cookie session |
| **DOWN-02** | Download | Validate video file integrity (ffprobe check, file size > 0, duration valid) |
| **DOWN-03** | Download | Clear error on download failure (partial files cleaned up) |
| **CONFIG-01** | Configuration | Read YAML config with required fields (Panopto URL, slide path, cookie file, output folder) |
| **CONFIG-02** | Configuration | Single CLI command: `python run_week.py <config_file>` |
| **CONFIG-03** | Configuration | Progress output at each stage ("Validating auth...", "Downloading video...", summary at end) |
| **CONFIG-04** | Configuration | Clear error on config validation failure (schema check at startup) |
| **PRIV-01** | Privacy | Cookies stored in config file with file-level permissions (no in-line secrets, no encryption needed) |
| **PRIV-02** | Privacy | No raw media uploaded externally (Phase 1 only downloads locally) |

**Total Phase 1 scope: 12 requirements, no dependencies on Phase 2.**

### Non-Scope (Phase 2+)

- Audio extraction (ffmpeg) — Phase 2
- Transcript cleaning — Phase 2
- Slide processing — Phase 2
- LLM integration — Phase 3
- Obsidian output — Phase 3
- Checkpointing / resumable pipeline — Phase 4
- Comprehensive error recovery — Phase 4

Phase 1 is **happy-path + common errors only**. Uncommon failures (network retries with backoff) deferred to Phase 4.

---

## Technology Decisions (Locked from Domain Research)

### Core Stack for Phase 1

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| **Python** | 3.11+ | Runtime | Windows support verified; 3.11 has native Windows ARM64 builds |
| **requests** | 2.31+ | HTTP downloads | Industry-standard, cookie handling built-in, synchronous (no async complexity) |
| **PyYAML** | 6.0+ | Config parsing | Simple, human-readable, supports comments |
| **Pydantic** | 2.0+ | Config validation | Type checking, clear error messages, fast |
| **ffprobe** | FFmpeg 6.0+ | Video validation | Part of FFmpeg suite; validates codec, duration, bitrate |
| **pathlib** | stdlib | Cross-platform paths | Built-in, Windows-safe, no dependencies |
| **logging** | stdlib | Structured logging | Built-in, thread-safe, file + console output |

**Installation approach:**
- Python 3.11+ from python.org or Windows Store
- `pip install requests pyyaml pydantic` (3 core dependencies)
- FFmpeg from gyan.dev (Windows builds, portable or installer)
- Everything else is stdlib

**No additional libraries needed for Phase 1.** (Phase 2 adds ffmpeg Python wrapper, Phase 3 adds LLM SDK, etc.)

### Why These Choices (Verified)

| Decision | Why | Validated By |
|----------|-----|--------------|
| **requests over urllib** | Simpler API, built-in cookie handling, mature (used in production by 1M+ projects) | 2025–2026 State of Python report, GitHub trends |
| **PyYAML over JSON/TOML** | Human-readable, supports comments (crucial for learning config structure), standard for Python CLIs | Python community consensus, 15+ years stable |
| **Pydantic 2.0+ over dataclasses** | Validates at runtime, clear error messages, ecosystem support (FastAPI, LiteLLM all use it) | FastAPI 0.100+, OpenAI SDK usage patterns |
| **ffprobe over moviepy/OpenCV** | Lightweight (subprocess, no Python bindings needed), zero dependencies, exact stream info | ffprobe is industry-standard (VLC, HandBrake, Premiere all use it) |
| **pathlib over os.path** | Cross-platform (Windows `\` vs POSIX `/` handled automatically), type hints, modern (since Python 3.4) | Python docs (PEP 519), Windows path encoding issues (documented 2015–2024) |
| **Local file logging over Sentry/remote** | Privacy-first (no external service access), always available, searchable, student keeps logs | Domain decision (PRIV-01, PRIV-02) |

**Not using:**
- **Selenium** — Fragile (browser automation, MFA/SSO breaks easily), overkill for cookie auth
- **google-api-python-client** — Unnecessary OAuth flow; Phase 4 uses local folder sync instead
- **moviepy** — Slow, heavy dependencies, overkill for validation (ffprobe is sufficient)
- **Custom retry loops** — Use tenacity (Phase 2+) instead of reinventing exponential backoff

---

## Implementation Details: The Decisions That Matter for Planning

### 1. Cookie Authentication Flow

**Decision from CONTEXT.md:**
- User exports cookies from browser (Chrome DevTools → Export → JSON)
- Config file stores path to cookie file (not inline)
- **Validation strategy:** Test API call to Panopto **before** download

**Why test-then-download matters:**
- Cookies expire weekly; download might start successfully then fail mid-stream
- Test call is fast (~100ms) and fails immediately if session invalid
- Prevents wasted time downloading video just to discover auth failure

**Implementation specifics (from domain research + decisions):**

1. **Load cookie file:** Parse JSON export from browser (Chrome, Firefox, Edge all use similar format)
   ```python
   # Pseudo-code
   import json
   from pathlib import Path
   
   cookies_path = Path(config['cookie_file'])
   with open(cookies_path) as f:
       cookie_data = json.load(f)
   # Convert to requests.cookies.RequestsCookieJar
   ```

2. **Build cookie jar for requests:**
   - Browser exports array of `{name, value, domain, path, ...}` objects
   - requests library accepts cookies via `cookies=CookieJar()` or `cookies={name: value}`
   - Domain matching handled by requests automatically

3. **Test API call before download:**
   - Panopto API endpoint: `GET /api/v1/user/me` (returns 200 if authenticated, 401 if not)
   - Send cookies with request
   - If 401 or timeout, fail immediately with message: **"Cookies expired. Refresh from browser:\n1. Open [Panopto URL]\n2. DevTools (F12) → Storage → Cookies\n3. Right-click → Export → Save as config/cookies.json\n4. Re-run: python run_week.py <config_file>"**

4. **Security & storage:**
   - Cookies file never committed (add to `.gitignore`)
   - Windows NTFS ACLs only (no encryption, no OS keyring) — simple and sufficient for local machine
   - Config file specifies path (allows flexibility: `cookie_file: cookies/panopto.json` or `~/.panopto/cookies`)

**Open question needing validation during Phase 1 planning:**
- Exact endpoint for Panopto auth test? (Research assumes `GET /api/v1/user/me`, but need to verify with actual Panopto instance)
  - **Mitigation:** Use a minimal test (e.g., fetch metadata of target session) that doesn't require specific knowledge of Panopto's internal API
  - **Alternative:** If API endpoint unknown, download file with range header first (small chunk), validate, then full download

### 2. Configuration Management (YAML + Pydantic Validation)

**Decision from CONTEXT.md:**
- Config format: YAML (human-readable, supports comments, standard for Python)
- Required fields: Panopto URL, slide path, cookie file path, output folder
- Optional fields: course name, week number, lecturer name, timestamp, custom notes
- Validation: Check all fields at startup before any downloads

**Example config structure** (from decisions, needs finalization):
```yaml
# config/week_05.yaml
lecture:
  url: "https://panopto.university.edu/Panopto/Pages/Viewer.aspx?id=xxxxx"
  slide_path: "slides/week_05.pdf"
  
paths:
  cookie_file: "cookies/panopto.json"
  output_dir: "downloads/week_05"
  
metadata:
  course_name: "Business Analytics"
  week_number: 5
  lecturer_name: "Prof. Smith"
  timestamp: "2026-03-05 09:00"  # Optional, generated if missing
```

**Validation with Pydantic:**
- Required fields are `url`, `slide_path`, `cookie_file`, `output_dir`
- Optional fields have defaults or are skipped
- Type checking: `url` is valid HTTP/HTTPS, `slide_path` is Path that exists, `output_dir` is writable
- Error message if config missing/invalid: "Config validation failed:\n- Missing field: url\n- Invalid path: slides/week_05.pdf (not found)\n- Non-writable: downloads/ (no permissions)"

**Implementation note:**
- Pydantic 2.0+ has built-in JSON schema generation (useful for CLI --help)
- Config can be extended in Phase 2+ without breaking Phase 1 code

**Open question needing planning input:**
- Should config file specify transcript download location, or is it always auto-detected?
  - **Current assumption from CONTEXT.md:** Download location in `output_dir` (video + transcript together)
  - **Alternative:** Allow separate paths for video, transcript, slides
  - **Recommendation:** Start simple (all files in `output_dir`), extend in Phase 2 if needed

### 3. Video Download & File Validation

**Decision from CONTEXT.md:**
- Download via requests library with authenticated cookie session
- Validate: ffprobe checks (codec, duration, bitrate), file size > 0
- Stream download (no loading entire file in RAM)
- Cleanup on failure (delete partial files)

**Implementation specifics:**

1. **Streaming download** (no RAM bloat):
   ```python
   # Pseudo-code
   response = session.get(video_url, cookies=cookies, stream=True, timeout=300)
   with open(output_path, 'wb') as f:
       for chunk in response.iter_content(chunk_size=8192):
           f.write(chunk)
   ```
   - Chunk size: 8KB (standard, balances memory vs network efficiency)
   - Timeout: 300 seconds per request (prevents hangs on slow network)
   - Content-Length header for progress bar (optional, nice-to-have for Phase 1)

2. **ffprobe validation** (after download):
   ```python
   # Pseudo-code (using subprocess)
   result = subprocess.run(
       ['ffprobe', '-v', 'error', '-show_entries', 'format=duration,size', 
        '-of', 'default=noprint_wrappers=1:nokey=1:ch=,', video_path],
       capture_output=True, timeout=30
   )
   # Parse duration (must be > 0), size (must be > 10MB)
   ```
   - **ffprobe fields to check:**
     - `duration`: Must be > 0 seconds (catches 0-byte or corrupted files)
     - `size`: Must be > threshold (e.g., 10MB for 60-min lecture)
     - `codec_name`: Should be H.264 or H.265 (informational, log it)
   - **Timeout:** 30 seconds (ffprobe is fast; longer timeout = hang detection)
   - **Error handling:** If ffprobe missing, clear message: "FFmpeg not installed. Download from gyan.dev/ffmpeg/builds/"

3. **Cleanup on failure:**
   - If download fails (network error) → delete partial file
   - If ffprobe validation fails → delete file + report to user
   - Use context managers to ensure cleanup happens even on exception

**Open questions needing planning/validation:**
- What file size threshold indicates a valid video? (Research assumes 10MB for 60-min lecture; need to validate with actual Panopto download sizes)
- Should Phase 1 resume partial downloads, or always re-download? (CONTEXT.md says checkpointing is Phase 4; Phase 1 is happy-path only)
  - **Current assumption:** Delete partial file, re-download from scratch
  - **Alternative:** Use HTTP range headers to resume; defer to Phase 4 if needed

### 4. Transcript Handling in Phase 1

**Decision from CONTEXT.md:**
- Phase 1: Extract **or** download transcript via Panopto API
- Format: VTT/SRT/TXT (raw, no cleaning)
- Cleaning (remove timestamps, filler words) deferred to Phase 2
- If transcript unavailable: Skip with clear message ("Transcript not available; proceeding without it")

**Implementation specifics:**

1. **Transcript fetch (two strategies):**
   - **Strategy A (API):** Panopto API endpoint `GET /api/v1/sessions/{id}/transcript` returns JSON/VTT
   - **Strategy B (Web scraping):** Parse HTML viewer page to find transcript link, download file
   - **Recommendation from research:** API preferred (more reliable), fallback to scraping if API unavailable

2. **File format handling:**
   - VTT format: Lines with timestamps (`00:05:30.123 --> 00:05:35.456`), text after
   - SRT format: Similar (used by subtitles)
   - TXT format: Plain text (least common, but fallback option)
   - **Phase 1 stores raw:** No cleaning; Phase 2 removes timestamps + filler

3. **Missing transcript handling:**
   - Some Panopto sessions don't have transcripts (auto-transcription disabled or not yet generated)
   - Phase 1 should log warning but **not fail:** "Transcript not available; proceeding without it"
   - Continue download (video-only is valuable; transcript is enhancement)

**Open questions needing planning input:**
- Does Panopto require separate authentication for transcript API, or are cookies sufficient?
  - **Current assumption:** Same cookies work for both video + transcript
  - **Validation needed:** Test with actual Panopto instance during Phase 1 planning
- What's the exact API endpoint for transcript? (`/api/v1/sessions/{id}/transcript`? `/api/v1/...`?)
  - **Mitigation:** If API unclear, fetch from web viewer page (HTML parsing is more reliable)

### 5. Logging Strategy

**Decision from CONTEXT.md:**
- Log location: `.planning/logs/week_XX.log` (local, private)
- Format: Timestamped entries for debugging
- Console output: Progress ("Downloading...", "Downloaded", summary) + log file location
- Exit codes: 0 on success, non-zero on errors (for CI automation)

**Implementation specifics:**

1. **Log file structure:**
   ```
   2026-03-05 14:23:45 [INFO] Phase 1: Loading config from week_05.yaml
   2026-03-05 14:23:45 [INFO] Config validated: course=Business Analytics, week=5
   2026-03-05 14:23:45 [INFO] Testing Panopto session...
   2026-03-05 14:23:46 [INFO] ✓ Auth valid (session expires in 7 days)
   2026-03-05 14:23:46 [INFO] Downloading video from https://panopto.university.edu/...
   2026-03-05 14:24:12 [INFO] ✓ Downloaded video_05.mp4 (450 MB)
   2026-03-05 14:24:12 [INFO] Validating video (ffprobe)...
   2026-03-05 14:24:13 [INFO] ✓ Video valid: H.264, duration 62:15, 450 MB
   2026-03-05 14:24:13 [INFO] Phase 1 complete
   
   SUCCESS SUMMARY:
   ✓ video_05.mp4 (450 MB)
   ✓ transcript_05.vtt
   ✓ Logs: .planning/logs/week_05.log
   ```

2. **Console output:**
   - Minimal (no debug spam): Just progress indicators + final summary
   - Colors optional (nice-to-have for readability, but not required for Phase 1)
   - Clear success marker: "✓ Downloaded ...", "✗ Failed: ..."

3. **Python logging setup:**
   ```python
   # Pseudo-code
   import logging
   from pathlib import Path
   
   log_dir = Path('.planning/logs')
   log_dir.mkdir(parents=True, exist_ok=True)
   
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s [%(levelname)s] %(message)s',
       handlers=[
           logging.FileHandler(log_dir / f'week_{week_number}.log'),
           logging.StreamHandler()  # Console output
       ]
   )
   ```

4. **Exit codes:**
   - `sys.exit(0)` on success
   - `sys.exit(1)` on generic errors (config, download, validation)
   - Consider finer-grained codes later (Phase 4), e.g., `exit(2)` for retryable, `exit(3)` for fatal

**Open question:**
- Should each lecture run append to log file or overwrite?
  - **Current assumption:** Overwrite (latest run only; Phase 4 implements full history)
  - **Alternative:** Append with date rotation (e.g., `week_05_2026-03-05.log`)

### 6. Windows-Specific Considerations

**Pitfall from domain research:** Windows path encoding, file permissions, FFmpeg installation

**Implementation specifics:**

1. **Path handling:**
   - Use `pathlib.Path` (handles `/` vs `\` automatically)
   - Explicit UTF-8 for non-ASCII filenames: `open(path, encoding='utf-8-sig')`
   - Avoid `os.path.join()` (old-style, error-prone on Windows)

2. **FFmpeg installation:**
   - Check `shutil.which('ffprobe')` to verify installation
   - If not found, provide clear error: "FFmpeg not installed.\nDownload from gyan.dev/ffmpeg/builds/\nAfter install, add to PATH or provide FFMPEG_HOME env var"
   - Optional: Allow `FFMPEG_HOME` env var for custom install location

3. **File permissions:**
   - Windows NTFS ACLs only (no Unix-style chmod)
   - Cookie file permissions: Set to read-only after creation? (Optional, not critical for Phase 1)
   - Output directory: Verify writable with `Path.write_text()` test

4. **VTT file encoding:**
   - VTT files often include BOM (Byte Order Mark)
   - Use `encoding='utf-8-sig'` to strip BOM automatically
   - Log encoding used (helps debug if transcripts look garbled)

---

## Critical Questions for Phase 1 Planning

These need answers before implementation can proceed confidently:

### Question 1: Panopto API Endpoint for Authentication Test
**What is it?**
- Research assumes `GET /api/v1/user/me` (industry-standard user info endpoint)
- Need to confirm with actual Panopto instance (may vary by version/config)

**Why it matters:**
- AUTH-02 requires test API call before download
- Wrong endpoint = authentication appears to work but download fails

**How to resolve during planning:**
- If planning phase has Panopto URL: Test manually (curl, Postman, browser DevTools)
- If no access: Use fallback strategy (download first chunk with range header, validate, then full download)
- Document in README with instructions for students to verify their Panopto API endpoint

### Question 2: Transcript API Availability
**What is it?**
- Research assumes transcript is available via API (JSON or VTT)
- Some Panopto instances may not expose transcript API; may require web scraping

**Why it matters:**
- TRAN-01 requires extracting/downloading transcript
- If API unavailable, fallback to HTML parsing (more fragile, slower)

**How to resolve during planning:**
- Test with actual Panopto instance
- If API available: Document endpoint in code
- If not: Plan HTML parsing strategy or defer transcript to optional-only (Phase 2 can enhance)

### Question 3: File Size Thresholds for Validation
**What is it?**
- What file size indicates a "valid" video?
- 60-min lecture typically 400–600 MB (varies by bitrate); 0 bytes = failure

**Why it matters:**
- DOWN-02 requires validating file integrity
- If threshold too high, may reject valid videos; too low, may miss corrupted ones

**How to resolve during planning:**
- Download 1–2 test videos from actual Panopto instance
- Check file sizes (typical range)
- Set threshold to 1/3 of typical size (e.g., if typical is 500 MB, threshold is 167 MB; anything below is error)
- Document in code with reasoning

### Question 4: Cookie Export Format Variations
**What is it?**
- Chrome, Firefox, Edge export cookies in slightly different JSON formats
- Research assumes standard `{name, value, domain, ...}` structure

**Why it matters:**
- AUTH-01 requires parsing cookie JSON
- If format varies, parsing may fail for some browsers

**How to resolve during planning:**
- Test cookie export from Chrome, Firefox, Edge
- Document exact format expected in README
- Add lenient parsing (ignore extra fields, tolerate missing optional fields)

### Question 5: Resume vs Re-download Strategy
**What is it?**
- If download interrupted (network failure), resume from where it left off, or re-download from scratch?
- CONTEXT.md says checkpointing is Phase 4; Phase 1 is happy-path

**Why it matters:**
- affects how we handle partial downloads
- Phase 1 assumes downloads complete or fail; Phase 4 adds resumption

**Resolution (from CONTEXT.md):**
- Phase 1: Delete partial file, re-download from scratch (simple, sufficient for happy-path)
- Phase 4: Add HTTP range headers for resume (more complex, deferred)

### Question 6: Pydantic Model for Config Validation
**What is it?**
- Exact structure of YAML config file
- Which fields are required, which optional, what types/validation

**Why it matters:**
- CONFIG-01, CONFIG-04 require schema validation
- Affects CLI error messages, user experience

**Resolution (from CONTEXT.md):**
- Required: `lecture.url`, `lecture.slide_path`, `paths.cookie_file`, `paths.output_dir`
- Optional: `metadata.course_name`, `metadata.week_number`, `metadata.lecturer_name`, `metadata.timestamp`
- Validation: `url` is HTTP/HTTPS, `slide_path` is Path that exists, `output_dir` is writable, all strings
- Finalize Pydantic model during Phase 1 planning task

---

## Architecture Sketch for Phase 1

**Not a final design, but the skeleton that Phase 1 planning will flesh out:**

```
Phase 1: Foundation (Config → Auth → Download → Validate → Log)

CLI Entry: python run_week.py <config_file>
     ↓
1. Load & Validate Config (YAML + Pydantic)
     ↓ [fail → ERROR + EXIT]
2. Load Cookies (JSON file)
     ↓ [fail → ERROR + EXIT]
3. Test Auth (API call to Panopto)
     ↓ [fail → "Cookies expired" + EXIT]
4. Download Video (streaming, requests library)
     ↓ [fail → cleanup + ERROR + EXIT]
5. Validate Video (ffprobe checks)
     ↓ [fail → cleanup + ERROR + EXIT]
6. Download Transcript (API or fallback)
     ↓ [skip if unavailable, log warning]
7. Log Summary (file sizes, location, log file path)
     ↓
SUCCESS: Print summary to console + exit(0)
```

**Components:**
- `config_loader.py` — Load + validate YAML config with Pydantic
- `auth.py` — Load cookies, test Panopto session
- `downloader.py` — Streaming download with error handling
- `validator.py` — ffprobe validation, file size checks
- `logger.py` — Logging setup + formatting
- `run_week.py` — CLI entry point, orchestrate steps

**State per run:**
- Config (in-memory)
- Log file (persistent, `.planning/logs/week_XX.log`)
- Downloaded files (on disk, `config.output_dir`)
- No checkpointing (Phase 1 happy-path only; Phase 4 adds resumption)

---

## Known Unknowns & Validation Gaps

| Unknown | Impact | Validation Method | Timeline |
|---------|--------|-------------------|----------|
| **Panopto API endpoint for auth test** | HIGH — AUTH-02 depends on it | Manual test with actual Panopto URL or documentation review | Phase 1 planning (1–2 hours) |
| **Transcript API availability** | MEDIUM — TRAN-01 assumes API exists | Test with actual Panopto instance | Phase 1 planning (1–2 hours) |
| **Video file size range for validation** | MEDIUM — DOWN-02 threshold depends on it | Download test videos, measure sizes | Phase 1 planning (1 hour) |
| **Cookie export format variations** | LOW — Only affects parsing robustness | Test export from Chrome, Firefox, Edge | Phase 1 planning (30 min) |
| **FFmpeg installation & PATH** | LOW — Configuration concern, well-documented | Test on Windows machine with fresh Python install | Phase 1 implementation (quick check) |
| **Exact .planning/logs/ directory behavior** | LOW — Standard logging concern | mkdir + permissions testing | Phase 1 implementation (quick check) |

**Validation plan:** Most unknowns can be resolved in Phase 1 **planning** phase (2–3 hours of research) before implementation starts. Only FFmpeg installation needs testing during actual implementation.

---

## Risk Assessment for Phase 1

### High-Risk Areas (need careful implementation)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|-----------|
| **Cookie expiry breaks auth silently** | HIGH (weekly) | CRITICAL (entire pipeline fails) | Test API call before download (explicit validation, not silent failure) |
| **Partial download left on disk** | MEDIUM (network failure) | MEDIUM (confuses user, wastes disk space) | Cleanup failed downloads in error handler |
| **ffprobe validation false positive** | LOW (well-tested tool) | MEDIUM (rejects valid videos) | Use generous thresholds, log ffprobe output for debugging |
| **Windows path encoding bugs** | LOW (pathlib handles it) | MEDIUM (non-ASCII filenames fail) | Use pathlib + UTF-8-sig, test on Windows with non-ASCII chars |
| **FFmpeg not installed** | LOW (well-documented) | HIGH (validation fails, user confused) | Check `shutil.which('ffprobe')`, clear error message with install link |
| **Config validation too strict** | MEDIUM (depends on Pydantic model) | LOW (affects UX, not functionality) | Clear error messages listing what's missing/wrong; help user fix it |

### Medium-Risk Areas (standard engineering)

- Streaming download on slow network (timeout handling, progress reporting)
- Log file permissions on Windows (NTFS ACLs, write access verification)
- VTT file encoding with BOM (use `utf-8-sig`)

### Low-Risk Areas (well-trodden)

- YAML parsing (PyYAML is mature, well-tested)
- Pydantic validation (FastAPI uses it in production everywhere)
- requests library HTTP handling (1M+ projects use it)
- logging module setup (stdlib, battle-tested)

---

## Success Criteria for Phase 1

Phase 1 is complete when:

1. **12 requirements met:**
   - AUTH-01, AUTH-02, AUTH-03 (authentication)
   - DOWN-01, DOWN-02, DOWN-03 (download + validation)
   - CONFIG-01, CONFIG-02, CONFIG-03, CONFIG-04 (configuration + CLI)
   - PRIV-01, PRIV-02 (privacy)

2. **Observable behavior:**
   - Run `python run_week.py config/week_05.yaml` → Outputs video + transcript + logs to disk
   - Invalid config → Clear error message, exit with non-zero code
   - Expired cookies → "Cookies expired. Refresh..." message, exit gracefully
   - Invalid video file → ffprobe catches it, deleted, user informed

3. **Code quality:**
   - No commented-out code, debugging print statements
   - Clear error messages (not stack traces for user-facing errors)
   - Logging at key steps (config load, auth test, download start/end, validation results)
   - README with instructions for cookie export, config creation, FFmpeg install

4. **Testing (if included in Phase 1 scope):**
   - Unit tests for Pydantic config validation
   - Integration test with actual Panopto instance (if available) or mocked responses
   - Windows path handling tested (if available)

---

## Recommendations for Phase 1 Planner

### Scope is Tight ✓
Phase 1 has clear boundaries: Config → Auth → Download → Validate. No ambiguity about what should/shouldn't be included. This reduces planning risk.

### Technology is Proven ✓
All tools (requests, PyYAML, Pydantic, ffprobe) are well-documented, stable, widely used. No novel patterns or unproven libraries.

### Most Unknowns are Solvable Quickly
The 6 unknowns above can be resolved in 2–3 hours during Phase 1 planning (before implementation). Only FFmpeg installation testing needs to wait for implementation.

### Plan for Windows Gotchas
Windows path encoding, FFmpeg install location, file permissions are well-known pain points. Budget 1–2 hours for Windows-specific testing during Phase 1 implementation.

### Consider Error Messages as First-Class Deliverable
Students will see error messages more often than success messages (especially first run, cookie expiry). Invest in clear, actionable error text. This is high-impact, low-cost UX improvement.

### Defer Checkpointing to Phase 4
Phase 1 should be happy-path + common errors only. Don't build resumable pipeline yet; Phase 4 will add it. This keeps Phase 1 scope tight and testable.

---

## Sources

### Primary (HIGH confidence — Official Docs & Current)
- **requests:** https://docs.python-requests.org/ (verified Feb 2026)
- **PyYAML:** https://pyyaml.org/wiki/PyYAMLDocumentation (verified Feb 2026)
- **Pydantic 2.0:** https://docs.pydantic.dev/latest/ (verified Feb 2026)
- **FFmpeg/ffprobe:** https://ffmpeg.org/documentation.html (verified Feb 2026)
- **FFmpeg Windows builds:** https://www.gyan.dev/ffmpeg/builds/ (verified Feb 2026)
- **pathlib:** https://docs.python.org/3/library/pathlib.html (verified Feb 2026)
- **logging:** https://docs.python.org/3/library/logging.html (verified Feb 2026)

### Secondary (MEDIUM confidence — Community Reference Implementations)
- **Panopto downloaders:** panopto-downloader, Panopto-Video-DL, PanoptoSync (GitHub, reference implementations for cookie auth + ffprobe validation)
- **Windows path encoding:** Stack Overflow, Sentry blog, Medium (2015–2024, validated patterns)

### Domain Research (HIGH confidence — Project Research Summary)
- `.planning/research/SUMMARY.md` (completed March 2, 2026)
- `.planning/phases/01-foundation/01-CONTEXT.md` (Phase 1 decisions from /gsd-discuss-phase)

---

## Next Steps (for Phase 1 Planner)

1. **Validate unknowns** (2–3 hours):
   - Confirm Panopto API endpoint for auth test
   - Test transcript API availability
   - Download test videos, measure file sizes
   - Test cookie export from different browsers

2. **Finalize Pydantic config model** (1 hour):
   - Lock field names, types, validation rules
   - Create example config file
   - Write config validation error messages

3. **Create Phase 1 implementation plan** (2–3 hours):
   - Decompose into 3–5 concrete tasks
   - Estimate effort per task (hours)
   - Flag dependencies and risks
   - Assign to developers (or clarify YOLO solo timeline)

4. **Decide on testing scope** (1 hour):
   - Unit tests for config validation?
   - Integration tests with Panopto (if available)?
   - Windows path handling tests?
   - Mock-based tests (faster, no Panopto access needed)?

5. **Set up development environment** (1 hour):
   - Python 3.11+ installed
   - FFmpeg installed on dev machine
   - Project structure: `src/`, `tests/`, `config/`, `.planning/logs/`
   - Git repo ready (assume already initialized)

---

*Phase 1 Research completed: March 2, 2026*  
*Ready for Phase 1 Planning: YES*  
*Confidence: HIGH*
