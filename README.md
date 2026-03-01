# Lecture Processing Pipeline

Automated system to process weekly university lectures—download video, extract transcripts, generate structured study notes, and save to Obsidian vault.

**Goal:** Process 1 lecture with `python run_week.py config/week_05.yaml`, outputs appear in Obsidian vault in < 2 min, cost ≤ AUD $0.50, no manual intervention after setup.

---

## Quick Start

1. **Create a config file** (copy `config/example_week_05.yaml`)
2. **Extract browser cookies** (see below)
3. **Run the pipeline:** `python run_week.py config/week_05.yaml`
4. **Check outputs** in your Obsidian vault

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

See `config/example_week_05.yaml` for a complete example. Copy and customize for each lecture.

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

### Security & Privacy

- Cookie file stored locally, never uploaded
- Config file should NOT contain sensitive information (cookies stored separately)
- Recommended: Add `cookies/` to `.gitignore` (already done)

---

## Architecture

### Phase 1: Foundation
- **Configuration validation** (YAML + Pydantic)
- **Authentication** (Panopto session validation)
- **Download** (video + transcript)
- **Validation** (ffprobe, format checks)

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

## Development

### Test Suite

Run all tests:
```bash
pytest -xvs
```

Run specific test file:
```bash
pytest src/test_config.py -xvs
```

### Project Structure

```
.
├── run_week.py              # Main CLI entry point
├── src/
│   ├── __init__.py          # Package exports
│   ├── config.py            # Pydantic config model + YAML loader
│   ├── models.py            # Data classes (ConfigModel, AuthResult, etc.)
│   ├── auth.py              # Panopto authentication
│   ├── downloader.py        # Video + transcript download
│   ├── validator.py         # Video validation (ffprobe)
│   ├── logger.py            # Logging setup
│   └── test_*.py            # Unit tests
├── config/
│   └── example_week_05.yaml # Example config file
├── cookies/                 # Browser cookies (in .gitignore)
├── downloads/               # Downloaded media (in .gitignore)
├── .planning/
│   ├── logs/                # Execution logs
│   ├── ROADMAP.md           # 4-phase project plan
│   ├── REQUIREMENTS.md      # 46 requirements (v1)
│   └── phases/              # Phase plans and summaries
└── .gitignore              # Exclude sensitive files
```

---

## Requirements

**Python 3.11+** with dependencies:
- `pydantic` — Config validation
- `pyyaml` — YAML parsing
- `requests` — HTTP client
- `tenacity` — Retry logic
- `ffmpeg` / `ffprobe` — Video processing
- `pdfplumber` — PDF extraction
- `openai` — LLM integration (OpenRouter)

Install: `pip install -r requirements.txt`

---

## Pipeline Stages

Each `python run_week.py` execution follows:

1. **Config Load** — Validate YAML, check file paths, verify permissions
2. **Auth Test** — Load cookies, validate Panopto session
3. **Download** — Stream video + transcript (8KB chunks, cleanup on failure)
4. **Validation** — ffprobe check (size, duration, codec)
5. **Progress** — Log each stage, clear error messages on failure

---

## Troubleshooting

### "Config file not found"
- Check file path (use forward slashes `/`)
- Verify file exists: `ls config/week_05.yaml`

### "Invalid URL"
- Must start with `http://` or `https://`
- Copy full URL from browser address bar, not shortened link

### "Slide path does not exist"
- Verify PDF file exists
- Use full path or path relative to current directory

### "Output directory not writable"
- Check directory permissions
- Verify parent directory exists and is writable

### "Config validation failed"
- Check YAML syntax (`:` after keys, proper indentation)
- Verify all required fields present
- Run with `-v` flag for detailed error output

---

## Cost Model

**Per lecture (60 min):**
- Panopto authentication: Free
- Video download: Free (local only)
- LLM processing: ~$0.20–0.50 (DeepSeek / Claude Haiku)
- **Total:** ≤ AUD $0.50

**Recommended LLM routing:**
- DeepSeek for transcripts > 5000 tokens (~$0.20)
- Claude Haiku for shorter transcripts (~$0.50)

---

## Next Steps

1. Extract browser cookies and save to `cookies/panopto.json`
2. Copy `config/example_week_05.yaml` and customize
3. Run: `python run_week.py config/week_05.yaml`
4. Check logs in `.planning/logs/week_05.log`

---

*Last updated: March 2, 2026*
