# LLM Note Generation Plan

## Current Status ✅

The lecture download and organization system is **fully functional** and tested:

```bash
python process_lecture.py MIS271 1 lecture
# Output: Files ready for processing
```

**What's working:**
- ✅ Multi-course support (MIS271, MIS999, and any Deakin course: 3 letters + 3 digits)
- ✅ Dynamic folder creation (--create, --create-all)
- ✅ Video and transcript discovery
- ✅ Named argument CLI (--course, --week, --session)
- ✅ Progress tracking (--list, --stats)

**Available files for each lecture:**
- `downloads/MIS271_week_01_lecture/week_01_lecture/video.mp4` (128.4MB)
- `downloads/MIS271_week_01_lecture/week_01_lecture/transcript.txt`

---

## Next Phase: LLM Note Generation

### Goal
Generate Feynman-technique notes from lecture transcripts using OpenRouter LLM API

### High-Level Process
1. **Extract** text from transcript file
2. **Process** transcript through LLM with Feynman-technique prompt
3. **Generate** structured notes (concepts, explanations, examples, practice questions)
4. **Save** formatted notes to Obsidian vault

---

## Architecture Overview

### Components to Build

#### 1. Transcript Processing Module
**File:** `src/transcript_processor.py`

**Functions needed:**
- `load_transcript(file_path)` - Read .txt or .vtt transcript
- `clean_transcript(text)` - Remove timestamps, clean formatting
- `chunk_transcript(text, max_tokens)` - Split into manageable pieces for LLM
- `extract_key_concepts(text)` - Pre-process to identify main topics

**Considerations:**
- Handle both .txt and .vtt formats
- Remove speaker names/timestamps
- Preserve paragraph breaks and structure
- Split long transcripts (LLM token limits)

#### 2. LLM Integration Module
**File:** `src/llm_generator.py` (already exists, needs enhancement)

**Functions needed:**
- `generate_feynman_notes(transcript_text, config)` - Main generation function
- `create_feynman_prompt(transcript)` - Create effective prompt
- `call_openrouter_api(prompt, model, budget)` - API communication
- `parse_llm_response(response)` - Extract structured notes from LLM output

**Considerations:**
- Use OpenRouter API (already in config)
- Implement budget tracking (AUD cost limits per lecture)
- Handle API rate limits and retries
- Fallback strategies for API failures
- Cost calculation and safety buffer

#### 3. Note Formatter Module
**File:** `src/note_formatter.py`

**Functions needed:**
- `format_for_obsidian(notes_dict)` - Format for Obsidian vault
- `create_note_structure(title, concepts, explanations, examples, questions)` - Structure notes
- `add_metadata(notes, course_code, week_number, lecture_type)` - Add frontmatter
- `generate_markdown(notes)` - Convert to markdown format

**Output structure:**
```markdown
---
course: MIS271
week: 1
type: lecture
date: 2026-03-04
---

# MIS271 Week 1 Lecture - [Topic]

## Key Concepts
- Concept 1: Simple explanation
- Concept 2: Simple explanation

## Detailed Explanations
### Concept 1
[Teach-it-to-a-child explanation]

## Real-World Examples
- Example 1: How this applies
- Example 2: Practical application

## Practice Questions
- Q1: Self-test question
- Q2: Self-test question

## Learning Tips
- Tip 1
- Tip 2
```

#### 4. Obsidian Integration Module
**File:** `src/obsidian_writer.py` (likely already exists)

**Functions needed:**
- `create_note_file(note_content, vault_path, subfolder, filename)` - Save to vault
- `create_frontmatter(metadata)` - Generate YAML frontmatter
- `update_vault_index(vault_path, note_path)` - Update vault structure
- `link_related_notes(note_path, related_courses)` - Create wikilinks

**Considerations:**
- Respect Obsidian vault structure
- Create folders if needed (Trimester_1_26/Lectures/MIS271/)
- Add frontmatter metadata (course, week, type, date)
- Create backlinks to related notes

