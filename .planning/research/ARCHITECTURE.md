# Architecture Research: Automated Lecture Workflow

**Domain:** Media processing automation pipeline (video → transcript → notes)
**Researched:** 2026-03-02
**Confidence:** HIGH (multiple authoritative sources verify patterns)

## Standard Architecture

### System Overview

The lecture workflow is a stateful ETL pipeline with local-first processing and fine-grained error recovery. Data flows sequentially through validation, transformation, and storage stages with checkpoint support for resume-on-failure.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Input & Configuration                           │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │ CLI Entrypoint│  │ YAML Config  │  │ Lecture Metadata (URLs, etc)│  │
│  │  (typer/     │  │ (lecture.yml)│  │                              │  │
│  │  argparse)   │  │              │  │                              │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────────┬─────────────┘  │
│         └────────────────────────────────┬─────────────┘                │
├─────────────────────────────────────────┴──────────────────────────────┤
│                   Pipeline Orchestrator (Main Controller)                │
│  - Reads config → validates → logs → manages state → coordinates steps  │
├─────────────────────────────────────────────────────────────────────────┤
│                        Execution Stages (Sequential)                     │
├─────────────────────────────────────────────────────────────────────────┤
│  Stage 1: Download & Extract                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │  Panopto     │  │   Transcript │  │  State Check                 │  │
│  │  Downloader  │  │   Extractor  │  │  (skip if cached)            │  │
│  │(auth+cookies)│  │   (.vtt/.txt)│  │                              │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────────┬─────────────┘  │
│         └────────────────────────────────┬─────────────┘                │
├────────────────────────────────┬─────────────────────────────────────────┤
│  Stage 2: Transform                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │  FFmpeg      │  │ Transcript   │  │  Slide Text                  │  │
│  │  Audio       │  │  Cleaner     │  │  Extractor                   │  │
│  │  Extractor   │  │  (timestamps,│  │  (OCR fallback)              │  │
│  │              │  │   filler)    │  │                              │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────────┬─────────────┘  │
│         └────────────────────────────────┬─────────────┘                │
├────────────────────────────────┬─────────────────────────────────────────┤
│  Stage 3: Sync to Google Drive                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Copy processed files to Google Drive sync folder (G:\ or equiv) │   │
│  └──────────────────────────────┬─────────────────────────────────┘   │
├────────────────────────────────┬─────────────────────────────────────────┤
│  Stage 4: AI Note Generation                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │  OpenRouter  │  │ Feynman      │  │  Markdown                    │  │
│  │  API Call    │  │  Formatter   │  │  Writer                      │  │
│  │(DeepSeek/    │  │  (summary,   │  │  (to Obsidian vault)         │  │
│  │ Haiku)       │  │   concepts)  │  │                              │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────────┬─────────────┘  │
│         └────────────────────────────────┬─────────────┘                │
├─────────────────────────────────────────────────────────────────────────┤
│                           Local Storage                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────────────┐  │
│  │ Cache dir│  │ State    │  │ Logs     │  │ Obsidian vault         │  │
│  │(video,   │  │(.json)   │  │(.log)    │  │(finalized notes)       │  │
│  │audio,    │  │          │  │          │  │                        │  │
│  │transcript)│  │          │  │          │  │                        │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Communication |
|-----------|----------------|-----------------|
| **CLI Entrypoint** | Parse arguments, validate inputs, dispatch to orchestrator | → Orchestrator |
| **Configuration Manager** | Load & validate YAML, merge CLI overrides, provide defaults | ← CLI, → Orchestrator |
| **Pipeline Orchestrator** | Coordinate stage execution, manage state, handle errors, log progress | ← All stages, → State Manager |
| **Panopto Downloader** | Authenticate with cookies, download video, handle auth expiry | → Cache, State Manager |
| **Transcript Extractor** | Fetch .vtt/.txt transcripts from Panopto API or embedded data | → Cache, State Manager |
| **FFmpeg Audio Extractor** | Call ffmpeg subprocess, extract audio from video, handle errors | → Cache, State Manager |
| **Transcript Cleaner** | Remove timestamps, filler words, redundancy; compress for LLM | → Cleaner output |
| **Slide Text Extractor** | Read PDF metadata, OCR images if needed, fallback to manual | → Slide text output |
| **Google Drive Sync** | Copy files to local Drive sync folder (no API required) | → Sync folder |
| **OpenRouter API Client** | Call LLM with transcript + slide text, handle rate limits | → Note Generator |
| **Feynman Note Generator** | Format API response into summary/concepts/examples/questions | → Markdown Writer |
| **Markdown Writer** | Write notes to Obsidian vault in flat structure | → Obsidian vault |
| **State Manager** | Persist progress to .json, enable checkpoint/resume | ← All stages |
| **Error Handler** | Categorize errors, retry with backoff, log for debugging | ← All stages |
| **Logger** | Structured logging (progress, errors, timing) to file + console | ← All stages |

