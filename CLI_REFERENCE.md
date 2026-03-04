# Complete CLI Reference - uni-automation

## Overview

The `process_lecture.py` script provides a complete command-line interface for managing multi-course lecture downloads and processing.

## Quick Reference

```bash
# Create folders
python process_lecture.py --create MIS271 1
python process_lecture.py --create-all MIS999

# Process lectures
python process_lecture.py --course MIS271 --week 1
python process_lecture.py --course MIS271 --week 1 --session prac

# View information
python process_lecture.py --list
python process_lecture.py --stats
```

---

## Complete Command Reference

### 1. Creating Folder Structure

#### Create folders for a specific week (both lecture + prac)

```bash
python process_lecture.py --create MIS271 1
```

**Output:**
```
[*] Creating folders for MIS271 Week 1

[+] Created: downloads\MIS271_week_01_lecture\week_01_lecture
[+] Created: downloads\MIS271_week_01_prac\week_01_prac

[+] Folders created successfully

Next steps:
1. Download video using Panopto-Video-DL
2. Save to one of the folders created above as 'video.mp4'
3. Export transcript and save as 'transcript.txt' (optional)
4. Run: python process_lecture.py --course MIS271 --week 1
```

**When to use:** Before downloading a new lecture/practical

---

#### Create all folders for an entire course

```bash
python process_lecture.py --create-all MIS271
```

**Output:**
```
[*] Creating all folders for MIS271 (11 weeks × 2 sessions)

[+] Created 22 folder structures (11 weeks × 2 sessions)

Folder structure:
  downloads/MIS271_week_01_lecture/week_01_lecture/
  downloads/MIS271_week_01_prac/week_01_prac/
  downloads/MIS271_week_02_lecture/week_02_lecture/
  ... (continues for all 11 weeks)

Next steps:
1. Download videos using Panopto-Video-DL
2. Save to corresponding folders as 'video.mp4'
3. Export transcripts and save as 'transcript.txt' (optional)
4. Use 'python process_lecture.py --stats' to track progress
```

**When to use:** At the beginning of the trimester to set up everything

---

### 2. Processing Lectures

#### Process with named arguments (Recommended)

```bash
# Process a lecture (default)
python process_lecture.py --course MIS271 --week 1

# Explicitly specify lecture
python process_lecture.py --course MIS271 --week 1 --session lecture

# Process a practical
python process_lecture.py --course MIS271 --week 1 --session prac
```

**Output:**
```
[*] Processing: MIS271 - Lecture (Week 1)

[CHECK] Checking for video file...
[+] Found video: video.mp4 (128.4MB)
[FILE] Checking for transcript...
[+] Found transcript: transcript.txt

[+] Lecture files ready for processing

Files:
  Video:      video.mp4 (128.4MB)
  Transcript: transcript.txt

Next steps:
1. Files are ready for analysis
2. You can generate Feynman notes using the LLM pipeline
```

**When to use:** After downloading a video and transcript

---

#### Process with positional arguments (Legacy)

```bash
# Default (lecture)
python process_lecture.py MIS271 1

# Explicit lecture
python process_lecture.py MIS271 1 lecture

# Practical
python process_lecture.py MIS271 1 prac
```

**Note:** Named arguments are recommended for clarity and consistency

---

### 3. Viewing Information

#### List all available sessions

```bash
python process_lecture.py --list
```

**Output:**
```
[LIST] Available downloaded sessions:

  • MIS271 - Lecture (Week 1)
  • MIS271 - Lecture (Week 2)
  • MIS271 - Practical (Week 1)
```

**When to use:** Track which lectures you've already downloaded

---

#### Show download statistics

```bash
python process_lecture.py --stats
```

**Output:**
```
[STATS] Session Statistics

Total sessions downloaded: 3

MIS271:
  Total:   2
  Lectures: 1
  Pracs:   1
MIS999:
  Total:   1
  Lectures: 1
  Pracs:   0
```

**When to use:** Monitor progress across both courses

---

#### Show help

```bash
python process_lecture.py --help
```

---

## Workflow Examples

### Example 1: Setting Up a New Course at Start of Trimester

```bash
# Set up MIS271 (create all folders immediately)
python process_lecture.py --create-all MIS271

# Set up MIS999 (create all folders immediately)
python process_lecture.py --create-all MIS999

# Verify both are ready
python process_lecture.py --stats
```

**Output:**
```
[STATS] Session Statistics

Total sessions downloaded: 0

MIS271:
  Total:   0
  Lectures: 0
  Pracs:   0
MIS999:
  Total:   0
  Lectures: 0
  Pracs:   0
```

---

### Example 2: Weekly Download and Process Workflow

**Monday:**
```bash
# Download MIS271 Week 1 Lecture using Panopto-Video-DL
# Save to: downloads/MIS271_week_01_lecture/week_01_lecture/video.mp4
# Save to: downloads/MIS271_week_01_lecture/week_01_lecture/transcript.txt

# Process it
python process_lecture.py --course MIS271 --week 1 --session lecture
```

**Tuesday:**
```bash
# Download MIS271 Week 1 Practical
# Save to: downloads/MIS271_week_01_prac/week_01_prac/video.mp4

# Process it
python process_lecture.py --course MIS271 --week 1 --session prac
```

