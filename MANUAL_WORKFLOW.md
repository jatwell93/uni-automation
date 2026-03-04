# Manual Lecture Processing Workflow

This document describes how to manually download Panopto videos and process them with the uni-automation system using Feynman-technique notes.

## Prerequisites
- Panopto-Video-DL browser extension installed
- Browser access to Panopto lectures
- Python environment set up with `uni-automation`

## Workflow

### Step 1: Get the Download Link from Panopto

1. Open your lecture in Panopto
2. Click the **Panopto-Video-DL** browser extension button
3. A download link will be copied to your clipboard (looks like: `https://s-cloudfront.cdn.au.panopto.com/sessions/.../*.mp4`)

### Step 2: Download Video and Transcript

1. **Download Video:**
   - Open Panopto-Video-DL application/interface
   - Paste the video link
   - Set destination to: `downloads/MIS272_week_01/week_01/`
   - Filename: `video.mp4`
   - Click Download and wait for completion

2. **Export Transcript:**
   - Go back to the Panopto lecture page
   - Click the **Download** button (usually bottom-left of player)
   - Select **Transcript** (if available)
   - Save as `transcript.txt` to: `downloads/MIS272_week_01/week_01/`

### Step 3: Verify Files Are in Place

Files should be located at:
```
downloads/
└── MIS272_week_01/
    └── week_01/
        ├── video.mp4          (required)
        └── transcript.txt     (optional but recommended)
```

### Step 4: Generate Feynman Notes

Run the processing script:
```bash
python process_lecture.py config/MIS272_week_01.yaml
```

This will:
- ✓ Validate your video file
- ✓ Check for transcript
- ✓ Prepare files for note generation
- ✓ Display status and next steps

### Step 5: Generate Notes Using LLM (Coming Soon)

Once the lecture is processed, use the LLM pipeline to generate Feynman-technique notes:
```bash
# Generate detailed notes from video transcript
python generate_notes.py config/MIS272_week_01.yaml
```

This will:
- Read transcript and extract key concepts
- Generate Feynman-technique explanations
- Apply learning principles
- Save notes to your Obsidian vault

## Supported File Formats

| File | Format | Location | Required |
|------|--------|----------|----------|
| Video | `.mp4` | `downloads/COURSE/week_XX/video.mp4` | ✓ Yes |
| Transcript | `.txt` or `.vtt` | `downloads/COURSE/week_XX/transcript.txt` | Optional |

## Troubleshooting

### Video validation fails
- Check file size is > 10MB
- Ensure download completed fully
- Verify file is valid MP4 (can play in media player)

### Transcript not found
- You can proceed without transcript
- Transcript improves note quality if available
- Try exporting again from Panopto

### File path issues
- Ensure folder structure matches exactly
- Check for typos in course/week folder names
- Use forward slashes in paths for consistency

## Example for Multiple Lectures

Week 1:
```bash
# Download video.mp4 to downloads/MIS272_week_01/week_01/
# Download transcript.txt to downloads/MIS272_week_01/week_01/
python process_lecture.py config/MIS272_week_01.yaml
```

Week 2:
```bash
# Download video.mp4 to downloads/MIS272_week_02/week_02/
# Download transcript.txt to downloads/MIS272_week_02/week_02/
python process_lecture.py config/MIS272_week_02.yaml
```

## Next Steps

1. Download your first lecture video and transcript
2. Run `python process_lecture.py config/MIS272_week_01.yaml`
3. Once that works, we'll integrate the LLM note generation pipeline
4. Later: Integrate option 1 (FFmpeg) for fully automated downloads