## Recommended Project Structure

```
lecture-automation/
├── src/
│   ├── main.py                    # CLI entrypoint (typer-based)
│   ├── config.py                  # Configuration loading (YAML + Pydantic)
│   ├── orchestrator.py            # Pipeline controller
│   ├── state.py                   # Checkpoint & state persistence
│   │
│   ├── stages/                    # Pipeline stages
│   │   ├── __init__.py
│   │   ├── download.py            # Panopto video/transcript
│   │   ├── extract_audio.py       # FFmpeg audio extraction
│   │   ├── clean_transcript.py    # Transcript preprocessing
│   │   ├── extract_slides.py      # PDF → text (metadata + OCR)
│   │   ├── generate_notes.py      # LLM call + Feynman formatting
│   │   └── save_output.py         # Write to Obsidian vault
│   │
│   ├── utils/                     # Reusable utilities
│   │   ├── __init__.py
│   │   ├── file_ops.py            # File I/O, caching
│   │   ├── http_client.py         # Requests with retry/backoff
│   │   ├── ffmpeg_wrapper.py      # FFmpeg subprocess wrapper
│   │   ├── logging.py             # Structured logging
│   │   ├── errors.py              # Custom exceptions
│   │   └── validators.py          # Input validation (Pydantic)
│   │
│   └── integrations/              # External services
│       ├── __init__.py
│       ├── panopto.py             # Panopto API & auth
│       ├── openrouter.py          # OpenRouter LLM API
│       └── obsidian.py            # Obsidian vault writer
│
├── config/
│   ├── lecture_template.yml       # Example lecture config
│   └── defaults.yml               # System defaults
│
├── tests/
│   ├── test_config.py
│   ├── test_orchestrator.py
│   ├── test_stages/
│   └── fixtures/                  # Test data (sample videos, configs)
│
├── scripts/
│   ├── setup.sh                   # Install deps, setup paths
│   └── run_week.sh                # Convenience wrapper
│
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # Package metadata
├── .env.example                   # API keys template
├── README.md
└── lecture.yml                    # User's lecture config (not in repo)
```

### Structure Rationale

- **`src/main.py`** — Single CLI entry point using Typer. All commands dispatch through `run_week(week_number)` or similar.
- **`config.py`** — Centralized config loading. Merge YAML + CLI args + environment variables in priority order. Return validated Pydantic model.
- **`orchestrator.py`** — Coordinates stage execution. Checks state before each step, catches exceptions, logs, triggers retries.
- **`stages/`** — Each stage is a separate module with a `run(state: PipelineState) -> PipelineState` signature. Pure functions for testability.
- **`utils/`** — Shared concerns (logging, HTTP, subprocess). Not coupled to specific stages.
- **`integrations/`** — External service clients (Panopto, OpenRouter, Obsidian). Easier to mock/test.
- **Tests alongside code** — Test file mirrors source structure (`test_stages/test_download.py` → `stages/download.py`).

## Architectural Patterns

### Pattern 1: Stateful ETL with Checkpoint/Resume

**What:** Each stage writes its output + metadata to a state file (`.json`). On re-run, pipeline checks state before executing each stage.

**When to use:** Long-running processes (downloading, LLM calls) need recovery from failure without losing work.

**Trade-offs:**
- ✅ Users can re-run failed lectures without re-downloading/re-processing everything
- ✅ Easy to debug: state file shows exactly where pipeline stopped
- ✅ Cost-efficient: avoids duplicate LLM calls
- ❌ Requires careful state schema design and validation
- ❌ Mutable state can be tricky to reason about