**Wednesday:**
```bash
# Download MIS999 Week 1 Lecture
# Process it
python process_lecture.py --course MIS999 --week 1
```

**Check progress:**
```bash
python process_lecture.py --stats
```

---

### Example 3: Batch Processing Multiple Weeks

**Windows (PowerShell):**
```powershell
# Process all MIS271 lectures (weeks 1-11)
for ($i=1; $i -le 11; $i++) {
  python process_lecture.py --course MIS271 --week $i --session lecture
}

# Process all MIS271 practicals
for ($i=1; $i -le 11; $i++) {
  python process_lecture.py --course MIS271 --week $i --session prac
}
```

**Linux/Mac/Git Bash:**
```bash
# Process all MIS271 lectures
for week in {1..11}; do
  python process_lecture.py --course MIS271 --week $week --session lecture
done

# Process all MIS271 practicals
for week in {1..11}; do
  python process_lecture.py --course MIS271 --week $week --session prac
done

# Process both courses at once
for course in MIS271 MIS999; do
  for week in {1..11}; do
    python process_lecture.py --course $course --week $week --session lecture
    python process_lecture.py --course $course --week $week --session prac
  done
done
```

---

## Argument Reference

### Named Arguments (Recommended)

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--course` | string | - | Course code (MIS271, MIS999) |
| `--week` | integer | - | Week number (1-11) |
| `--session` | string | "lecture" | Session type (lecture, prac) |

### Special Commands

| Command | Arguments | Description |
|---------|-----------|-------------|
| `--create` | COURSE WEEK | Create folders for a specific week |
| `--create-all` | COURSE | Create all folders for a course |
| `--list` | - | List available downloaded sessions |
| `--stats` | - | Show statistics about downloads |
| `--help` | - | Show help message |

### Positional Arguments (Legacy)

```bash
python process_lecture.py [COURSE] [WEEK] [SESSION]
```

| Position | Type | Default | Description |
|----------|------|---------|-------------|
| 1 | string | - | Course code |
| 2 | integer | - | Week number |
| 3 | string | "lecture" | Session type |

---

## Error Handling

### Unknown course code

```bash
$ python process_lecture.py --create INVALID 1

[*] Unknown course code: INVALID. Available: MIS271, MIS999
```

**Solution:** Use valid course codes (MIS271 or MIS999)

---

### Invalid week number

```bash
$ python process_lecture.py --course MIS271 --week 15

[*] Invalid week number: 15. Course MIS271 has 11 weeks
```

**Solution:** Use week numbers 1-11

---

### Video not found

```bash
$ python process_lecture.py --course MIS271 --week 1

[*] Processing: MIS271 - Lecture (Week 1)

[CHECK] Checking for video file...
[*] Video not found: downloads\MIS271_week_01_lecture\week_01_lecture\video.mp4

Expected location:
  downloads\MIS271_week_01_lecture\week_01_lecture\video.mp4

To fix:
1. Download the video using Panopto-Video-DL
2. Save it to the path above
3. Run this script again
```

**Solution:**
1. Create folders first: `python process_lecture.py --create MIS271 1`
2. Download video using Panopto-Video-DL
3. Save as `video.mp4` to the exact path shown
4. Try again

---

## Tips & Tricks

### Pre-create everything at once

```bash
# Both courses ready to go immediately
python process_lecture.py --create-all MIS271
python process_lecture.py --create-all MIS999
```

### Quick status check

```bash
# See what you've downloaded so far
python process_lecture.py --stats

# See exactly which sessions
python process_lecture.py --list
```

### Simplify scripts

If you download videos regularly, create a simple batch file:

**Windows batch file (`download_all.bat`):**
```batch
@echo off
for /L %%i in (1,1,11) do (
  echo Processing MIS271 Week %%i
  python process_lecture.py --course MIS271 --week %%i --session lecture
  python process_lecture.py --course MIS271 --week %%i --session prac
)
for /L %%i in (1,1,11) do (
  echo Processing MIS999 Week %%i
  python process_lecture.py --course MIS999 --week %%i --session lecture
  python process_lecture.py --course MIS999 --week %%i --session prac
)
```

Run with: `download_all.bat`

---

## FAQ

**Q: Which format should I use - positional or named arguments?**
A: Use named arguments (`--course`, `--week`, `--session`) - they're clearer and easier to remember.

**Q: Do I need to create folders before downloading?**
A: No, but it helps organize things. Use `--create` or `--create-all` to prepare folders ahead of time.

**Q: Can I process both lecture and practical at once?**
A: No, but you can run two commands quickly:
```bash
python process_lecture.py --course MIS271 --week 1 --session lecture
python process_lecture.py --course MIS271 --week 1 --session prac
```

**Q: What if I forget the course code?**
A: The valid codes are **MIS271** and **MIS999**. Use `--stats` or `--list` to see what's available.

**Q: Can I add more courses?**
A: Yes! Edit `src/course_manager.py` and add to the `COURSES` dictionary.

---

## Getting Help

```bash
# Show all available commands
python process_lecture.py --help

# See what's available
python process_lecture.py --list

# Check progress
python process_lecture.py --stats
```
