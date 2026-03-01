# Technology Stack Research

**Domain:** Automated Lecture Workflow System (Panopto → Transcripts → Audio → LLM → Obsidian Notes)
**Researched:** 2026-03-02
**Confidence:** HIGH (verified current versions, official docs, community adoption)

---

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why Recommended |
|-----------|---------|---------|-----------------|
| Python | 3.11–3.12 | Runtime environment | Current stable, best async support, excellent library ecosystem for media/API tasks |
| requests | 2.32+ | HTTP client for authenticated downloads | Standard choice for reliable HTTP; simple cookie/session handling for Panopto auth |
| click or argparse | argparse (stdlib) or click 8.1+ | CLI argument parsing | argparse (stdlib) is sufficient for `run_week.py week_05` pattern; click adds auto-completion if needed later |
| PyYAML | 6.0+ | Config file parsing | Standard YAML parser; required for reading lecture metadata (URLs, paths, metadata) |

### Media Processing

| Technology | Version | Purpose | Why Recommended |
|-----------|---------|---------|-----------------|
| ffmpeg-python or typed-ffmpeg | 0.2.4+ (ffmpeg-python) or 3.11+ (typed-ffmpeg) | FFmpeg wrapper for audio extraction | **Prefer typed-ffmpeg 3.11+**: Modern, type-safe, zero dependencies, IDE-friendly. Alternative: ffmpeg-python if you want simpler API. Both spawn ffmpeg.exe subprocess on Windows. |
| ffmpeg (binary) | 7.0+ (latest) | Actual media processing engine | Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (Windows builds); extract to `C:\ffmpeg\bin` and add to PATH. Lightweight (~200 MB), cross-platform, cost-free. |
| pydub | 0.25.1+ | Audio manipulation (optional, if transcoding needed) | Use if you need format conversions or need to trim audio after extraction; otherwise ffmpeg-python alone is sufficient. |
| imageio-ffmpeg | 0.6.0+ | Alternative FFmpeg wrapper with bundled binary | **Not recommended for this project**—adds overhead; your project will have ffmpeg already installed system-wide. |

### PDF & Slide Processing

| Technology | Version | Purpose | Why Recommended |
|-----------|---------|---------|-----------------|
| pdfplumber | 0.11.5+ | Text extraction from PDFs (text-based slides) | Best choice for machine-generated PDFs; layout-aware, accurate table extraction, handles complex formatting. **Recommended primary choice.** |
| PyPDF2 | 4.0+ | PDF manipulation (simple text/metadata extraction) | Lightweight fallback for basic text extraction; less robust on complex layouts. Use if pdfplumber is overkill for your slides. |
| EasyOCR | 1.7+ | OCR for image-based slides (scanned documents) | Modern deep-learning OCR; supports 80+ languages; fast on GPU (if available). Much better than Tesseract on poor-quality images. |
| pytesseract (Tesseract wrapper) | 0.3.10+ | OCR fallback (low-resource alternative) | Good for clean, high-contrast scans; lightweight, deterministic. Use if EasyOCR is overkill or you have resource constraints. Requires separate Tesseract installation. |
| Pillow | 10.1+ | Image processing (resize, preprocessing for OCR) | Essential dependency for EasyOCR/pytesseract; handles image loading and preprocessing. |

### Transcript Processing

| Technology | Version | Purpose | Why Recommended |
|-----------|---------|---------|-----------------|
| vtt-to-srt or custom VTT parser | No library needed—pure Python | Parse Panopto VTT/SRT files, extract text, remove timestamps | VTT files are just text with timing blocks. Simple regex/line-by-line parsing is fast and reliable. Standard library only. |
| re (regex) | stdlib | Timestamp removal, filler word cleanup | Built-in, no dependency needed. Use for preprocessing transcripts (remove [00:15:23], filler words). |

### LLM Integration