**Example:**

```python
# state.py
from dataclasses import dataclass, asdict
from pathlib import Path
import json

@dataclass
class StageState:
    stage_name: str
    status: str  # 'pending', 'running', 'completed', 'failed'
    output_path: str | None = None
    error: str | None = None
    timestamp: str = None

@dataclass
class PipelineState:
    lecture_id: str
    week_number: int
    stages: dict[str, StageState]  # {stage_name: state}
    
    def to_json(self, path: Path):
        path.write_text(json.dumps(asdict(self), indent=2))
    
    @classmethod
    def from_json(cls, path: Path):
        if not path.exists():
            return cls(lecture_id="", week_number=0, stages={})
        return cls(**json.loads(path.read_text()))
    
    def stage_completed(self, stage_name: str) -> bool:
        return self.stages.get(stage_name, {}).status == 'completed'

# orchestrator.py
def run_pipeline(config: LectureConfig) -> PipelineState:
    state_file = Path(config.cache_dir) / f"week_{config.week}.state.json"
    state = PipelineState.from_json(state_file)
    
    stages = [
        ('download', stages.download.run),
        ('extract_audio', stages.extract_audio.run),
        ('clean_transcript', stages.clean_transcript.run),
        ('generate_notes', stages.generate_notes.run),
    ]
    
    for stage_name, stage_fn in stages:
        if state.stage_completed(stage_name):
            logger.info(f"✓ {stage_name} already completed, skipping")
            continue
        
        try:
            logger.info(f"→ Starting {stage_name}...")
            state = stage_fn(state)
            state.stages[stage_name].status = 'completed'
            logger.info(f"✓ {stage_name} completed")
        except Exception as e:
            state.stages[stage_name].status = 'failed'
            state.stages[stage_name].error = str(e)
            logger.error(f"✗ {stage_name} failed: {e}")
            state.to_json(state_file)
            raise PipelineError(f"Pipeline failed at {stage_name}") from e
        
        state.to_json(state_file)  # Persist after each stage
    
    return state
```

### Pattern 2: Configuration as Code (YAML + Pydantic)

**What:** Lecture metadata lives in `lecture.yml` (URLs, metadata, paths). Configuration is validated with Pydantic, merged with CLI args and defaults.

**When to use:** Automatable workflows where users need to specify lecture-specific data without hardcoding.

**Trade-offs:**
- ✅ Human-readable configuration
- ✅ Type validation catches errors early
- ✅ CLI args can override YAML (flexibility)
- ❌ Requires users to understand YAML syntax

**Example:**

```python
# config.py
from pydantic import BaseModel, Field, validator
from pathlib import Path
import yaml

class LectureConfig(BaseModel):
    week_number: int
    lecture_title: str
    
    panopto_video_url: str
    panopto_transcript_url: str | None = None
    
    slides_pdf_path: Path | None = None
    
    cache_dir: Path = Field(default_factory=lambda: Path.home() / ".lecture_cache")
    obsidian_vault_path: Path = Field(default_factory=lambda: Path.home() / "Obsidian" / "Notes")
    google_drive_sync_path: Path | None = None
    
    llm_model: str = "deepseek-chat"  # or "claude-3-haiku"
    llm_max_tokens: int = 2000
    
    @validator('cache_dir', 'obsidian_vault_path', pre=True)
    def expand_paths(cls, v):
        if isinstance(v, str):
            return Path(v).expanduser()
        return v

def load_config(yaml_file: Path, week_override: int | None = None) -> LectureConfig:
    data = yaml.safe_load(yaml_file.read_text())
    config = LectureConfig(**data)
    
    if week_override:
        config.week_number = week_override
    
    return config

# lecture.yml (user file)
week_number: 5
lecture_title: "Business Analytics - Week 5"
panopto_video_url: "https://..."
panopto_transcript_url: "https://..."
slides_pdf_path: "~/Google Drive/Lectures/Week_5_slides.pdf"
cache_dir: "~/lecture_cache"
obsidian_vault_path: "~/Obsidian/Notes"
google_drive_sync_path: "G:/"
```

### Pattern 3: Error Handling with Exponential Backoff + Dead Letter Queue

