# Quick Start Guide

## One-time Setup

**1. Create all download folders for a course (do this once per trimester):**

```bash
python process_lecture.py --create-all MIS271
python process_lecture.py --create-all MIS999
```

**2. Add your API key to `.env`:**

```
OPENROUTER_API_KEY=sk-or-...
```

---

## Weekly Routine

Each week: download sessions manually, then generate notes.

### Step 1 — Download from Panopto

Use the **Panopto-Video-DL** browser extension to download the video and export the transcript. Save files to the correct folder:

| Session | Save to |
|---------|---------|
| MIS271 Week 1 Lecture | `downloads/MIS271_week_01_lecture/week_01_lecture/` |
| MIS271 Week 1 Practical | `downloads/MIS271_week_01_prac/week_01_prac/` |

Files inside each folder: `video.mp4` and `transcript.txt`

### Step 2 — Generate Notes

```bash
# Lecture notes
python generate_notes.py --course MIS271 --week 1 --session lecture

# Practical notes
python generate_notes.py --course MIS271 --week 1 --session prac
```

Notes are saved to your Obsidian vault at:
`Lectures/MIS271/Week_01_lecture.md`

### Step 3 — Review in Obsidian

Open Obsidian and find the note under `University notes > Trimester_1_26 > Lectures > MIS271`.

---

## Full Week Example (MIS271 + MIS999)

```bash
# After downloading all sessions for the week:

python generate_notes.py --course MIS271 --week 3 --session lecture
python generate_notes.py --course MIS271 --week 3 --session prac
python generate_notes.py --course MIS999 --week 3 --session lecture
python generate_notes.py --course MIS999 --week 3 --session prac
```

Or use batch mode:

```bash
python generate_notes.py --course MIS271 --weeks 1-5 --session lecture
```

---

## Model Selection

The default model (`deepseek/deepseek-chat`) costs ~$0.003 AUD per lecture and is good for most sessions.

For high-stakes content (e.g., exam topics, complex concepts), use a stronger model:

```bash
# Default — fast and cheap
python generate_notes.py --course MIS271 --week 5 --session lecture

# Stronger model for important lectures
python generate_notes.py --course MIS271 --week 5 --session lecture --model anthropic/claude-3.5-sonnet

# Check cost before running
python generate_notes.py --course MIS271 --week 5 --session lecture --estimate-only
```

---

## Check What You Have

```bash
python process_lecture.py --list     # Show downloaded sessions
python process_lecture.py --stats    # Show progress per course
```
