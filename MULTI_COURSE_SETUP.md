# Multi-Course Lecture Processing Setup

Complete guide for managing multiple courses and sessions with the uni-automation system.

## Overview

This system supports:
- **Multiple courses**: MIS271, MIS999 (easily extensible)
- **Multiple weeks**: 11 weeks per course
- **Multiple sessions**: Lecture and Practical for each week
- **Automatic organization**: Files automatically organized into the correct structure

## Quick Start

### 1. Download Your First Lecture

1. Open your lecture in Panopto
2. Click the **Panopto-Video-DL** browser extension
3. Open Panopto-Video-DL and paste the video link
4. Set destination folder to: `downloads/MIS271_week_01_lecture/week_01_lecture/`
5. Download the video as `video.mp4`

### 2. Export Transcript (Optional but Recommended)

1. Go back to Panopto lecture page
2. Click **Download** → **Transcript**
3. Save to: `downloads/MIS271_week_01_lecture/week_01_lecture/transcript.txt`

### 3. Process the Lecture

```bash
python process_lecture.py MIS271 1 lecture
```

Output:
```
[*] Processing: MIS271 - Lecture (Week 1)

[CHECK] Checking for video file...
[+] Found video: video.mp4 (128.4MB)
[FILE] Checking for transcript...
[+] Found transcript: transcript.txt

[+] Lecture files ready for processing
```

## Folder Structure

Files are organized automatically in this structure:

```
downloads/
├── MIS271_week_01_lecture/
│   └── week_01_lecture/
│       ├── video.mp4          (required)
│       └── transcript.txt     (optional)
├── MIS271_week_01_prac/
│   └── week_01_prac/
│       ├── video.mp4
│       └── transcript.txt
├── MIS271_week_02_lecture/
│   └── week_02_lecture/
│       ├── video.mp4
│       └── transcript.txt
│ ... (continues for all weeks and sessions)
└── MIS999_week_01_lecture/
    └── week_01_lecture/
        ├── video.mp4
        └── transcript.txt
```

**Why this structure?**
- Each lecture/prac has its own folder (no conflicts)
- Easy to manage and navigate
- Automatically discovered by the system
- Supports batch processing

## Command Reference

### Process a Single Lecture

```bash
# Default (lecture)
python process_lecture.py MIS271 1

# Explicit lecture
python process_lecture.py MIS271 1 lecture

# Practical session
python process_lecture.py MIS271 1 prac
```

### View Available Sessions

```bash
# List all downloaded sessions
python process_lecture.py --list

# Output:
# [LIST] Available downloaded sessions:
#   • MIS271 - Lecture (Week 1)
#   • MIS271 - Lecture (Week 2)
```

### Show Statistics

```bash
# Display statistics about downloaded sessions
python process_lecture.py --stats

# Output:
# [STATS] Session Statistics
#
# Total sessions downloaded: 5
#
# MIS271:
#   Total:   3
#   Lectures: 2
#   Pracs:   1
# MIS999:
#   Total:   2
#   Lectures: 1
#   Pracs:   1
```

### Batch Processing

Process all lectures for a course:

```bash
# Windows (PowerShell or CMD)
for /L %i in (1,1,11) do python process_lecture.py MIS271 %i lecture

# Linux/Mac/Git Bash
for week in {1..11}; do
  python process_lecture.py MIS271 $week lecture
  python process_lecture.py MIS271 $week prac
done

# Or process both courses
for course in MIS271 MIS999; do
  for week in {1..11}; do
    python process_lecture.py $course $week lecture
    python process_lecture.py $course $week prac
  done
done
```

## Course Configuration

Template configuration files are provided in `config/courses/`:

- `MIS271_template.yaml` - Business Intelligence and Data Warehousing
- `MIS999_template.yaml` - Artificial Intelligence for Business

### Using Templates