**What:** Network calls (Panopto, OpenRouter) use exponential backoff (wait 1s → 2s → 4s). Failures are categorized (retryable vs fatal). Fatal errors go to dead letter file for manual review.

**When to use:** Integration with external services that may have transient failures.

**Trade-offs:**
- ✅ Transient failures don't crash the pipeline
- ✅ Cost-efficient (avoids redundant LLM calls)
- ✅ Clear error audit trail
- ❌ Adds complexity; needs tuning per service

**Example:**

```python
# utils/http_client.py
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class ResilientHTTPClient:
    def __init__(self, max_retries: int = 3, timeout: int = 30):
        self.max_retries = max_retries
        self.timeout = timeout
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)  # 1s, 2s, 4s
    )
    def get(self, url: str, headers: dict | None = None) -> httpx.Response:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            return resp

# errors.py
class RetryableError(Exception):
    """Network, rate limiting, temporary server errors"""
    pass

class FatalError(Exception):
    """Auth failure, malformed config, missing files"""
    pass

# orchestrator.py — Dead Letter Queue
def run_with_dlq(state: PipelineState, stage_fn, stage_name: str) -> PipelineState:
    dlq_file = Path(state_dir) / f"dlq_{stage_name}.json"
    
    try:
        return stage_fn(state)
    except RetryableError as e:
        # Already retried by @retry decorator, moving to DLQ
        dlq = json.loads(dlq_file.read_text() if dlq_file.exists() else "[]")
        dlq.append({
            'stage': stage_name,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'state_snapshot': asdict(state)
        })
        dlq_file.write_text(json.dumps(dlq, indent=2))
        raise PipelineError(f"{stage_name} failed after retries. See {dlq_file} for details.")
    except FatalError as e:
        raise  # Re-raise immediately, don't retry
```

### Pattern 4: Pipeline Stages as Composable Functions

**What:** Each stage is a pure function: `stage_run(state: PipelineState, config: LectureConfig) -> PipelineState`. No side effects except writing to cache/state file.

**When to use:** Simplify testing, enable composition, make pipeline logic clear.

**Trade-offs:**
- ✅ Easy to test (mock inputs, check outputs)
- ✅ Easy to understand pipeline flow
- ✅ Can reorder/skip stages with state management
- ❌ Requires discipline to keep stages pure (avoid global state)

**Example:**

```python
# stages/download.py
def run(state: PipelineState, config: LectureConfig) -> PipelineState:
    """Download video and transcript from Panopto."""
    
    video_path = config.cache_dir / f"week_{config.week_number}.mp4"
    transcript_path = config.cache_dir / f"week_{config.week_number}.vtt"
    
    # Skip if already cached
    if video_path.exists():
        logger.info(f"Using cached video: {video_path}")
    else:
        logger.info(f"Downloading video from {config.panopto_video_url}...")
        # Download logic here
        video_path.write_bytes(...)
    
    if transcript_path.exists():
        logger.info(f"Using cached transcript: {transcript_path}")
    else:
        logger.info(f"Downloading transcript...")
        transcript_path.write_text(...)
    
    state.stages['download'] = StageState(
        stage_name='download',
        status='completed',
        output_path=str(video_path)
    )
    
    return state
```

### Pattern 5: Config-Driven Retry & Timeout Policies

**What:** Each external service (Panopto, OpenRouter) has its own retry policy defined in config. Easy to adjust without code changes.

**When to use:** Different services have different reliability profiles.

**Trade-offs:**
- ✅ Operators can tune without redeploying
- ✅ Clear visibility into retry policies
- ❌ Config can become verbose

**Example:**

```yaml
# config.yml
retry_policy:
  panopto:
    max_attempts: 4
    initial_wait_seconds: 1
    max_wait_seconds: 30
    backoff_multiplier: 2
    retryable_codes: [429, 500, 502, 503]  # Rate limit, server errors
  
  openrouter:
    max_attempts: 3
    initial_wait_seconds: 2
    max_wait_seconds: 60
    backoff_multiplier: 1.5
    retryable_codes: [429, 500, 502, 503]
  
  ffmpeg:
    timeout_seconds: 300  # 5 min max for audio extraction
    max_attempts: 1  # Don't retry FFmpeg; it's local & deterministic
```

## Data Flow

### Main Processing Flow

