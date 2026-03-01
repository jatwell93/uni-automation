# Automated Lecture Workflow

Process weekly Panopto lectures into structured study notes in one command.

**Key Features:**
- Download video and transcript from Panopto
- Validate files automatically (ffprobe checks)
- Clear error messages and recovery instructions
- Offline-first (all files stored locally)
- Cost-effective (< AUD $0.50/lecture using DeepSeek LLM)

**Status:** Phase 1 (Foundation) — Config, Auth, Download, Validate ✓

---

## Quick Start

### Prerequisites

- **Python 3.11+** (download from [python.org](https://www.python.org/) or Windows Store)
- **FFmpeg** (download from [gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/))
- **pip** (comes with Python)

### Installation

1. Clone repository and navigate to project:
   ```bash
   git clone <url>
   cd uni-automation
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Extract your Panopto cookies from browser (see **Configuration** below)

4. Create config file for your lecture (copy `config/example_week_05.yaml`)

### Running Phase 1

```bash
python run_week.py config/week_05.yaml
```

Expected output:
```
🔧 Loading config from config/week_05.yaml...
✓ Config validated
🔐 Testing Panopto authentication...
✓ Session valid (expires in 5 days)
📥 Downloading video...
✓ Downloaded video.mp4 (450MB)
🔍 Validating video...
✓ Video valid (62:15, H.264)
📄 Downloading transcript...
✓ Downloaded transcript.vtt
✓ Phase 1 complete
Files:
  - downloads/week_05/video.mp4 (450MB)
  - downloads/week_05/transcript.vtt
✓ Logs: .planning/logs/week_05.log
```

Files downloaded to: `downloads/week_05/`  
Logs available at: `.planning/logs/week_05.log`

---

## Configuration

Phase 1 requires a YAML configuration file specifying the lecture URL, slides path, and authentication.

### Required Fields

- `lecture.url` — Full Panopto URL (copy from browser address bar)
- `lecture.slide_path` — Path to PDF slides file (must exist)
- `paths.cookie_file` — Path to browser cookie JSON export
- `paths.output_dir` — Where to save downloaded files

### Optional Fields

- `metadata.course_name` — Course name (default: "Unknown Course")
- `metadata.week_number` — Week number (default: 1)
- `metadata.lecturer_name` — Lecturer name (default: "")
- `metadata.timestamp` — Timestamp (default: current time)

### Getting Your Panopto Cookies

To authenticate with Panopto, you need to export your session cookies from your browser:

1. Open Panopto in your browser and log in
2. Open DevTools: Press `F12` (Windows) or `Cmd+Option+I` (Mac)
3. Go to **Storage** tab (Chrome/Edge) or **Cookies** tab (Firefox)
4. Find domain: `panopto.university.edu` (or your institution's Panopto domain)
5. Right-click and select "Copy All as cURL" or export as JSON
6. Save to `cookies/panopto.json`
7. **Important:** Cookies expire after ~7 days; refresh before re-running lectures

**Note:** Cookies are sensitive. Never commit `cookies/` to git (already in `.gitignore`).

### Example

See `config/example_week_05.yaml` for a complete example. Copy and customize for each lecture:

```yaml
lecture:
  url: https://panopto.university.edu/Panopto/Pages/Viewer.aspx?id=abc123def456
  slide_path: slides/week_05.pdf

paths:
  cookie_file: cookies/panopto.json
  output_dir: downloads

metadata:
  course_name: Business Analytics
  week_number: 5
  lecturer_name: Dr. Smith
```

### Validation

When you run `python run_week.py config/week_05.yaml`, the system validates your config immediately:
- Missing required fields → Clear error listing what's needed
- Invalid paths → Error with full path and reason
- Non-writable directory → Error with permission details

Fix any validation errors before proceeding.

### Video Format Requirements

- Video codec: H.264 or H.265 (supported by most browsers/players)
- Duration: > 0 seconds
- File size: > ~100 MB for typical 60-min lecture (verified via ffprobe after download)

---

## Security & Privacy

### Cookie Storage

Panopto cookies contain your authentication session and must be stored securely:

1. **Never commit cookies to git** — Add `cookies/` to `.gitignore` (already done)
2. **File permissions** — Windows NTFS ACLs protect file (read-only for non-owner is recommended)
3. **Local storage only** — Cookies never uploaded or sent externally (except direct Panopto download)
4. **Periodic refresh** — Cookies expire after ~7 days; refresh before each lecture week

### Cookie Location

By default, cookies are stored in `cookies/panopto.json`:
- Config file specifies path: `paths.cookie_file: "cookies/panopto.json"`
- Change path in config if you prefer different location (e.g., `~/.panopto/cookies` for home dir)

### Recommended Setup

1. Create `cookies/` directory in project root: `mkdir cookies`
2. Export cookies from browser: DevTools → Storage → Export as JSON
3. Save to `cookies/panopto.json`
4. **DO NOT** edit or share this file

### Privacy Features (Phase 1)

- Raw video and audio files stored locally only (never uploaded)
- Transcript and slides stored locally only
- Cookies not logged anywhere except in local file

### Privacy Hardening (Phase 4)

- Temporary files cleaned up after processing
- PII (student names, emails) removed before LLM processing
- Google Drive sync optional (students can disable if preferred)

### Compliance Notes

- **Data residency:** All lectures stored on your local Windows machine
- **Offline-capable:** Phase 1 requires internet only for download; Phase 2+ works entirely offline
- **No external APIs in Phase 1:** Only Panopto authentication required

---

## Architecture

### Phase 1: Foundation (Current)
- **Configuration validation** (YAML + Pydantic)
- **Authentication** (Panopto session validation)
- **Download** (video + transcript)
- **Validation** (ffprobe, format checks)
- **Error handling** (comprehensive error messages, recovery instructions)
- **Logging** (file + console output with timestamps)

### Phase 2: Media Processing
- **Transcript processing** (cleanup, speaker identification)
- **Audio extraction** (silent segments, quality)
- **Slide extraction** (OCR, structure)

### Phase 3: Intelligence & Output
- **LLM integration** (summary, key concepts, review questions)
- **Obsidian formatting** (structured markdown, links)
- **Cost tracking** (token counting, model selection)

### Phase 4: Reliability
- **Error recovery** (checkpoints, retries, graceful degradation)
- **State management** (progress tracking, resume capability)
- **Privacy** (data encryption, automatic cleanup)

---

## Troubleshooting

### Error: "Config file not found"
- Check file path (use forward slashes `/`)
- Verify file exists: `ls config/week_05.yaml`
- Use correct path in command: `python run_week.py config/week_05.yaml`

### Error: "Cookies expired"
- Cookies are valid for ~7 days after export
- Refresh from browser: F12 → Storage → Cookies → Export
- Save to `cookies/panopto.json`
- Re-run: `python run_week.py config/week_05.yaml`

### Error: "FFmpeg not installed"
- Download from: [gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)
- Windows: Download portable ZIP, extract, add to PATH
- Or: Set `FFMPEG_HOME` env var to ffmpeg directory
- Verify: `ffprobe -version` should work

### Error: "Config validation failed"
- Check that all required fields are present:
  - `lecture.url` (Panopto video link)
  - `lecture.slide_path` (path to PDF)
  - `paths.cookie_file` (path to cookies JSON)
  - `paths.output_dir` (where to save files)
- Check that paths exist and are readable
- Check YAML syntax: `:` after keys, proper indentation

### Error: "File size suspicious"
- Downloaded file is too small (< 100MB for typical lecture)
- This usually means:
  1. Download was interrupted (partial file)
  2. Wrong Panopto URL
  3. Video is very short (< 10 minutes)
- Try again with fresh cookies

### Error: "Cannot reach Panopto"
- Check internet connection
- Check that Panopto URL is correct
- Verify Panopto domain matches your institution

### Performance Issues

**Slow download:**
- Normal for large files (450MB ≈ 2–5 min on typical internet)
- Video downloads at network speed (no optimization in Phase 1)

**Memory usage:**
- Phase 1 uses streaming download (no RAM bloat)
- System may use 100–200 MB total (config, cookies, logging)

**Disk space:**
- Each lecture ~450–600 MB
- Ensure output directory has space before running

---

## Project Structure

```
.
├── run_week.py                       # Main CLI entry point
├── requirements.txt                  # Python dependencies
├── README.md                         # This file
├── .gitignore                        # Exclude sensitive files
├── src/
│   ├── __init__.py                   # Package exports
│   ├── config.py                     # Pydantic config model + YAML loader
│   ├── models.py                     # Data classes (ConfigModel, AuthResult, etc.)
│   ├── auth.py                       # Panopto authentication
│   ├── downloader.py                 # Video + transcript download
│   ├── validator.py                  # Video validation (ffprobe)
│   └── logger.py                     # Logging setup
├── tests/
│   ├── test_config.py                # Config validation tests
│   ├── test_auth.py                  # Auth tests
│   ├── test_downloader.py            # Download tests
│   ├── test_validator.py             # Video validation tests
│   └── test_integration.py           # End-to-end pipeline tests
├── config/
│   └── example_week_05.yaml          # Example config file
├── cookies/                          # Panopto cookies (NOT committed)
│   └── panopto.json                  # Browser cookie export
├── downloads/                        # Downloaded media (NOT committed)
│   └── week_05/
│       ├── video.mp4                 # Panopto video
│       └── transcript.vtt            # Panopto transcript
├── .planning/
│   ├── logs/                         # Execution logs (NOT committed)
│   │   └── week_05.log               # Execution log with timestamps
│   ├── ROADMAP.md                    # 4-phase project plan
│   ├── REQUIREMENTS.md               # 46 requirements (v1)
│   └── phases/                       # Phase plans and summaries
└── .vscode/ / .idea/                 # IDE configuration (optional)
```

---

## Testing

### Run All Tests

```bash
pytest -xvs
```

### Run Specific Test File

```bash
pytest tests/test_config.py -xvs          # Config validation
pytest tests/test_auth.py -xvs            # Cookie + auth
pytest tests/test_downloader.py -xvs      # Download logic
pytest tests/test_validator.py -xvs       # ffprobe validation
pytest tests/test_integration.py -xvs     # End-to-end pipeline
```

### Test Coverage

Phase 1 includes 42+ unit tests covering:
- Config validation (YAML parsing, schema validation)
- Cookie loading (multiple browser formats)
- Session authentication (dual strategies with fallback)
- Video download (streaming, chunking, error cleanup)
- Video validation (ffprobe checks, format validation)
- Transcript download (optional, graceful fallback)
- Integration tests (full pipeline end-to-end)

All tests should pass before proceeding to Phase 2.

---

## Cost Model

**Per lecture (60 min):**
- Panopto authentication: Free
- Video download: Free (local only)
- LLM processing: ~$0.20–0.50 (DeepSeek / Claude Haiku, added in Phase 3)
- **Total:** ≤ AUD $0.50

**Recommended LLM routing:**
- DeepSeek for transcripts > 5000 tokens (~$0.20)
- Claude Haiku for shorter transcripts (~$0.50)

---

## Development & Testing

### Unit Tests

Unit tests for each component:

```bash
pytest tests/test_config.py -xvs          # Config validation
pytest tests/test_auth.py -xvs            # Cookie + auth
pytest tests/test_downloader.py -xvs      # Download logic
pytest tests/test_validator.py -xvs       # ffprobe validation
pytest tests/test_integration.py -xvs     # End-to-end pipeline
```

All tests should pass before proceeding to Phase 2.

### Integration Tests

Run end-to-end tests to verify complete pipeline:

```bash
pytest tests/test_integration.py -xvs
```

Tests cover:
- Happy path (full pipeline succeeds)
- Config validation errors
- Auth failures (expired cookies)
- Download errors (network, 404, 403)
- Validation failures (file too small, invalid format)
- Transcript optional (graceful skip on failure)

### Contributing

Phase 1 is a solo project (YOLO mode). For bug reports:
- Check `.planning/logs/` for detailed error messages
- Provide log file when reporting issues
- Check troubleshooting section above first

---

## Next Steps

### For Users

1. Extract browser cookies and save to `cookies/panopto.json`
2. Copy `config/example_week_05.yaml` and customize for your lecture
3. Run: `python run_week.py config/week_05.yaml`
4. Check logs in `.planning/logs/week_05.log` if issues occur

### For Developers

Phase 1 foundation complete. Next phases:
- **Phase 2:** Clean transcript, extract audio, extract slide text
- **Phase 3:** Generate Feynman-structured notes using LLM (OpenRouter API)
- **Phase 4:** Add checkpointing, error recovery, privacy controls, Google Drive sync

Check `.planning/ROADMAP.md` for detailed phase breakdown.

---

*Last updated: March 2, 2026*  
*Phase 1 (Foundation) Complete*
