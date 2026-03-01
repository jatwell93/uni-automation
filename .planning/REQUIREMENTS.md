# Requirements: Automated Lecture Workflow

**Defined:** 2026-03-02
**Core Value:** Enable a business analytics student to process weekly lectures in one command, with all media privately stored locally and structured notes ready for review—without manual video cutting, uploads, or prompting.

## v1 Requirements

### Authentication & Download

- [ ] **AUTH-01**: System can load Panopto authentication cookies from config file
- [ ] **AUTH-02**: System validates cookie freshness before download attempt (test API call succeeds)
- [ ] **AUTH-03**: User receives clear error if cookie is invalid or expired (with recovery instructions)
- [x] **DOWN-01**: System downloads Panopto video file using authenticated cookie ✓ (Plan 01-03)
- [x] **DOWN-02**: Downloaded video file is validated for integrity (file size > 0, ffprobe succeeds) ✓ (Plan 01-03)
- [x] **DOWN-03**: Download failures produce clear error messages (partial files cleaned up) ✓ (Plan 01-03)

### Transcript Handling

- [ ] **TRAN-01**: System extracts or downloads Panopto transcript (VTT/SRT/TXT format)
- [ ] **TRAN-02**: System parses transcript into clean text (removes timestamps and formatting)
- [ ] **TRAN-03**: System removes filler words ('um', 'uh', 'like') to reduce verbosity
- [ ] **TRAN-04**: System handles missing or malformed transcripts with clear error (allows manual upload)
- [ ] **TRAN-05**: Cleaned transcript passed to LLM contains no identifying information (student names/emails stripped)

### Audio Extraction

- [ ] **AUDIO-01**: System extracts audio from downloaded video using ffmpeg locally
- [ ] **AUDIO-02**: Extracted audio file is validated (duration > 0, plays without corruption)
- [ ] **AUDIO-03**: Extraction errors produce clear error message with recovery instructions
- [ ] **AUDIO-04**: Audio file is saved to local temporary directory before upload

### Slide Processing

- [ ] **SLIDE-01**: System reads PDF slides from provided file path
- [ ] **SLIDE-02**: System extracts text from text-based PDF slides using pdfplumber
- [ ] **SLIDE-03**: System detects image-based/scanned slides and flags for manual OCR (or uses EasyOCR as fallback)
- [ ] **SLIDE-04**: Extracted slide text organized by page for LLM consumption
- [ ] **SLIDE-05**: Missing or unreadable slides produce clear error (notes can generate without slide text)

### File Organization & Sync

- [ ] **SYNC-01**: System copies audio, slides, and transcript to Google Drive local sync folder
- [ ] **SYNC-02**: Files organized in Google Drive subfolder by course/week (e.g., /Business Analytics/Week_05/)
- [ ] **SYNC-03**: File copy success validated (target file exists, size matches source)
- [ ] **SYNC-04**: Google Drive quota errors produce clear message (with manual fallback instructions)

### LLM Integration & Note Generation

- [ ] **LLM-01**: System counts tokens in transcript + slide text before API call
- [ ] **LLM-02**: System truncates content if token count exceeds budget (0.30 AUD / lecture with headroom)
- [ ] **LLM-03**: System calls OpenRouter API with prompt for Feynman-style notes
- [ ] **LLM-04**: System generates Markdown notes with 6 sections: Summary, Key Concepts, Examples, Formulas, Pitfalls, Review Questions
- [ ] **LLM-05**: LLM timeouts or API errors handled with clear message and retry instructions
- [ ] **LLM-06**: Cost per lecture stays under 0.50 AUD (using DeepSeek or Claude Haiku via OpenRouter)

### Obsidian Vault Output

- [ ] **OBS-01**: System writes generated notes to Obsidian vault as Markdown file
- [ ] **OBS-02**: Notes saved to configured path (e.g., /Business Analytics/Week_05.md)
- [ ] **OBS-03**: File write errors produce clear message (with manual folder creation instructions)
- [ ] **OBS-04**: Generated notes are properly formatted Markdown (valid for Obsidian rendering)

### Configuration & CLI

- [x] **CONFIG-01**: System reads lecture config from YAML file with lecture URL, slides path, metadata
- [x] **CONFIG-02**: System runs from single command: `python run_week.py <config_file>`
- [x] **CONFIG-03**: User receives progress output at each pipeline stage
- [x] **CONFIG-04**: Invalid config produces clear error message (schema validation)

### State & Recovery

- [ ] **STATE-01**: System saves progress checkpoint after each pipeline stage (video, transcript, audio, slides, LLM, output)
- [ ] **STATE-02**: Failed runs can resume from last successful checkpoint without re-downloading
- [ ] **STATE-03**: Failed files are cleaned up (no partial/corrupt files left behind)
- [ ] **STATE-04**: User can force re-run of specific stage (e.g., re-generate notes with different LLM)

### Error Handling & Reliability

- [ ] **ERR-01**: All failures logged to file (timestamp, stage, error message, recovery action)
- [ ] **ERR-02**: Clear error messages guide user to fix or manual workaround
- [ ] **ERR-03**: No silent failures (process never exits without status message)
- [ ] **ERR-04**: Retryable errors (network) get exponential backoff, up to 3 attempts
- [ ] **ERR-05**: Fatal errors (auth, config) fail fast with clear message

### Privacy & Security