```
┌─────────────────────────────────────────────────────────────┐
│  User runs: python run_week.py week_05                      │
│             (or: python -m lecture_automation week 5)        │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│  CLI entrypoint parses args                                  │
│  - week_number from positional arg                           │
│  - config file path from --config flag (default: ./lecture.yml)│
│  - overrides (--cache-dir, --obsidian-path, etc.)            │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│  Load & validate LectureConfig from YAML                     │
│  Merge with CLI overrides                                    │
│  Pydantic validates all fields                               │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│  Create pipeline state from checkpoint file (or new)         │
│  State tracks which stages completed, where errors occurred  │
└──────────────────────┬──────────────────────────────────────┘
                       ↓ Sequential Execution
┌──────────────────────────────────────────────────────────────┐
│  STAGE 1: Download                                           │
│  If NOT completed in state:                                  │
│    1.1 Download Panopto video using cookies                  │
│    1.2 Extract/download transcript (.vtt)                    │
│    1.3 Save both to cache_dir                                │
│  Update state + checkpoint to disk                           │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│  STAGE 2: Extract Audio                                      │
│  If NOT completed in state:                                  │
│    2.1 Call ffmpeg: video → audio (WAV/MP3)                  │
│    2.2 Save audio to cache_dir                               │
│  Update state + checkpoint to disk                           │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│  STAGE 3: Clean Transcript                                   │
│  If NOT completed in state:                                  │
│    3.1 Parse .vtt file (remove timestamps, speaker labels)   │
│    3.2 Remove filler words ("um", "uh", "like", etc.)        │
│    3.3 Deduplicate adjacent lines                            │
│    3.4 Return token-optimized text                           │
│  Save cleaned transcript to cache_dir                        │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│  STAGE 4: Extract Slide Text                                 │
│  If NOT completed in state:                                  │
│    4.1 Open PDF, extract metadata (title, text from objects) │
│    4.2 If text extraction fails, use fallback:               │
│        - Log warning, mark for manual OCR                    │
│        - Return empty string (notes without slides)          │
│    4.3 Concatenate all slide text                            │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│  STAGE 5: Sync to Google Drive (optional)                    │
│  If google_drive_sync_path is set:                           │
│    5.1 Copy video, audio, cleaned transcript to sync folder  │
│    5.2 Keep local cache untouched                            │
│  If NOT set, skip this stage (local-only mode)               │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│  STAGE 6: Generate Notes                                     │
│  If NOT completed in state:                                  │
│    6.1 Combine: cleaned_transcript + slide_text              │
│    6.2 Build OpenRouter API prompt:                          │
│        - System: "You are a Feynman-style note generator"    │
│        - User: "Summarize this lecture into: summary,        │
│                 key concepts, worked examples, formulas,     │
│                 common pitfalls, review questions"           │
│    6.3 Call OpenRouter (with retry policy)                   │
│    6.4 Parse response into structured fields                 │
│  Save raw LLM response to cache_dir (for debugging)          │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│  STAGE 7: Write to Obsidian Vault                            │
│  If NOT completed in state:                                  │
│    7.1 Format notes as Markdown:                             │
│        # Week 5: Lecture Title                               │
│        ## Summary                                            │
│        [summary text]                                        │
│        ## Key Concepts                                       │
│        [bullet list]                                         │
│        ...                                                   │
│    7.2 Write to: vault_path/CourseName/Week_5.md             │
│    7.3 Create course folder if missing                       │
│  Update state + checkpoint                                   │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│  SUCCESS                                                     │
│  Log summary: "✓ Week 5 processed in 3min 45sec"             │
│  Cost: $0.42 (OpenRouter LLM call)                           │
│  Notes written to: vault_path/Week_5.md                      │
└──────────────────────────────────────────────────────────────┘
```

### Error Recovery Flow

```
Any stage fails
    ↓
Catch exception → categorize (Retryable vs Fatal)
    ↓
    ├─ RETRYABLE (network, rate limit):
    │   Exponential backoff retry (wait 1s → 2s → 4s)
    │   ↓
    │   Success? → Continue pipeline
    │   Still failing? → Add to Dead Letter Queue (DLQ)
    │                  → Log error + state snapshot
    │                  → Exit with error code
    │
    ├─ FATAL (auth, config, missing file):
    │   Immediate exit, don't retry
    │   → Log error details
    │   → User fixes config/inputs, re-runs
    │
    └─ RECOVERABLE (state checkpoint exists):
        User can re-run same command
        ↓
        Load state from checkpoint
        Skip completed stages
        Resume from failed stage
        (This avoids re-downloading, re-processing)
```

