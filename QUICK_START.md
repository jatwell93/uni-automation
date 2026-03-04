# Quick Start Guide - Multi-Course Setup

## For Your Two Courses

You have:
- **MIS271**: Business Intelligence and Data Warehousing (11 weeks)
- **MIS999**: Artificial Intelligence for Business (11 weeks)

Each has lecture + practical sessions.

## Processing Workflow

### Step 1: Download Using Panopto-Video-DL

For **MIS271 Week 1 Lecture**:
1. Open lecture in Panopto
2. Click Panopto-Video-DL extension → get download link
3. Open Panopto-Video-DL downloader
4. Paste link, set destination to: `downloads/MIS271_week_01_lecture/week_01_lecture/`
5. Save as `video.mp4`

For **MIS271 Week 1 Practical**:
1. Repeat above but set destination to: `downloads/MIS271_week_01_prac/week_01_prac/`

### Step 2: Export Transcript (Optional)

1. On Panopto page, click **Download** → **Transcript**
2. Save to same folder as video: `transcript.txt`

### Step 3: Process the Lecture

```bash
# Process the lecture
python process_lecture.py MIS271 1 lecture

# Or the practical
python process_lecture.py MIS271 1 prac
```

Done! Files are now organized and ready for note generation.

## Commands Reference

```bash
# Process a specific lecture
python process_lecture.py MIS271 1 lecture

# Process a practical
python process_lecture.py MIS271 1 prac

# See all available sessions
python process_lecture.py --list

# Show download progress
python process_lecture.py --stats

# Process multiple weeks (Windows PowerShell)
for ($i=1; $i -le 11; $i++) { 
  python process_lecture.py MIS271 $i lecture
}

# Process multiple weeks (Git Bash)
for i in {1..11}; do
  python process_lecture.py MIS271 $i lecture
done
```

## Folder Structure (Auto-Generated)

System automatically creates and organizes:

```
downloads/
├── MIS271_week_01_lecture/week_01_lecture/
│   ├── video.mp4
│   └── transcript.txt
├── MIS271_week_01_prac/week_01_prac/
│   ├── video.mp4
│   └── transcript.txt
├── MIS271_week_02_lecture/week_02_lecture/
│   └── video.mp4
... (all weeks automatically structured)
└── MIS999_week_01_lecture/week_01_lecture/
    └── video.mp4
```

## Your Current Status

✅ Video downloaded: `MIS271 Week 1 Lecture`
✅ Transcript available: `MIS271 Week 1 Lecture`
✅ System tested and working

### Next Steps:
1. Continue downloading more lectures/pracs
2. Once all downloaded, use `python process_lecture.py --stats` to verify
3. Then we'll integrate Feynman note generation

## Typical Weekly Process

Each week for each course:

```bash
# Monday: Download MIS271 lecture
# → Use Panopto-Video-DL to download video + transcript

# Tuesday: Download MIS271 practical
# → Use Panopto-Video-DL to download video + transcript

# Wednesday: Download MIS999 lecture
# → Use Panopto-Video-DL to download video + transcript

# Thursday: Download MIS999 practical
# → Use Panopto-Video-DL to download video + transcript

# Friday: Process all 4 sessions
python process_lecture.py MIS271 1 lecture
python process_lecture.py MIS271 1 prac
python process_lecture.py MIS999 1 lecture
python process_lecture.py MIS999 1 prac

# Then generate Feynman notes for all (coming next phase)
```

## Help

For more details, see:
- `MULTI_COURSE_SETUP.md` - Complete documentation
- `python process_lecture.py --help` - Command options

## Questions?

Run `python process_lecture.py --stats` to see what's available and verify everything is working correctly.
