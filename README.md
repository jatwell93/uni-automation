# Lecture Automation System

Automatically generate Feynman-technique study notes from Panopto lecture recordings.

**Workflow:** Download lecture → export transcript → run one command → notes appear in Obsidian.

---

## How It Works

1. **Download** lecture video + transcript manually using the [Panopto-Video-DL](https://github.com/Panopto-Video-DL/Panopto-Video-DL) browser extension
2. **Save** files to the auto-created folder structure (`downloads/MIS271_week_01_lecture/...`)
3. **Generate notes** with one command — transcript is cleaned, sent to LLM, saved to Obsidian

---

## Prerequisites

- **Python 3.11+**
- **OpenRouter API key** ([openrouter.ai](https://openrouter.ai)) — for LLM note generation
- **Obsidian vault** — where notes are saved
- **Panopto-Video-DL** browser extension — for manual lecture downloads

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create `.env` file

```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-YOUR-KEY-HERE

# Optional — defaults to the configured vault path
# OBSIDIAN_VAULT_PATH=C:\Users\YourName\Documents\Obsidian Vault\University notes\Trimester_1_26
```

### 3. Create folder structure

```bash
python process_lecture.py --create-all MIS271
python process_lecture.py --create-all MIS999
```

---

## Weekly Workflow

### Step 1 — Download (manual)

Use the **Panopto-Video-DL** browser extension:
1. Open the lecture in Panopto
2. Click the extension → copy download link
3. Download and save as `video.mp4` to the correct folder
4. On the Panopto page: **Download → Transcript** → save as `transcript.txt` to the same folder

**Folder paths:**
```
downloads/MIS271_week_01_lecture/week_01_lecture/video.mp4
downloads/MIS271_week_01_lecture/week_01_lecture/transcript.txt
```

### Step 2 — Generate notes

```bash
python generate_notes.py --course MIS271 --week 1 --session lecture
```

Notes are saved to your Obsidian vault:
```
Lectures/MIS271/Week_01_lecture.md
```

### Step 3 — Open Obsidian

The note has 6 sections: **Summary · Key Concepts · Examples · Formulas · Pitfalls · Review Questions**

---

## Commands

### generate_notes.py

```bash
# Generate notes for one lecture
python generate_notes.py --course MIS271 --week 1 --session lecture

# Check cost estimate without making an API call
python generate_notes.py --course MIS271 --week 1 --estimate-only

# Batch — generate notes for a range of weeks
python generate_notes.py --course MIS271 --weeks 1-5 --session lecture

# Use a different model (any OpenRouter model ID)
python generate_notes.py --course MIS271 --week 1 --model deepseek/deepseek-v3
python generate_notes.py --course MIS271 --week 1 --model bytedance-seed/seed-2.0-mini
```

| Flag | Default | Description |
|------|---------|-------------|
| `--course` | required | Course code (e.g. `MIS271`) |
| `--week` | — | Week number |
| `--weeks` | — | Week range, e.g. `1-11` |
| `--session` | `lecture` | `lecture` or `prac` |
| `--model` | `deepseek/deepseek-chat` | Any OpenRouter model ID |
| `--estimate-only` | — | Show cost without calling API |

### process_lecture.py

```bash
# Create folders for one week (both lecture + prac)
python process_lecture.py --create MIS271 1

# Create all folders for a course (do this once at trimester start)
python process_lecture.py --create-all MIS271

# Check status of a session
python process_lecture.py --course MIS271 --week 1 --session lecture

# List downloaded sessions
python process_lecture.py --list

# Show download progress
python process_lecture.py --stats
```

---

## Model Selection

The default model (`deepseek/deepseek-chat`) is fast and cheap (~$0.003 AUD per lecture).

| Model | Cost/lecture | Use when |
|-------|-------------|----------|
| `deepseek/deepseek-chat` | ~$0.003 | Default — everyday lectures |
| `deepseek/deepseek-v3` | ~$0.01 | Important lectures, better quality |
| `bytedance-seed/seed-2.0-mini` | very low | Large transcripts, cost-sensitive |
| `anthropic/claude-3-haiku` | ~$0.02 | High quality alternative |

Budget limit: **$0.30 AUD per lecture** (enforced with 20% safety buffer). Long transcripts are automatically truncated if they would exceed budget.

---

## Course Support

Any Deakin course code works (format: 3 uppercase letters + 3 digits):

```bash
python generate_notes.py --course MIS271 --week 1   # pre-configured
python generate_notes.py --course CHM101 --week 3   # auto-configured (11 weeks default)
```

Courses `MIS271` and `MIS999` have custom metadata. All others use 11-week defaults. To customise, add an entry to `KNOWN_COURSES` in `src/course_manager.py`.

---

## Architecture

```
process_lecture.py          — folder management, download tracking
generate_notes.py           — main note generation CLI

src/
├── course_manager.py       — multi-course folder structure
├── transcript_processor.py — VTT/SRT/TXT parsing, cleaning, PII removal
├── llm_generator.py        — OpenRouter API, token counting, budget enforcement
├── obsidian_writer.py      — frontmatter generation, markdown validation, vault write
├── cost_tracker.py         — per-lecture cost logging, weekly summaries
└── config.py               — Pydantic config model, .env loading
```

---

## Testing

```bash
pytest -xvs                          # all tests
pytest tests/test_config.py -xvs    # specific module
pytest --cov=src tests/ -xvs        # with coverage
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `OPENROUTER_API_KEY not set` | Add key to `.env` file |
| `Transcript not found` | Export transcript from Panopto, save as `transcript.txt` in session folder |
| `Obsidian vault not found` | Set `OBSIDIAN_VAULT_PATH` in `.env` |
| `Invalid course code` | Use format: 3 letters + 3 digits (e.g. `MIS271`) |
| Notes already exist | Script auto-saves with timestamp suffix — both versions kept |
| Cost exceeds budget | Use `--estimate-only` first; switch to a cheaper model |
