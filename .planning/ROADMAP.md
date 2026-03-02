# Roadmap: Automated Lecture Workflow

**Phases:** 4  
**Depth:** Standard  
**Coverage:** 46/46 requirements mapped ✓  
**Mode:** Solo (OpenCode implementation)

---

## Phases

- [ ] **Phase 1: Foundation** - Core CLI, configuration, Panopto authentication, and video/transcript download with validation
- [ ] **Phase 2: Media Processing** - Transcript cleanup, audio extraction, and slide text extraction with fallbacks
- [ ] **Phase 3: Intelligence & Output** - LLM integration, Feynman-structured note generation, and Obsidian vault output
- [ ] **Phase 4: Reliability & Recovery** - Checkpointing, error handling, privacy controls, and Google Drive sync

---

## Phase Details

### Phase 1: Foundation

**Goal:** Enable authenticated downloads and validated file retrieval, with configuration infrastructure that supports all downstream stages.

**Depends on:** Nothing (first phase)

**Requirements:** AUTH-01, AUTH-02, AUTH-03, DOWN-01, DOWN-02, DOWN-03, CONFIG-01, CONFIG-02, CONFIG-03, CONFIG-04, PRIV-01, PRIV-02

**Success Criteria** (what must be TRUE):
1. User can configure Panopto cookies in YAML file and system validates they're fresh before download (test API call succeeds)
2. User can run `python run_week.py <config_file>` and system downloads Panopto video file; integrity validated with ffprobe (codec, duration, size > 10MB)
3. System downloads Panopto transcript (.vtt/.txt) alongside video without manual extraction steps
4. User receives clear, actionable error messages if authentication fails or files are invalid (e.g., "Refresh cookies from browser", "File size suspicious—retry or check Panopto URL")
5. System logs all actions to file with timestamps; user can trace pipeline execution

**Plans:** 4 plans in 2 waves

**Wave 1 (Parallel):**
- [ ] 01-01-PLAN.md — Config model + Pydantic validation (CONFIG-01, CONFIG-02, CONFIG-03, CONFIG-04)
- [ ] 01-02-PLAN.md — Cookie auth + Panopto session validation (AUTH-01, AUTH-02, AUTH-03)
- [x] 01-03-PLAN.md — Video/transcript download + ffprobe validation (DOWN-01, DOWN-02, DOWN-03, PRIV-02) **COMPLETE**

**Wave 2 (Depends on Wave 1):**
- [ ] 01-04-PLAN.md — Integration, logging, security setup (PRIV-01)

---

### Phase 2: Media Processing

**Goal:** Transform downloaded raw media (video, transcript, PDF) into structured, clean data ready for LLM consumption.

**Depends on:** Phase 1 (provides validated video, transcript, config)

**Requirements:** TRAN-01, TRAN-02, TRAN-03, TRAN-04, TRAN-05, AUDIO-01, AUDIO-02, AUDIO-03, AUDIO-04, SLIDE-01, SLIDE-02, SLIDE-03, SLIDE-04, SLIDE-05

**Success Criteria** (what must be TRUE):
1. System extracts audio from downloaded video using ffmpeg; validates output with ffprobe (duration ≥80% of video, file size ≥1MB, plays without corruption)
2. User receives clear error messages if audio extraction fails (codec unsupported, ffmpeg not installed, etc.) with recovery instructions
3. System parses transcript into clean text: removes timestamps, filler words ('um', 'uh', 'like'), redundancies; no identifying information (student names/emails) remains
4. System extracts text from text-based PDF slides using pdfplumber; detects image-based slides and flags for manual OCR or uses EasyOCR fallback
5. User can process lecture with mixed text-based and scanned slides; slide text organized by page for LLM consumption

**Plans:** 3 plans in 1 wave

**Wave 1 (Parallel):**
- [x] 02-01-PLAN.md — Audio extraction + validation (AUDIO-01, AUDIO-02, AUDIO-03, AUDIO-04) **COMPLETE**
- [ ] 02-02-PLAN.md — Transcript processing + cleanup (TRAN-01, TRAN-02, TRAN-03, TRAN-04, TRAN-05)
- [ ] 02-03-PLAN.md — Slide text extraction (SLIDE-01, SLIDE-02, SLIDE-03, SLIDE-04, SLIDE-05)

---

### Phase 3: Intelligence & Output

**Goal:** Convert cleaned media into high-quality, structured study notes using LLM integration, with direct output to Obsidian vault.

**Depends on:** Phase 2 (provides cleaned transcript, audio, slide text)

**Requirements:** LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06, OBS-01, OBS-02, OBS-03, OBS-04, COST-01, COST-02, COST-03, COST-04

