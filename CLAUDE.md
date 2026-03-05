# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Generate notes for a lecture (main workflow)
python generate_notes.py --course MIS271 --week 1 --session lecture
python generate_notes.py --course MIS271 --week 1 --estimate-only   # check cost without API call
python generate_notes.py --course MIS271 --weeks 1-5 --session lecture  # batch
python generate_notes.py --course MIS271 --week 1 --model claude-3-haiku-20240307

# Folder management (for tracking downloaded sessions)
python process_lecture.py --course MIS271 --week 1 --session lecture  # show status
python process_lecture.py --create MIS271 1          # create lecture + prac folders
python process_lecture.py --create-all MIS271        # create all 22 folders
python process_lecture.py --list                     # list all downloaded sessions
python process_lecture.py --stats                    # show progress stats

# Run the full pipeline for a lecture (legacy - requires Panopto URL in YAML config)
python run_week.py config/week_05.yaml

# Resume from a failed checkpoint
python run_week.py config/week_05.yaml --retry

# Run all tests
pytest -xvs

# Run a single test
pytest tests/test_config.py::test_validate_config -xvs

# Run tests with coverage
pytest --cov=src tests/ -xvs

# Run tests by phase
pytest tests/test_config.py tests/test_auth.py tests/test_downloader.py tests/test_validator.py -xvs  # Phase 1
pytest tests/test_audio_extractor.py tests/test_transcript_processor.py tests/test_slide_extractor.py -xvs  # Phase 2
pytest tests/test_llm_generator.py tests/test_obsidian_writer.py -xvs  # Phase 3
pytest tests/test_checkpoint.py tests/test_state.py -xvs  # Phase 4
```

## Architecture

The project is a 4-phase pipeline that converts Panopto lecture recordings into structured Obsidian study notes.

### Entry Point

`run_week.py` — CLI that accepts a YAML config file. Handles Phase 1 (download + validate) directly, then delegates Phase 2–4 to `src/pipeline.py`.

```
run_week.py
  ├─ Phase 1: Download & Validate (inline)
  │   ├─ src/auth.py       — Cookie-based Panopto auth
  │   ├─ src/downloader.py — Streaming video + transcript download
  │   └─ src/validator.py  — ffprobe file validation
  │
  └─ Phase 2–4: src/pipeline.py (run_lecture_pipeline)
      ├─ src/transcript_processor.py — Cleans VTT, strips PII
      ├─ src/slide_extractor.py      — PDF text extraction + OCR fallback
      ├─ src/llm_generator.py        — OpenRouter API (DeepSeek default)
      ├─ src/cost_tracker.py         — Token counting + AUD budget enforcement
      ├─ src/obsidian_writer.py      — Writes YAML-frontmatter Markdown notes
      ├─ src/gdrive_sync.py          — Optional Google Drive backup
      ├─ src/checkpoint.py           — JSON checkpoint persistence
      ├─ src/state.py                — Stage skip logic for --retry
      ├─ src/error_handler.py        — Transient vs fatal error categorization
      └─ src/temp_manager.py         — Singleton for temp file cleanup
```

### Configuration (`src/config.py`)

Pydantic v2 models load from YAML. Key top-level fields:
- `lecture.url` + `lecture.slide_path` — Panopto URL and PDF slides
- `paths.cookie_file` + `paths.output_dir` — file locations
- `metadata.course_name`, `metadata.week_number`
- `openrouter_api_key`, `llm_model`, `llm_budget_aud`, `llm_safety_buffer`
- `obsidian_vault_path`, `obsidian_note_subfolder`
- `gdrive_sync_enabled`, `gdrive_sync_folder`

The `openrouter_api_key` field supports environment variable substitution: if the value is all-uppercase with underscores, it looks up that env var.

### Multi-Course Support (`src/course_manager.py`)

`CourseManager` handles multi-course folder structure. Course codes follow the pattern `[A-Z]{3}\d{3}` (e.g., `MIS271`, `CHM101`). Courses in `KNOWN_COURSES` get custom metadata; any other valid code uses defaults (11 weeks, folder named after course code).

Downloads are organized as:
```
downloads/{COURSE_CODE}_week_{NN}_{type}/{subfolder}/
```

### Pipeline Reliability

- **Checkpoints**: Saved as JSON after each major stage (`llm`, `output`). Located in `.planning/checkpoints/`.
- **Retry logic**: `run_stage()` in `pipeline.py` retries transient errors (network, API) up to 3× with exponential backoff via `ErrorHandler`. Fatal errors (invalid config, auth) fail immediately.
- **Cost control**: `CostTracker` counts tokens with `tiktoken` before the API call. If estimated cost exceeds `llm_budget_aud × (1 + llm_safety_buffer)`, transcript is truncated (binary search sampling). Budget alerts fire at 1.67× budget per lecture or 3.00 AUD/week.
- **PII detection**: `PIIDetector` scans transcript for names/emails before LLM call (controlled by `remove_pii_from_transcript`).
- **Temp cleanup**: `TempFileManager` is a singleton; `cleanup_all()` runs in the `finally` block regardless of success/failure.

### Logging

Logs written to `.planning/logs/week_{NN}.log`. The custom `get_logger()` in `src/logger.py` supports `stage_name` and `recovery_action` fields on log records.

### Key External Dependencies

- **ffmpeg/ffprobe** — must be on PATH (audio extraction + video validation)
- **OpenRouter API** — LLM generation via OpenAI-compatible client (`openai` package)
- **pdfplumber** — primary PDF slide text extraction; **EasyOCR** is optional (uncomment in `requirements.txt`) for scanned PDFs
- **tiktoken** — token counting before API calls
- **tenacity** — retry decorators (used in LLM generator)

### Sensitive Files (Never Commit)

- `cookies/panopto.json` — Panopto session cookies (expire ~7 days)
- `.env` — OpenRouter API key
- `downloads/` — raw video/audio files
- `.planning/logs/` + `.planning/checkpoints/`
