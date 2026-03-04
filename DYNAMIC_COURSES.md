# Dynamic Course Code Support

## Overview

The system now supports **ANY Deakin course code** with the format **3 letters + 3 digits**.

No more hardcoding! Just use your course code and everything works automatically.

## Quick Start

```bash
# Works with ANY valid Deakin course code
python process_lecture.py --create-all MIS271
python process_lecture.py --create-all CHM101
python process_lecture.py --create-all BIO333
python process_lecture.py --course ENG202 --week 1
```

## Supported Course Code Format

**Valid:** 3 letters + 3 digits
- MIS271 ✓
- CHM101 ✓
- BIO333 ✓
- ENG202 ✓
- PHY101 ✓

**Invalid:** Anything else
- INVALID ✗ (no digits)
- MIS27 ✗ (too few digits)
- MIS2701 ✗ (too many digits)
- mis271 ✗ (lowercase)

## Examples

### Set Up Multiple Courses

```bash
# Once per trimester
python process_lecture.py --create-all MIS271
python process_lecture.py --create-all MIS999
python process_lecture.py --create-all CHM101
python process_lecture.py --create-all BIO333
```

### Process Lectures

```bash
# Process lectures (any course)
python process_lecture.py --course CHM101 --week 1 --session lecture
python process_lecture.py --course BIO333 --week 5 --session prac
python process_lecture.py --course ENG202 --week 3
```

### Create Folders for Specific Week

```bash
# Create folder for specific week
python process_lecture.py --create MIS373 2
python process_lecture.py --create CHM201 7
python process_lecture.py --create PHY101 4
```

## How It Works

### Validation

```python
CourseManager.is_valid_course_code("MIS271")  # True
CourseManager.is_valid_course_code("CHM101")  # True
CourseManager.is_valid_course_code("INVALID") # False
CourseManager.is_valid_course_code("MIS27")   # False
```

### Course Information

Two types of courses:

1. **Known Courses** (custom metadata)
   ```python
   KNOWN_COURSES = {
       "MIS271": {"name": "...", "obsidian_folder": "...", "weeks": 11},
       "MIS999": {"name": "...", "obsidian_folder": "...", "weeks": 11},
   }
   ```

2. **Unknown Courses** (automatic defaults)
   - Name: "{course_code} Course"
   - Obsidian folder: "{course_code}"
   - Weeks: 11 (default)

### Dynamic Discovery

The system automatically discovers all downloaded sessions:
```bash
python process_lecture.py --stats
# Shows ALL courses with downloaded sessions (known or unknown)
```

## Customization

### Adding Custom Course Metadata

Edit `src/course_manager.py`:

```python
KNOWN_COURSES = {
    "MIS271": {
        "name": "Business Intelligence and Data Warehousing",
        "obsidian_folder": "MIS271_BI_DW",
        "weeks": 11,
    },
    "CHM101": {  # Add new
        "name": "General Chemistry I",
        "obsidian_folder": "CHM101_General_Chem",
        "weeks": 12,  # Custom week count
    },
}
```

### Non-Standard Week Counts

Some courses might have different week counts. Add them to `KNOWN_COURSES`:

```python
"BIO333": {
    "name": "Advanced Biology",
    "obsidian_folder": "BIO333_Advanced",
    "weeks": 14,  # Different from default 11
}
```

## Real-World Usage

### Scenario 1: New Course Mid-Semester

```bash
# Discover a new course (BIO333)
# No code changes needed!

python process_lecture.py --create-all BIO333
python process_lecture.py --course BIO333 --week 1 --session lecture
python process_lecture.py --stats
# BIO333 is automatically discovered and listed
```

### Scenario 2: Non-Standard Course

```bash
# Course has 12 weeks instead of 11
# Add to KNOWN_COURSES in src/course_manager.py

python process_lecture.py --create-all CHM201
# All 24 folders created (12 weeks × 2 sessions)
```

### Scenario 3: Track Multiple Courses

```bash
python process_lecture.py --create-all MIS271
python process_lecture.py --create-all MIS999
python process_lecture.py --create-all CHM101
python process_lecture.py --create-all BIO333

# Later, check progress
python process_lecture.py --stats

# Output shows:
# Total sessions: 88 (22 per course)
# MIS271: 22 (11 lectures + 11 pracs)
# MIS999: 22 (11 lectures + 11 pracs)
# CHM101: 22 (11 lectures + 11 pracs)
# BIO333: 22 (11 lectures + 11 pracs)
```

## Technical Details

### Course Code Validation Pattern

```regex
^[A-Z]{3}\d{3}$
```

- `^` - Start of string
- `[A-Z]{3}` - Exactly 3 uppercase letters
- `\d{3}` - Exactly 3 digits
- `$` - End of string

Examples:
- Matches: MIS271, CHM101, BIO333, ENG202, PHY101
- Doesn't match: mis271, MIS27, MIS2701, INVALID

### Folder Structure (Auto-Generated)

For any course code `XXX###`:

```
downloads/
├── XXX###_week_01_lecture/week_01_lecture/
│   ├── video.mp4
│   └── transcript.txt
├── XXX###_week_01_prac/week_01_prac/
│   ├── video.mp4
│   └── transcript.txt
... (continues for all weeks)
```

## Benefits

✅ **Scalable** - Works with any Deakin course
✅ **Automatic** - No code changes needed
✅ **Flexible** - Customize as needed
✅ **Extensible** - Easy to add custom metadata
✅ **Future-proof** - New courses work immediately
✅ **Validated** - Invalid codes are caught early

## Troubleshooting

### Error: Invalid course code format

```bash
$ python process_lecture.py --create INVALID 1
[*] Invalid course code format: INVALID
Course codes must be 3 letters + 3 digits (e.g., MIS271, CHM101)
```

**Solution:** Use valid Deakin course codes (3 letters + 3 digits)

### Course has non-standard week count

**Solution:** Add to `KNOWN_COURSES` in `src/course_manager.py`

```python
"CHM201": {
    "name": "Organic Chemistry",
    "obsidian_folder": "CHM201_Organic",
    "weeks": 12,  # Not the default 11
}
```

## Summary

- **Works with:** Any Deakin course (3 letters + 3 digits)
- **Default behavior:** 11 weeks per course
- **Custom metadata:** Edit `KNOWN_COURSES` as needed
- **No code changes required:** For courses using defaults
- **Fully validated:** Invalid codes rejected immediately

You're now truly future-proof! 🚀