#### 5. Cost Tracking Module
**File:** `src/cost_tracker.py` (may exist)

**Functions needed:**
- `estimate_cost(transcript_length, model)` - Estimate API cost before calling
- `track_cost(model, tokens_used, amount_spent)` - Log actual cost
- `check_budget(spent_so_far, budget_limit, safety_buffer)` - Verify budget not exceeded
- `get_cost_summary()` - Cost report

**Considerations:**
- Track usage per lecture
- Track usage per course
- Track total trimester usage
- Implement safety buffer (config: llm_safety_buffer: 0.20 = 20%)

### 6. Main CLI Script
**File:** `generate_notes.py` (new)

**Usage:**
```bash
# Generate notes for specific lecture
python generate_notes.py --course MIS271 --week 1 --session lecture

# Generate notes for entire course
python generate_notes.py --course MIS271 --weeks 1-11

# Generate with custom model
python generate_notes.py --course MIS271 --week 1 --model gpt-4-turbo

# Generate with cost estimate only
python generate_notes.py --course MIS271 --week 1 --estimate-only
```

**Features:**
- Check for video and transcript first
- Estimate API cost before calling
- Generate and format notes
- Save to Obsidian vault
- Display cost summary
- Handle errors gracefully

---

## Feynman Technique Prompt Design

The LLM prompt should guide generation using Feynman technique principles:

**Key elements:**
1. **Simplicity** - Explain as if teaching a 12-year-old
2. **Clarity** - No jargon, or explain jargon when used
3. **Completeness** - Cover all major topics from transcript
4. **Structure** - Organized with clear sections
5. **Examples** - Real-world applications
6. **Self-testing** - Practice questions for learner

**Prompt template:**
```
You are an expert educator using the Feynman Technique to create study notes.

Analyze this lecture transcript and create comprehensive study notes that:

1. Extract and list all key concepts
2. Explain each concept simply (as if teaching a smart 12-year-old)
3. Provide real-world examples for each concept
4. Create self-testing questions
5. Include learning tips

Format as structured markdown with these sections:
- Key Concepts
- Detailed Explanations
- Real-World Examples
- Practice Questions
- Learning Tips

Transcript:
[INSERT TRANSCRIPT HERE]
```

---

## Implementation Roadmap

### Phase 1: Core LLM Integration
1. Transcript loading and cleaning
2. Basic LLM API calls via OpenRouter
3. Simple note formatting
4. Cost tracking

### Phase 2: Feynman Enhancement
1. Refined prompts for Feynman technique
2. Better note structure
3. Example generation
4. Practice question creation

### Phase 3: Obsidian Integration
1. Connect to Obsidian vault
2. Create proper folder structure
3. Add frontmatter metadata
4. Create wikilinks between notes

### Phase 4: Polish & Features
1. Batch processing (entire course)
2. Resume failed generations
3. Cost optimization
4. Performance improvements
5. Error recovery

---

## Configuration Requirements

Current config already has:
```yaml
openrouter_api_key: "OPENROUTER_API_KEY"  # Loaded from .env
llm_model: "deepseek/deepseek-chat"       # Model selection
llm_budget_aud: 0.30                      # Per-lecture budget
llm_safety_buffer: 0.20                   # 20% safety buffer
obsidian_vault_path: "C:\\Users\\josha\\OneDrive\\Documents\\Obsidian Vault\\University notes\\Trimester_1_26"
obsidian_note_subfolder: "Lectures"
```

**Needed in code:**
- Model pricing/cost mapping
- Token estimation functions
- Budget validation logic

---

## Data Flow Diagram

```
Lecture Downloaded
        ↓
[Process] transcript.txt
        ↓
Load & Clean Transcript
        ↓
Split into chunks (if needed)
        ↓
Estimate LLM Cost
        ↓
Check Budget (spent + estimate < limit?)
        ↓
Call OpenRouter API with Feynman prompt
        ↓
Parse LLM Response
        ↓
Format as Markdown
        ↓
Add Obsidian Metadata
        ↓
Save to Vault
        ↓
Update Cost Tracking
        ↓
Display Summary
```