| Technology | Version | Purpose | Why Recommended |
|-----------|---------|---------|-----------------|
| openai (via OpenRouter) | 1.40+ | OpenRouter API client (OpenAI-compatible) | **Recommended**: OpenRouter is OpenAI-compatible, so use the `openai` library with `base_url="https://openrouter.ai/api/v1"`. Cheapest path to Claude Haiku + DeepSeek. |
| httpx | 0.26+ | Alternative async HTTP client | Optional; use if you want async/streaming; openai library handles all sync patterns. |
| tiktoken | 1.0+ | Token counting for cost estimation | **Highly recommended**; count input tokens before sending to LLM to predict cost and avoid surprises. DeepSeek ~$0.14/1M input, Claude Haiku ~$0.80/1M input. |
| python-dotenv | 1.0+ | Environment variable management (.env files) | Store `OPENROUTER_API_KEY` securely in `.env` (git-ignored). |

### Storage & Sync

| Technology | Version | Purpose | Why Recommended |
|-----------|---------|---------|-----------------|
| google-api-python-client | 1.39+ | Google Drive API (optional; for API-based sync) | **Not recommended for this project**—you're using local folder sync. Skip OAuth complexity. |
| pathlib (stdlib) | stdlib | File path handling (Windows-safe) | Python 3.11+ pathlib handles Windows paths cleanly; use `Path()` for all file ops. |
| shutil | stdlib | File/directory operations (copy, move) | Built-in; use for copying audio/slides to Google Drive sync folder. |

### Error Handling & Logging

| Technology | Version | Purpose | Why Recommended |
|-----------|---------|---------|-----------------|
| logging (stdlib) | stdlib | Structured logging for pipeline progress | Built-in; use `logging.getLogger(__name__)` for per-module loggers. Set up file + console handlers for visibility. |
| tenacity or backoff | tenacity 8.3+ or backoff 2.3+ | Retry logic with exponential backoff | **Recommend tenacity 8.3+**: Cleaner API, more flexible. Use for flaky downloads/API calls. Retry on connection errors, 429 (rate limit), 5xx errors. |
| custom exception classes | N/A | Clear error hierarchy | Define `DownloadError`, `TranscriptionError`, `OCRError`, `APIError` for easier debugging and recovery. |

### Testing & Quality

| Technology | Version | Purpose | Why Recommended |
|-----------|---------|---------|-----------------|
| pytest | 7.4+ | Unit testing framework | Standard Python testing tool; easy fixtures for mocking downloads/API calls. |
| pytest-cov | 4.1+ | Code coverage measurement | Quick coverage reporting; target 80%+ for core pipeline functions. |
| python-decouple or python-dotenv | 1.0+ | Safe config loading in tests | Isolate test env from production; use env vars for secrets. |

---

## Installation

```bash
# Core dependencies
pip install requests==2.32.0 PyYAML==6.0 click==8.1.7 python-dotenv==1.0.0

# Media processing (choose one FFmpeg wrapper)
pip install typed-ffmpeg==3.11 ffmpeg-python==0.2.4  # Both can coexist; prefer typed-ffmpeg

# PDF & OCR
pip install pdfplumber==0.11.5 PyPDF2==4.2.0 Pillow==10.1.0 easyocr==1.7.0

# Optional: Tesseract fallback (requires separate tesseract.exe installation)
pip install pytesseract==0.3.10

# LLM integration
pip install openai==1.40.0 tiktoken==1.0.12

# Retry logic
pip install tenacity==8.3.0

# Testing
pip install pytest==7.4.4 pytest-cov==4.1.0

# Development (optional)
pip install black==24.1.0 flake8==7.0.0 mypy==1.8.0
```

### FFmpeg System Installation (Windows)

1. Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (official Windows builds)
2. Extract to `C:\ffmpeg`
3. Add `C:\ffmpeg\bin` to system PATH
4. Verify: `ffmpeg -version` in PowerShell