## Integration Points

### External Services

| Service | Integration Pattern | Error Handling | Notes |
|---------|---------------------|----------------|-------|
| **Panopto API** | HTTP client with cookie-based auth; no OAuth needed | Retryable: 429 (rate limit), 5xx (server errors); Fatal: 401 (expired cookies), 404 (missing content) | User refreshes cookies weekly from browser; stores in `.env` or secure config |
| **FFmpeg** | Subprocess wrapper (`subprocess.run()`) with timeout | Retryable: timeout errors, codec issues; Fatal: missing ffmpeg binary | Assumed installed on Windows; detect on startup, provide install URL if missing |
| **OpenRouter API** | HTTP POST with JSON payload; key-based auth | Retryable: 429 (rate limit), 5xx; Fatal: 400 (bad request), 401 (invalid key), 403 (quota) | Cost-optimized: DeepSeek $0.14/M input tokens vs Claude $3.75/M; track usage in state |
| **Local Google Drive Sync** | `shutil.copytree()` / `Path.copy()` | Retryable: disk full, permission denied; Fatal: path doesn't exist | No OAuth; folder must be manually synced to G:\ already |
| **Obsidian Vault** | Direct Markdown file writes to local folder | Retryable: permission denied, disk full; Fatal: invalid path | No API required; Obsidian auto-detects new files |

### Internal Boundaries

| Module Boundary | Communication | Notes |
|-----------------|---------------|-------|
| **CLI → Orchestrator** | Typed config object + callback functions | CLI only parses; orchestrator executes |
| **Orchestrator → Stages** | Config + PipelineState (in); PipelineState (out) | Stages are pure functions, stateless from their perspective |
| **Stages → Utils** | Dependency injection (HTTP client, logger, file ops) | Utils don't know about pipeline context |
| **Utils → Integrations** | Direct HTTP/subprocess calls | Integrations are thin wrappers around external services |
| **All stages → State Manager** | Async/sync write to `.json` checkpoint file | State manager is the source of truth for recovery |
| **All stages → Logger** | Structured logging (progress, errors, timing) | Logged to file + console; helpful for debugging |

## Anti-Patterns

### Anti-Pattern 1: Monolithic Stage Function

**What people do:**
```python
def run_week():
    # Download, extract, clean, generate, save — all in one function
    download_video()
    download_transcript()
    extract_audio()
    clean_transcript()
    generate_notes()
    save_notes()
```

**Why it's wrong:**
- If one step fails, no recovery without re-doing everything
- Hard to test individual steps
- Hard to skip completed steps on re-run
- Mixing concerns (I/O, transformation, validation)

**Do this instead:**
- Break into stages with clear inputs/outputs
- Each stage reads from state, performs work, updates state
- Orchestrator coordinates stages sequentially
- Easy to skip, retry, or debug individual stages

### Anti-Pattern 2: Global State / Configuration

**What people do:**
```python
# global_config.py
CONFIG = load_yaml("lecture.yml")

# In any module:
from global_config import CONFIG
video_path = CONFIG.cache_dir / "video.mp4"
```

**Why it's wrong:**
- Hard to test (must mock global)
- Multiple config sources conflict
- No per-lecture override capability
- Can't parallelize runs with different configs

**Do this instead:**
- Pass `config` and `state` objects as parameters
- Dependency injection pattern
- Config validated upfront, immutable during run
- Each function explicit about dependencies

### Anti-Pattern 3: Silent Failures / Logging to Console Only

**What people do:**
```python
try:
    download_video()
except Exception as e:
    print(f"Error: {e}")  # Where did this go? Lost on scroll.
```

**Why it's wrong:**
- Errors disappear on scroll
- No audit trail for debugging
- Hard to diagnose failures after the fact

**Do this instead:**
- Structured logging to file + console
- Include timestamps, stage name, error type, context
- Save state snapshot on failure
- DLQ for failed items (for manual review)