**Success Criteria** (what must be TRUE):
1. System counts tokens in transcript + slide text before API call; truncates content if budget exceeded (enforce ~0.30 AUD per lecture)
2. System calls OpenRouter API and generates Markdown notes with 6 sections: Summary, Key Concepts, Examples, Formulas, Pitfalls, Review Questions
3. User receives cost estimate before API call and warning if single lecture exceeds 0.50 AUD budget; cost logged per lecture for weekly tracking
4. System writes generated notes to Obsidian vault at configured path (e.g., `/Business Analytics/Week_05.md`) with proper Markdown formatting (valid for Obsidian rendering)
5. User receives clear error message if LLM API times out or fails; instructions to retry or manually complete notes

**Plans:** 2 plans in 2 waves

**Wave 1 (Parallel with Phase 2):**
- [ ] 03-01-PLAN.md — LLM integration & cost control (LLM-01, LLM-02, LLM-03, LLM-05, LLM-06, COST-01, COST-02, COST-03, COST-04)

**Wave 2 (Depends on Wave 1):**
- [ ] 03-02-PLAN.md — Obsidian output & formatting (LLM-04, OBS-01, OBS-02, OBS-03, OBS-04)

---

### Phase 4: Reliability & Recovery

**Goal:** Ensure production readiness with resumable processing, comprehensive error handling, privacy controls, and file sync validation.

**Depends on:** Phases 1-3 (all pipeline stages implemented)

**Requirements:** STATE-01, STATE-02, STATE-03, STATE-04, ERR-01, ERR-02, ERR-03, ERR-04, ERR-05, PRIV-03, PRIV-04, PRIV-05, SYNC-01, SYNC-02, SYNC-03, SYNC-04

**Success Criteria** (what must be TRUE):
1. System saves progress checkpoint after each stage (video download, transcript, audio, slides, LLM, Obsidian output); failed runs resume from last successful checkpoint without re-downloading
2. User can retry failed runs with `python run_week.py <config_file> --retry`; system skips completed stages and re-runs only failed steps
3. All failures logged to timestamped file with stage, error message, and recovery action; no silent failures (process always exits with status message)
4. System copies processed audio, slides, and transcript to Google Drive local sync folder (e.g., `/Business Analytics/Week_05/`); validates file copy success and quota
5. System detects and optionally removes PII from transcript before LLM call (student names, emails); temporary files cleaned up after processing (no residual data)

**Plans:** TBD

---

## Progress Tracking

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 4/4 | Complete | ✓ |
| 2. Media Processing | 1/3 | In Progress | ⊙ |
| 3. Intelligence & Output | 0/2 | Planning | ⊙ |
| 4. Reliability & Recovery | 0/? | Not started | — |

---

## Coverage Validation

**Requirement → Phase Mapping:**

| Category | Requirements | Phase |
|----------|--------------|-------|
| **Auth** | AUTH-01, AUTH-02, AUTH-03 | Phase 1 |
| **Download** | DOWN-01, DOWN-02, DOWN-03 | Phase 1 |
| **Config** | CONFIG-01, CONFIG-02, CONFIG-03, CONFIG-04 | Phase 1 |
| **Privacy (Setup)** | PRIV-01, PRIV-02 | Phase 1 |
| **Transcript** | TRAN-01, TRAN-02, TRAN-03, TRAN-04, TRAN-05 | Phase 2 |
| **Audio** | AUDIO-01, AUDIO-02, AUDIO-03, AUDIO-04 | Phase 2 |
| **Slides** | SLIDE-01, SLIDE-02, SLIDE-03, SLIDE-04, SLIDE-05 | Phase 2 |
| **LLM** | LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06 | Phase 3 |
| **Obsidian** | OBS-01, OBS-02, OBS-03, OBS-04 | Phase 3 |
| **Cost** | COST-01, COST-02, COST-03, COST-04 | Phase 3 |
| **State** | STATE-01, STATE-02, STATE-03, STATE-04 | Phase 4 |
| **Error** | ERR-01, ERR-02, ERR-03, ERR-04, ERR-05 | Phase 4 |
| **Privacy (Runtime)** | PRIV-03, PRIV-04, PRIV-05 | Phase 4 |
| **Sync** | SYNC-01, SYNC-02, SYNC-03, SYNC-04 | Phase 4 |

**Total Mapped:** 46/46 ✓  
**Unmapped:** 0 ✓

---

*Roadmap created: March 2, 2026*  
*Based on research: SUMMARY.md (HIGH confidence)*  
*Depth: Standard (4 coherent phases with balanced workload)*