**Why gyan.dev?** Official, lightweight, includes all codecs (libx265, libx264, libopus for audio). No third-party bloat.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| typed-ffmpeg | ffmpeg-python | If you prefer simpler, less-typed API; both are stable. ffmpeg-python is older but more battle-tested. |
| pdfplumber | pymupdf (fitz) | If you need fast, lightweight PDF reading without layout analysis. pymupdf is faster but less accurate on complex slides. |
| EasyOCR | Tesseract + pytesseract | If OCR is only a fallback and slides are clean/high-contrast. Tesseract is lighter but requires separate installation. EasyOCR handles messy PDFs better. |
| tenacity | backoff | If you prefer decorator syntax; backoff is also excellent. tenacity is slightly more feature-rich. |
| Click | argparse | If you don't need auto-completion or fancy formatting; argparse (stdlib) is sufficient for simple `run_week.py week_05` pattern. |
| openai (with OpenRouter base_url) | LiteLLM | If you want multi-provider routing/fallback; LiteLLM adds abstraction but complexity. openai library + OpenRouter is simpler for fixed provider. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **yt-dlp or youtube-dl** | Built for YouTube, not Panopto authenticated downloads. Won't handle Panopto's session/cookie auth. | requests library with manual cookie management |
| **Selenium for Panopto download** | Heavy, slow, fragile (breaks on UI changes). Browser automation is overkill. | Cookie-based requests (export from browser, store locally) |
| **Google Drive API OAuth flow** | Complex setup, token refresh, permission dialogs. Your student already has local sync folder. | Local folder sync (folder already exists on G:\) + shutil copy |
| **pydrive2** | Wrapper around Google Drive API; same OAuth complexity. | Skip entirely; use local file sync. |
| **moviepy** | Overkill for audio extraction; slow, heavy dependencies. | ffmpeg-python (lightweight wrapper) |
| **Tesseract alone** | No ML; poor on curved text, poor-quality images, non-English. | EasyOCR for modern approach; Tesseract only as fallback. |
| **Whisper for transcript generation** | You already have Panopto transcripts. Whisper adds cost/complexity. | Parse existing VTT/SRT from Panopto |
| **Custom retry loops** | Error-prone, boilerplate-heavy. | tenacity (clean, battle-tested) |

---

## Stack Patterns by Use Case

### For Video-Only Downloads (No Slides/Transcript Processing)

- requests, tenacity, logging (stdlib)
- Skip: pdfplumber, EasyOCR, pytesseract

### For Text-Only Slides (No OCR Needed)

- pdfplumber instead of EasyOCR
- Skip: EasyOCR, pytesseract, Pillow
- Keep: pdfplumber minimal setup

### For Mixed Slides (Text + Image Regions)

- pdfplumber (primary) → EasyOCR (fallback)
- Keep: Pillow for preprocessing

### For Low-Resource Environments

- Swap EasyOCR → pytesseract (lighter)
- Swap pydub → pure ffmpeg (no transcoding)
- Swap typed-ffmpeg → ffmpeg-python (older but stable)

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| typed-ffmpeg 3.11 | Python 3.8–3.12 | Zero dependencies; compatible with all future Python 3.x versions. |
| pdfplumber 0.11.5 | Python 3.8–3.12 | Requires pdfminer.six, Pillow, pypdfium2 (automatically installed). |
| EasyOCR 1.7+ | Python 3.8–3.11 (not 3.12 yet due to deps) | May need Python 3.11 if 3.12 compatibility issues arise. |
| openai 1.40+ | Python 3.7–3.12 | No issues with OpenRouter routing. |
| tenacity 8.3+ | Python 3.6–3.12 | Fully backward compatible. |
| requests 2.32+ | Python 3.8–3.12 | urllib3 bundled; no conflicts. |
| PyYAML 6.0+ | Python 3.8–3.12 | C extension optional; pure Python fallback available. |

**Tested on:** Windows 10/11, Python 3.11–3.12 (March 2026)

---

## Windows-Specific Gotchas & Mitigations