### Anti-Pattern 4: No Timeout on Network Calls

**What people do:**
```python
response = requests.get(panopto_url)  # Hangs forever if server is slow
```

**Why it's wrong:**
- Pipeline can hang indefinitely
- No user feedback during failure
- Wastes time and tokens (if LLM call)

**Do this instead:**
- Set explicit timeout (e.g., 30s)
- Use exponential backoff with max attempts
- Fail fast if service is down

### Anti-Pattern 5: No State Tracking

**What people do:**
```python
# Run 1: Download video (succeeds), extract audio (fails)
# Run 2: Start over, re-download everything
```

**Why it's wrong:**
- Wastes time and bandwidth
- Costs more (if LLM call re-runs)
- Slow user experience

**Do this instead:**
- Checkpoint state after each stage
- On re-run, check state; skip completed stages
- Use state file as recovery mechanism

## Scaling Considerations

| Scale | Approach | Limitations |
|-------|----------|-------------|
| **1 lecture/week** | Local CLI, single Python process, cache on disk | No scaling needed; fully local |
| **5+ lectures/week** | Queue-based (simple queue.Queue or celery-lite), async I/O | Consider separating compute (LLM) from I/O (download); run LLM in parallel |
| **10+ lectures/week** | Separate download, processing, and note-generation jobs; async orchestrator | FFmpeg bottleneck (CPU-bound); consider GPU acceleration or batch processing |
| **100+ lectures/week** | Distributed orchestrator (Airflow, Prefect); message queue (Celery, Kafka); cost tracking | Cost management critical; need quota enforcement, cost alerts |

### First Bottleneck: LLM API Latency

At 5+ lectures/week, LLM API calls (2-5 min/lecture) are the bottleneck. Solution:
- Decouple download (fast) from note generation (slow)
- Queue downloaded transcripts for batch LLM processing
- Process multiple lectures in parallel (if budget allows)

### Second Bottleneck: FFmpeg CPU

At 10+ lectures/week, FFmpeg audio extraction becomes CPU-bottleneck (5-10 min/lecture depending on video length). Solution:
- Consider GPU-accelerated FFmpeg (NVIDIA NVENC)
- Or: Pre-extract audio before main pipeline, cache separately

## Sources

- **ETL Pipeline Patterns:** Integrate.io (2025), Medium - "15 Data Pipeline Architecture Patterns Every Engineer Should Know" (Feb 2026), Dagster "Data Pipeline Architecture" guide
- **Video Processing:** OneUptime "How to Build a Video Processing Pipeline on AWS" (Feb 2026), "Auto-Remediation Workflows with FFmpeg" (Sept 2025)
- **Orchestration & State Management:** Temporal "Media Processing Workflows" (2021), Microsoft Agent Framework "Checkpointing & Resuming" (2026), Fivetran "Data Pipeline State Management" (2025)
- **Error Handling & Retries:** OneUptime "How to Implement Retry Logic with Exponential Backoff in Python" (Jan 2025), n8n "Complex Error Handling" guides (2025)
- **CLI Tools:** Inventive HQ "Building Python CLI Tools" (Jan 2026), DevToolbox "Python CLI Tools with Click and Typer" (Feb 2026), Medium "From argparse Spaghetti to Typer Elegance" (Feb 2026)
- **Configuration Management:** Micropole Belux "Best Practices for Configurations in Python-based Pipelines", Configu "Working with Python Configuration Files" (2024), Better Stack "Working with YAML Files in Python" (May 2025)
- **FFmpeg & Media Processing:** Medium "Mastering FFmpeg in Python" (Feb 2026), Cloudinary "A Beginner's Guide to FFmpeg in Python", CodeRivers "Mastering FFmpeg in Python" (Jan 2025)
- **Batch Processing Patterns:** AI Knowledge Library "Batch Processing Patterns" (Feb 2026), Medium "Checkpointer: Save Your Progress or Start From Zero" (Feb 2026)
- **File-Based State:** GitHub/awesome-agentic-patterns "Filesystem-Based Agent State", PyPI "simple-state-tracker" (May 2025)

---

*Architecture research for: Automated Lecture Workflow (Python media processing pipeline)*
*Researched: 2026-03-02*
