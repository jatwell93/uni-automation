# CLI Cheatsheet

## Get Started

```bash
# Set up everything at once
python process_lecture.py --create-all MIS271
python process_lecture.py --create-all MIS999

# Check what you have
python process_lecture.py --stats
```

## Download Workflow (Repeat weekly)

```bash
# 1. Create folders for the week (optional, already created above)
python process_lecture.py --create MIS271 1

# 2. Download video + transcript using Panopto-Video-DL
#    → Save to: downloads/MIS271_week_01_lecture/week_01_lecture/

# 3. Process
python process_lecture.py --course MIS271 --week 1 --session lecture
python process_lecture.py --course MIS271 --week 1 --session prac
```

## Commands at a Glance

### Setup

```bash
--create MIS271 1           # Create folders for week 1
--create-all MIS271         # Create all 22 folders
--create-all MIS999         # Create all 22 folders for AI course
```

### Process

```bash
--course MIS271 --week 1                # Lecture (default)
--course MIS271 --week 1 --session prac # Practical
--course MIS999 --week 3 --session lecture
```

### Info

```bash
--list                      # What's downloaded
--stats                     # How many sessions
--help                      # Show all options
```

## Arguments

| Argument | Example | Purpose |
|----------|---------|---------|
| `--course` | `MIS271` | Which course |
| `--week` | `1` | Which week (1-11) |
| `--session` | `lecture` or `prac` | Lecture or practical |

## By Course

```bash
# MIS271 - Business Intelligence & Data Warehousing
python process_lecture.py --course MIS271 --week 1 --session lecture

# MIS999 - Artificial Intelligence for Business
python process_lecture.py --course MIS999 --week 2 --session prac
```

## Check Progress

```bash
python process_lecture.py --stats
```

Output shows:
- Total sessions downloaded
- Lectures vs practicals per course
- Easy to see what's missing

## Common Tasks

### Download all lectures for MIS271

**Git Bash:**
```bash
for week in {1..11}; do
  python process_lecture.py --course MIS271 --week $week --session lecture
done
```

**PowerShell:**
```powershell
for ($i=1; $i -le 11; $i++) {
  python process_lecture.py --course MIS271 --week $i --session lecture
}
```

### Download everything

**Git Bash:**
```bash
for course in MIS271 MIS999; do
  for week in {1..11}; do
    python process_lecture.py --course $course --week $week --session lecture
    python process_lecture.py --course $course --week $week --session prac
  done
done
```

### See what's available

```bash
python process_lecture.py --list
```

## Folder Structure (Auto-created)

```
downloads/
├── MIS271_week_01_lecture/week_01_lecture/
│   ├── video.mp4          ← Download here
│   └── transcript.txt     ← Export here
├── MIS271_week_01_prac/week_01_prac/
│   ├── video.mp4
│   └── transcript.txt
... (all 22 folders for MIS271)
└── MIS999_week_01_lecture/week_01_lecture/
    └── video.mp4
```

## Quick Help

```bash
python process_lecture.py --help
```

## Error? Check This

| Error | Solution |
|-------|----------|
| "Unknown course code" | Use `MIS271` or `MIS999` |
| "Invalid week number" | Use 1-11 |
| "Video not found" | Run `--create`, download video, try again |
| Not sure what's where | Run `--list` or `--stats` |

---

**That's it!** Download videos to the right folders, run the command, done.