1. Copy the appropriate template for your course
2. Modify the course/week specific fields:
   - `slide_path`: Update to correct slide file
   - `week_number`: Update to correct week
   - `timestamp` (optional): Add if you want to record when processed

Example for MIS271 Week 2:
```yaml
metadata:
  week_number: 2
  
lecture:
  slide_path: "slides/MIS271_week_02.pdf"
```

## Workflow Example: Processing All Lectures for One Course

Typical workflow for MIS271 (11 weeks, 1 lecture per week):

```bash
# Week 1: Download and process
# 1. Download video and transcript using Panopto-Video-DL
# 2. Run:
python process_lecture.py MIS271 1 lecture

# Week 2: Download and process
python process_lecture.py MIS271 2 lecture

# ... repeat for weeks 3-11 ...

# Once all are downloaded, generate statistics
python process_lecture.py --stats

# To see all available
python process_lecture.py --list
```

## Supported Courses

The system currently supports:

| Code | Course Name | Weeks |
|------|-------------|-------|
| MIS271 | Business Intelligence and Data Warehousing | 11 |
| MIS999 | Artificial Intelligence for Business | 11 |

### Adding New Courses

To add support for additional courses, edit `src/course_manager.py`:

```python
COURSES = {
    "MIS271": {
        "name": "Business Intelligence and Data Warehousing",
        "obsidian_folder": "MIS271_BI_DW",
        "weeks": 11,
    },
    "MIS999": {
        "name": "Artificial Intelligence for Business",
        "obsidian_folder": "MIS999_AI_Business",
        "weeks": 11,
    },
    "NEW_CODE": {  # Add new course here
        "name": "New Course Name",
        "obsidian_folder": "obsidian_folder_name",
        "weeks": 12,
    },
}
```

## File Formats

### Video

- **Format**: MP4 (.mp4)
- **Min Size**: 10MB (for validation when FFmpeg is available)
- **Source**: Panopto-Video-DL downloader
- **Required**: Yes

### Transcript

- **Formats**: 
  - TXT (.txt) - Plain text from Panopto
  - VTT (.vtt) - WebVTT format
- **Source**: Panopto export or VTT caption file
- **Required**: No (but recommended for better notes)
- **Auto-detection**: System finds either format automatically

## Troubleshooting

### Video not found

**Error**: `Video not found: downloads\MIS271_week_01_lecture\week_01_lecture\video.mp4`

**Solution**:
1. Ensure you downloaded the video file
2. Check the exact path matches the required structure
3. Run `python process_lecture.py --list` to see expected locations

### Invalid course code

**Error**: `Unknown course code: MIS270. Available: MIS271, MIS999`

**Solution**:
- Use correct course codes (MIS271, MIS999)
- Check spelling
- To add new courses, see "Adding New Courses" section

### Week number out of range

**Error**: `Invalid week number: 15. Course MIS271 has 11 weeks`

**Solution**:
- Use week numbers 1-11 for both courses

### No sessions found with --list

**Solution**:
1. Download and save at least one video
2. Ensure folder structure is exactly: `downloads/MIS<CODE>_week_XX_<lecture|prac>/week_XX_<lecture|prac>/video.mp4`
3. Run `python process_lecture.py --stats` to verify system can see course folders

## Performance Tips

- **Batch process**: When you have multiple weeks ready, process them all at once with the batch scripts
- **Organize first**: Download all your videos and transcripts before processing
- **Check stats**: Use `--stats` command to see progress across both courses
- **List sessions**: Use `--list` to confirm files are discoverable before processing

## Next Steps

Once lectures are processed and ready:

1. **Generate Feynman Notes**: Use the LLM pipeline to create teaching-focused notes
2. **Sync to Obsidian**: Notes automatically save to your Obsidian vault
3. **Convert to Audio** (optional): Future enhancement for listening on commute

## Support

For issues or questions:
- Check this documentation first
- Run `python process_lecture.py --help` for command options
- Verify folder structure matches expected format
- Check file permissions if write errors occur
