# CLI Reference - uni-automation

The project provides two command-line scripts:

- **`process_lecture.py`** — folder creation and download tracking
- **`generate_notes.py`** — LLM-powered note generation from transcripts

---

## process_lecture.py

### Folder creation

Create the lecture and prac folders for a single week:

```bash
python process_lecture.py --create MIS271 1
```

Create all 22 folders for a course at once (11 weeks x 2 sessions):

```bash
python process_lecture.py --create-all MIS271
python process_lecture.py --create-all CHM101
```

This is the recommended approach at the start of a trimester. The folder structure created is:

```
downloads/
├── MIS271_week_01_lecture/week_01_lecture/
│   ├── video.mp4
│   └── transcript.txt
├── MIS271_week_01_prac/week_01_prac/
│   └── transcript.txt
```

Course codes must be the standard Deakin format: three uppercase letters followed by three digits (e.g. `MIS271`, `CHM101`, `BIO333`). MIS271 and MIS999 have custom metadata; all other codes use default settings (11 weeks).

### Session status

Show the status of a specific session — whether files are present and ready:

```bash
python process_lecture.py --course MIS271 --week 1 --session lecture
python process_lecture.py --course MIS271 --week 1 --session prac
```

`--session` defaults to `lecture` if omitted. Positional arguments also work:

```bash
python process_lecture.py MIS271 1 lecture
python process_lecture.py MIS271 1 prac
python process_lecture.py MIS271 1
```

### Listing and statistics

List every session that has been downloaded:

```bash
python process_lecture.py --list
```

Show a per-course breakdown of download progress:

```bash
python process_lecture.py --stats
```

### Help

```bash
python process_lecture.py --help
```

### Argument reference

| Argument | Description |
|----------|-------------|
| `--create COURSE WEEK` | Create lecture + prac folders for one week |
| `--create-all COURSE` | Create all folders for a course (11 weeks x 2 sessions) |
| `--course COURSE` | Course code (use with `--week` / `--session`) |
| `--week N` | Week number (1-11) |
| `--session SESSION` | `lecture` or `prac` (default: `lecture`) |
| `--list` | List all downloaded sessions |
| `--stats` | Show download progress per course |
| `--help` | Show help message |

---

## generate_notes.py

Reads a transcript from the downloads folder, cleans it, sends it to an OpenRouter LLM, and writes a structured Feynman-style note to your Obsidian vault.

### Basic usage

Generate notes for a single session:

```bash
python generate_notes.py --course MIS271 --week 1 --session lecture
python generate_notes.py --course MIS271 --week 1 --session prac
```

Preview the cost estimate without making an API call:

```bash
python generate_notes.py --course MIS271 --week 1 --estimate-only
```

Generate notes for a range of weeks:

```bash
python generate_notes.py --course MIS271 --weeks 1-5 --session lecture
python generate_notes.py --course MIS271 --weeks 1-11 --session prac
```

Use a different model:

```bash
python generate_notes.py --course MIS271 --week 1 --model deepseek/deepseek-v3
python generate_notes.py --course MIS271 --week 1 --model anthropic/claude-3-haiku
```

### Flag reference

| Flag | Default | Description |
|------|---------|-------------|
| `--course` | required | Course code (e.g. `MIS271`) |
| `--week` | — | Week number (1-11) |
| `--weeks` | — | Week range (e.g. `1-11`). Overrides `--week` |
| `--session` | `lecture` | `lecture` or `prac` |
| `--model` | `deepseek/deepseek-chat` | Any OpenRouter model ID |
| `--estimate-only` | false | Show cost estimate without calling the API |

### What it does

1. Locates the transcript at `downloads/{COURSE}_week_{NN}_{SESSION}/week_{NN}_{SESSION}/transcript.txt`
2. Cleans the transcript (removes timestamps, filler words, PII)
3. Displays a cost estimate
4. Calls the OpenRouter API using a Feynman-technique system prompt
5. Produces a six-section note: Summary, Key Concepts, Examples, Formulas, Pitfalls, Review Questions
6. Saves the note to `{OBSIDIAN_VAULT_PATH}/Lectures/{COURSE}/Week_{NN}_{SESSION}.md`
7. Appends cost data to `cost_tracking.json`

A budget limit of $0.30 per lecture is enforced with a 20% safety buffer.

### Model reference

All model IDs are OpenRouter identifiers.

| Model ID | Notes |
|----------|-------|
| `deepseek/deepseek-chat` | Default. Fast and cheap (~$0.003 AUD per lecture) |
| `deepseek/deepseek-v3` | Higher quality output |
| `bytedance-seed/seed-2.0-mini` | Very cheap; suited to large or lower-priority sessions |
| `anthropic/claude-3-haiku` | High-quality alternative |

### Required configuration

Create a `.env` file in the project root with the following:

```
OPENROUTER_API_KEY=your_key_here
OBSIDIAN_VAULT_PATH=/path/to/your/vault   # optional
```

`OPENROUTER_API_KEY` is required. If `OBSIDIAN_VAULT_PATH` is not set, notes are saved to a default local path.

---

## Error reference

| Error | Cause | Fix |
|-------|-------|-----|
| `Invalid course code format: X` | Course code does not match `[A-Z]{3}[0-9]{3}` | Use a valid format: `MIS271`, `CHM101`, etc. |
| `Invalid week number: N` | Week is outside the range for that course | Use 1-11 for most courses |
| `Video not found: ...` | `video.mp4` missing from the session folder | Download the video and place it at the expected path |
| `Transcript not found: ...` | `transcript.txt` missing | Export and save the transcript, or omit if not needed |
| `OPENROUTER_API_KEY not set` | Missing environment variable | Add `OPENROUTER_API_KEY` to `.env` |
| `Budget limit exceeded` | Estimated cost exceeds $0.30 | Use `--estimate-only` to inspect, or switch to a cheaper model |