---

## Testing Strategy

### Unit Tests
- Transcript loading (.txt, .vtt formats)
- Prompt generation
- Cost calculations
- Note formatting
- Obsidian file path generation

### Integration Tests
- End-to-end: transcript → notes → vault
- Budget enforcement
- API error handling
- Multiple courses simultaneously

### Manual Testing
- Test with MIS271 Week 1 (already have transcript)
- Test with different models
- Test cost tracking
- Test Obsidian vault integration

---

## Known Constraints

1. **OpenRouter API Costs**
   - Budget: $0.30 AUD per lecture
   - Safety buffer: 20% ($0.06 reserved)
   - Available: $0.24 for actual usage

2. **Token Limits**
   - Most models: 4k-8k input tokens
   - Transcripts may exceed this
   - Need chunking strategy

3. **Obsidian Integration**
   - Vault path: `C:\Users\josha\OneDrive\Documents\Obsidian Vault\University notes\Trimester_1_26`
   - Must maintain vault integrity
   - Proper folder structure required

4. **LLM Quality**
   - deepseek-chat: Cheap, good for summaries
   - claude-3-haiku: Expensive, better quality
   - gpt-4-turbo: Most expensive, highest quality
   - Trade-off between cost and quality

---

## Success Criteria

✅ Generate comprehensive notes from transcript
✅ Follow Feynman technique principles
✅ Stay within budget constraints
✅ Save to correct Obsidian vault location
✅ Handle errors gracefully
✅ Track costs accurately
✅ Support batch processing
✅ Work with all valid course codes

---

## Files to Create/Modify

### New Files
- `src/transcript_processor.py` - Transcript handling
- `src/note_formatter.py` - Markdown formatting
- `src/cost_tracker.py` - Budget tracking (or enhance existing)
- `generate_notes.py` - Main CLI for note generation
- `tests/test_transcript_processor.py` - Unit tests
- `tests/test_llm_generator.py` - Unit tests
- `tests/test_note_formatter.py` - Unit tests

### Existing Files to Enhance
- `src/llm_generator.py` - Add Feynman-specific functions
- `src/obsidian_writer.py` - Add metadata and linking
- `src/config.py` - Already has LLM config
- `process_lecture.py` - Already displays "Next steps: generate Feynman notes"

---

## Next Steps for New Chat

1. **Understand the current system**
   - Files are organized and ready
   - Transcripts are clean and available
   - Config has API key and budget

2. **Build transcript processor**
   - Load .txt files
   - Clean formatting
   - Chunk if needed

3. **Enhance LLM integration**
   - Create Feynman-technique prompt
   - Call OpenRouter API
   - Parse response

4. **Create note formatter**
   - Structure output
   - Add metadata
   - Generate markdown

5. **Integrate with Obsidian**
   - Save to correct vault
   - Create proper folder structure
   - Add frontmatter

6. **Test end-to-end**
   - Use MIS271 Week 1 as test case
   - Verify notes are generated
   - Check Obsidian vault

---

## Questions for New Chat

When opening new chat, clarify:
1. Which model to prioritize? (cost vs quality)
2. How to handle transcripts > token limit? (split strategy)
3. Obsidian structure preference? (flat vs hierarchical)
4. Batch processing needed immediately? (or sequential first)
5. Priority: basic generation or full Feynman technique?

---

## Summary

**Current state:** ✅ Lecture download system working perfectly
**Next goal:** 🎯 LLM-powered Feynman note generation
**Architecture:** Modular components for transcript → LLM → notes → Obsidian
**Timeline:** 4-6 phases with testing at each stage
**Constraints:** Budget ($0.30/lecture), token limits, vault integrity