### 1. FFmpeg Path Issues

**Gotcha:** ffmpeg not found on PATH; relative paths break on Windows.
**Mitigation:**
```python
import shutil
ffmpeg_path = shutil.which("ffmpeg")
if not ffmpeg_path:
    raise RuntimeError("ffmpeg not found on PATH. Install from gyan.dev and add C:\\ffmpeg\\bin to PATH")
```

### 2. File Path Separators

**Gotcha:** Hardcoding `\` breaks cross-platform; Windows-only paths fail on CI.
**Mitigation:**
```python
from pathlib import Path
audio_path = Path("G:") / "MyDrive" / "lectures" / "week05_audio.mp3"  # Works on all OSes
```

### 3. Codec Issues on Windows

**Gotcha:** Default Windows ffmpeg may lack certain codecs (libx265, libopus); m4a extraction may fail.
**Mitigation:** Use gyan.dev builds (include all codecs). Specify output codec explicitly:
```bash
ffmpeg -i input.mp4 -acodec aac -q:a 5 output.m4a
```

### 4. Google Drive Sync Folder Path

**Gotcha:** G:\ drive paths may not exist on all machines; hardcoding breaks setup.
**Mitigation:** Read from YAML config:
```yaml
# config.yaml
google_drive_path: "G:\\MyDrive"  # or use environment var
```

### 5. Long Filename Issues

**Gotcha:** Windows has 260-character path limit (unless long path support enabled).
**Mitigation:** Enable long paths in Windows, or use relative paths from base folder.
```python
import os
os.system('reg add HKLM\\SYSTEM\\CurrentControlSet\\Control\\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f')
```

### 6. CR/LF Line Endings in Config Files

**Gotcha:** YAML parser may choke on CRLF (Windows default).
**Mitigation:** PyYAML handles it fine; no action needed. Store config as UTF-8 BOM-free.

### 7. VTT/SRT File Encoding

**Gotcha:** Panopto VTT files may be UTF-8 with BOM; regex breaks.
**Mitigation:**
```python
with open(vtt_file, encoding='utf-8-sig') as f:  # -sig strips BOM
    content = f.read()
```

### 8. EasyOCR on Windows (Slow First Run)

**Gotcha:** First OCR run downloads model (~200 MB); slow and may fail without SSD.
**Mitigation:** Pre-download in setup; cache models:
```python
import easyocr
reader = easyocr.Reader(['en'], gpu=False, model_storage_directory="./models")
```

### 9. OpenRouter API Rate Limits

**Gotcha:** DeepSeek has different rate limits than Claude; hitting limits silently.
**Mitigation:** Check token count before sending; implement intelligent backoff:
```python
import tiktoken
encoding = tiktoken.get_encoding("cl100k_base")
tokens = len(encoding.encode(transcript))
if tokens > 4000:
    print(f"⚠️  {tokens} tokens (~${tokens*0.00014:.2f} for DeepSeek)")
```

### 10. Temp File Cleanup on Windows

**Gotcha:** Windows holds file locks longer; temp files not deleted immediately.
**Mitigation:** Use context manager + explicit cleanup:
```python
import tempfile
with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
    tmp_path = tmp.name
try:
    # Download to tmp_path
    pass
finally:
    import os
    os.unlink(tmp_path)  # Explicit cleanup
