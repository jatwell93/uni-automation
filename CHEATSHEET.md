# Cheatsheet

## Download & Organise — `process_lecture.py`

```bash
# One-time: create all folders for a course
python process_lecture.py --create-all MIS271

# Create folders for a single week
python process_lecture.py --create MIS271 1

# Check a specific session's status
python process_lecture.py --course MIS271 --week 1 --session lecture

# List all downloaded sessions
python process_lecture.py --list

# Show download progress stats
python process_lecture.py --stats
```

**Folder structure (files go here after downloading manually):**

```
downloads/
├── MIS271_week_01_lecture/week_01_lecture/
│   ├── video.mp4
│   └── transcript.txt
└── MIS271_week_01_prac/week_01_prac/
    └── transcript.txt
```

---

## Generate Notes — `generate_notes.py`

```bash
# Single session (defaults: lecture, deepseek/deepseek-chat)
python generate_notes.py --course MIS271 --week 1

# Practical session
python generate_notes.py --course MIS271 --week 1 --session prac

# Batch — weeks 1 through 5
python generate_notes.py --course MIS271 --weeks 1-5 --session lecture

# Check cost without calling the API
python generate_notes.py --course MIS271 --week 1 --estimate-only

# Stronger model for important lectures
python generate_notes.py --course MIS271 --week 1 --model anthropic/claude-3.5-sonnet
```

**Notes saved to:** `{ObsidianVault}/Lectures/MIS271/Week_01_lecture.md`

### Model Selection

| Use case | Model flag |
|----------|-----------|
| Everyday (default) | `deepseek/deepseek-chat` (~$0.003 AUD/lecture) |
| High-stakes content | `--model anthropic/claude-3.5-sonnet` |
| Any OpenRouter model | `--model <model-id>` |

**Budget limit:** $0.30 AUD per lecture (set in config).