- [ ] **PRIV-01**: Panopto cookies stored in config file (encrypted or with ACL recommended)
- [x] **PRIV-02**: Raw media (video, audio) never uploaded to external service except Google Drive (personal account) ✓ (Plan 01-03)
- [ ] **PRIV-03**: Only transcript + slide text sent to LLM (no video/audio binaries)
- [ ] **PRIV-04**: Transcript checked for PII before LLM call (student names, emails stripped)
- [ ] **PRIV-05**: Temporary files cleaned up after processing (no residual data)

### Cost Management

- [ ] **COST-01**: Weekly cost for processing 4 lectures stays under AUD $2–3
- [ ] **COST-02**: Token counting provides cost pre-flight estimate before LLM call
- [ ] **COST-03**: Cost tracking logged per lecture (for weekly budget review)
- [ ] **COST-04**: System alerts if single lecture exceeds 0.50 AUD budget

## v2 Requirements

### Advanced Features

- **BATCH-01**: Batch processing multiple lectures in one run
- **ROUTE-01**: Multi-model routing (use DeepSeek for simple lectures, Claude Sonnet for complex)
- **CACHE-01**: Cache extracted slide text for lectures with same slides
- **NOTIF-01**: Email summary of weekly processing (cost, notes generated, failures)
- **OBSID-01**: Obsidian plugin for vault auto-detection and note preview

### Integration & Scaling

- **INTEGR-01**: Support other LLM providers (local Ollama, Anthropic direct, OpenAI)
- **INTEGR-02**: Support other cloud storage (Dropbox, OneDrive, S3)
- **INTEGR-03**: Support other note-taking apps (OneNote, Notion, Apple Notes)
- **INTEGR-04**: Scheduled runs via cron (automated weekly processing)

## Out of Scope

| Feature | Reason |
|---------|--------|
| MFA/SSO automation | Too fragile; cookie-based auth simpler and more reliable |
| Google Drive API OAuth | Local sync folder simpler; no service account needed |
| Real-time collaboration | Out of scope; single-user CLI tool |
| Video editing/trimming | Audio extraction sufficient; no frame-level editing needed |
| Web UI or dashboard | CLI sufficient for power user; GUI can be v2+ |
| Mobile app | Windows desktop primary; mobile later (if demand exists) |
| Obsidian plugin | Direct Markdown files sufficient; plugin can be v2+ |
| Integration with Canvas/Blackboard | Panopto URLs only; other LMS systems out of scope for v1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 | Pending |
| AUTH-02 | Phase 1 | Pending |
| AUTH-03 | Phase 1 | Pending |
| DOWN-01 | Phase 1 | Complete (01-03) |
| DOWN-02 | Phase 1 | Complete (01-03) |
| DOWN-03 | Phase 1 | Complete (01-03) |
| TRAN-01 | Phase 2 | Pending |
| TRAN-02 | Phase 2 | Pending |
| TRAN-03 | Phase 2 | Pending |
| TRAN-04 | Phase 2 | Pending |
| TRAN-05 | Phase 2 | Pending |
| AUDIO-01 | Phase 2 | Pending |
| AUDIO-02 | Phase 2 | Pending |
| AUDIO-03 | Phase 2 | Pending |
| AUDIO-04 | Phase 2 | Pending |
| SLIDE-01 | Phase 2 | Pending |
| SLIDE-02 | Phase 2 | Pending |
| SLIDE-03 | Phase 2 | Pending |
| SLIDE-04 | Phase 2 | Pending |
| SLIDE-05 | Phase 2 | Pending |
| SYNC-01 | Phase 4 | Pending |
| SYNC-02 | Phase 4 | Pending |
| SYNC-03 | Phase 4 | Pending |
| SYNC-04 | Phase 4 | Pending |
| LLM-01 | Phase 3 | Pending |
| LLM-02 | Phase 3 | Pending |
| LLM-03 | Phase 3 | Pending |
| LLM-04 | Phase 3 | Pending |
| LLM-05 | Phase 3 | Pending |
| LLM-06 | Phase 3 | Pending |
| OBS-01 | Phase 3 | Pending |
| OBS-02 | Phase 3 | Pending |
| OBS-03 | Phase 3 | Pending |
| OBS-04 | Phase 3 | Pending |
| CONFIG-01 | Phase 1 | Complete (Plan 01-01) |
| CONFIG-02 | Phase 1 | Complete (Plan 01-01) |
| CONFIG-03 | Phase 1 | Complete (Plan 01-01) |
| CONFIG-04 | Phase 1 | Complete (Plan 01-01) |
| STATE-01 | Phase 4 | Pending |
| STATE-02 | Phase 4 | Pending |
| STATE-03 | Phase 4 | Pending |
| STATE-04 | Phase 4 | Pending |
| ERR-01 | Phase 4 | Pending |
| ERR-02 | Phase 4 | Pending |
| ERR-03 | Phase 4 | Pending |
| ERR-04 | Phase 4 | Pending |
| ERR-05 | Phase 4 | Pending |
| PRIV-01 | Phase 1 | Pending |
| PRIV-02 | Phase 1 | Complete (01-03) |
| PRIV-03 | Phase 4 | Pending |
| PRIV-04 | Phase 4 | Pending |
| PRIV-05 | Phase 4 | Pending |
| COST-01 | Phase 3 | Pending |
| COST-02 | Phase 3 | Pending |
| COST-03 | Phase 3 | Pending |
| COST-04 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 46 total
- Mapped to phases: 46
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-02*
*Last updated: 2026-03-01 after Plan 01-03 completion*
*Progress: 4/46 requirements complete (DOWN-01, DOWN-02, DOWN-03, PRIV-02)*