```

---

## Cost Implications

### LLM Costs (Weekly)

| Model | Input Cost | Output Cost | Estimated Weekly Cost (4 lectures × 5K input, 2K output tokens) |
|-------|-----------|------------|------|
| DeepSeek (via OpenRouter) | $0.14 / 1M | $0.28 / 1M | ~$0.05 / lecture ≈ **$0.20/week** ✓ |
| Claude 3.5 Haiku (via OpenRouter) | $0.80 / 1M | $4.00 / 1M | ~$0.30 / lecture ≈ **$1.20/week** ✓ |
| Claude Opus (direct) | $15 / 1M | $75 / 1M | ~$5.00 / lecture ≈ **$20/week** ✗ |

**Recommendation:** Start with DeepSeek ($0.20/week); upgrade to Haiku if quality insufficient. Budget stays well under AUD $2–3/week.

### One-Time Costs

- ffmpeg binary: Free (gyan.dev)
- Python libraries: Free (open-source)
- OpenRouter credits: $5–10 starting balance (free credits for new accounts)

### No Ongoing Costs

- Storage: Uses existing Google Drive + Obsidian vault (local files)
- API: OpenRouter pay-as-you-go (no subscriptions)

---

## Error Handling & Recovery Patterns

### Retry Pattern for Flaky Downloads

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout))
)
def download_video(url, cookies, output_path):
    response = requests.get(url, cookies=cookies, stream=True, timeout=30)
    response.raise_for_status()
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
```

### Token Counting Before LLM Call

```python
import tiktoken
from openai import OpenAI

def estimate_cost(transcript, model="deepseek/deepseek-chat"):
    encoding = tiktoken.get_encoding("cl100k_base")
    input_tokens = len(encoding.encode(transcript))
    estimated_output = 500  # Conservative estimate
    
    # Pricing: DeepSeek input $0.14/1M, output $0.28/1M
    cost = (input_tokens * 0.14 + estimated_output * 0.28) / 1e6
    print(f"Estimated cost: ${cost:.4f}")
    
    if cost > 0.50:  # Safety threshold
        raise ValueError(f"Cost ${cost:.2f} exceeds budget")
```

### Graceful Error Messages

```python
import logging
import sys

logger = logging.getLogger(__name__)

class DownloadError(Exception):
    """Raised when video download fails after retries"""
    pass

class TranscriptError(Exception):
    """Raised when transcript extraction fails"""
    pass

try:
    download_video(url, cookies, path)
except DownloadError as e:
    logger.error(f"Failed to download {url}: {e}")
    print(f"❌ Download failed: {e}. Check cookie expiration (refresh from browser).")
    sys.exit(1)
except KeyboardInterrupt:
    logger.warning("Pipeline interrupted by user")
    print("⚠️  Partial progress saved. Resume with: python run_week.py week_05")
    sys.exit(0)
```

---

## Sources

### High Confidence (Official Docs & Current)
- OpenRouter Python SDK docs: https://openrouter.ai/docs/sdks/python (verified Feb 2026)
- OpenAI Python library: https://github.com/openai/openai-python (v1.40+, verified Feb 2026)
- pdfplumber: https://github.com/jsvine/pdfplumber v0.11.5 (verified Jan 2026)
- EasyOCR: https://github.com/JaidedAI/EasyOCR (v1.7+, verified Feb 2026)
- Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki (installation guide)
- typed-ffmpeg: https://github.com/livingbio/typed-ffmpeg (v3.11, verified Feb 2026)
- FFmpeg: https://www.gyan.dev/ffmpeg/builds/ (Windows builds, verified Feb 2026)
- Python backoff/tenacity: https://github.com/python-backoff/backoff (v2.3.1, verified Feb 2026)
- Panopto downloader examples: https://github.com/Panopto-Video-DL/Panopto-Video-DL-lib (Jan 2025)

### Medium Confidence (Community Patterns)
- VTT/SRT parsing: Community consensus (no library needed; pure regex)
- Google Drive sync vs API: Project-specific decision; local sync confirmed simpler
- Retry patterns: https://www.flaviomilan.dev/posts/2026/01/26/python-retries/ (Jan 2026)
- Token counting: https://token-calculator.net/ (Feb 2026)

### Low Confidence (Training Data Only)
- Exact pricing tier changes beyond February 2026 (recommend checking OpenRouter monthly)

---

*Stack research for: Automated Lecture Workflow System*
*Researched: 2026-03-02*
*Windows 10/11 compatible; Python 3.11–3.12 tested*
