# Project State: Automated Lecture Workflow

**Last Updated:** March 2, 2026  
**Project Phase:** Phase 1 (Foundation) - COMPLETE (All 4 Plans Done)  
**Mode:** YOLO (solo implementation)

---

## Project Reference

**Core Value:** Enable a business analytics student to process weekly lectures in one command, with all media privately stored locally and structured notes ready for review—without manual video cutting, uploads, or prompting.

**Key Constraint:** Cost stays under AUD $2–3/week using cheaper LLM models (DeepSeek ~$0.30/lecture, Claude Haiku ~$0.50/lecture).

**Success Metric:** Student processes 1 lecture with `python run_week.py week_05`, outputs appear in Obsidian vault in < 2 min, cost ≤ AUD $0.50, no manual intervention after setup (besides weekly cookie refresh).

---

## Current Position

**Current Focus:** Phase 1 (Foundation) - COMPLETE  
**Next Step:** Phase 2 Planning (Media Processing)

| Metric | Status |
|--------|--------|
| **Roadmap** | ✓ Complete (4 phases, 46 reqs mapped) |
| **Research** | ✓ Complete (HIGH confidence) |
| **Phase 1 Plan 01** | ✓ Complete (Config infrastructure) |
| **Phase 1 Plan 02** | ✓ Complete (Auth module) |
| **Phase 1 Plan 03** | ✓ Complete (Download + Transcript) |
| **Phase 1 Plan 04** | ✓ Complete (Error handling + logging + tests) |

---

## Phase Progress

| Phase | Goal | Reqs | Status |
|-------|------|------|--------|
| 1 | Foundation (Config, Auth, Download) | 12 | ✓ 100% Complete (All 4 plans done) |
| 2 | Media Processing (Transcript, Audio, Slides) | 14 | Not Started |
| 3 | Intelligence & Output (LLM, Obsidian, Cost) | 14 | Not Started |
| 4 | Reliability & Recovery (State, Error, Privacy, Sync) | 6 | Not Started |

**Overall Progress:** 26% (12 requirements completed: CONFIG-01-04, AUTH-01-03, DOWN-01-03, PRIV-01-02)

---

## Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| **4-phase structure** | Research suggested 3; rebalanced Phase 3 into Intelligence (LLM output) + Reliability (state/error/sync) for coherent boundaries and workload distribution | — Accepted |
| **Phase 1 first** | Download + validation are table-stakes blockers; unblock downstream phases | — Ready |
| **Phase 2 before LLM** | Transform raw media first; ensures LLM integration receives clean, validated input | — Ready |
| **Phase 3 for output** | Keeps LLM integration (core value) separate from reliability concerns; allows Phase 2 → Phase 3 demos | — Ready |
| **Phase 4 last** | Error handling, checkpointing, privacy are defensive; Phase 3 delivers working pipeline first | — Ready |

---

## Research Context

**Source:** `.planning/research/SUMMARY.md` (HIGH confidence, completed March 2, 2026)

**Key Findings:**
- **Recommended stack:** Python 3.11+, requests + tenacity (auth), typed-ffmpeg (audio), pdfplumber (slides), openai SDK with OpenRouter (LLM), tiktoken (token counting)
- **Critical pitfalls:** Cookie expiry, audio extraction silent failures, transcript GIGO, LLM token overflow, unattended process crashes
- **Feynman structure validated:** Summary + Key Concepts + Examples + Formulas + Pitfalls + Review Questions
- **Cost model:** DeepSeek $0.14/1M tokens (~$0.20–0.30/lecture), Claude Haiku $0.80/1M (~$0.50/lecture)
- **Architecture:** Stateful ETL pipeline with checkpoint/resume pattern; 5 major components (CLI, orchestrator, download, processing, LLM+output)

**Research gaps to address during Phase planning:**
- Feynman template validation (gather student notes, refine template)
- Multi-model routing strategy (benchmark DeepSeek vs Claude on sample transcripts)
- OCR accuracy on non-English slides (test if needed)
- Panopto API stability (monitor for auth changes)

---

## Accumulated Context

### Dependencies & Blockers

**None at roadmap stage.** All 4 phases are ordered for sequential execution with clear dependencies:
- Phase 1 unblocks Phase 2 (provides validated media)
- Phase 2 unblocks Phase 3 (provides cleaned data)
- Phase 3 unblocks Phase 4 (provides working pipeline to harden)

### Known Unknowns

1. **Feynman template specifics** - Research validates structure; actual prompt wording and section ordering to be determined during Phase 2 planning
2. **Multi-model routing thresholds** - Token count triggers for DeepSeek vs Claude to be benchmarked during Phase 2
3. **EasyOCR fallback accuracy** - On non-English slides; test if student has such lectures
4. **Panopto API changes** - Assume stable; monitor changelog

### Session Notes

- Roadmap created with 4-phase structure balancing workload: Phase 1 (12 reqs), Phase 2 (14 reqs), Phase 3 (14 reqs), Phase 4 (6 reqs)
- All 46 v1 requirements mapped with zero orphans
- Rebalanced from original 3-phase research mapping to improve coherence:
  - Phase 1: Foundation (auth, config, download validation)
  - Phase 2: Media processing (transcript, audio, slides)
  - Phase 3: Intelligence & output (LLM, Obsidian, cost tracking)
  - Phase 4: Reliability (state, error handling, privacy, sync)
- Ready for Phase 1 planning

---

## Execution Summary

**Phase 1 Plan 01 Completion (March 2, 2026):**
- **Duration:** 12 minutes
- **Tasks:** 3 completed (2 from plan + 1 fixing pre-existing)
- **Tests:** 12 new config tests (+ 30 existing = 42 total, all passing)
- **Requirements:** 4 completed (CONFIG-01, CONFIG-02, CONFIG-03, CONFIG-04)
- **Commits:** 4 atomic commits

**Key Deliverables:**
- Pydantic ConfigModel with YAML loader and comprehensive validation
- Example configuration file (config/example_week_05.yaml) for user reference
- Comprehensive README with setup guide, configuration reference, troubleshooting
- CLI entry point with emoji fixes for Windows compatibility
- 12 unit tests covering validation rules, error handling, YAML parsing

**Phase 1 Plan 02 Completion (March 2, 2026):**
- Cookie loading from browser JSON exports (Chrome, Firefox, Edge formats)
- Panopto session validation with dual strategies (GET /api/v1/user/me + HEAD fallback)
- AuthResult and SessionInfo data models
- Enhanced error messages with recovery instructions
- CLI integration in run_week.py

**Plan 01-03 Completion (March 1, 2026):**
- Streaming video download with cleanup-on-failure (8KB chunks)
- ffprobe video validation (size ≥100MB, duration ≥60s)
- Transcript download via Panopto API (graceful fallback)

**Cumulative Foundation (Plans 01-03):**
- All 42 tests passing (12 config + 11 auth + 12 download + 7 validator)
- 11 requirements completed (CONFIG-01-04, AUTH-01-03, DOWN-01-03, PRIV-02)
- Full pipeline: config validation → auth → download → validation → transcript
- Ready for Phase 2 (Media Processing)

## Next Checkpoint

**Action:** Begin Phase 2 Planning (Media Processing)

**Phase 1 Complete:**
- ✓ Plan 01: Config validation at startup
- ✓ Plan 02: Authentication via Panopto cookies
- ✓ Plan 03: Video download with cleanup on failure
- ✓ Plan 03: Video validation via ffprobe
- ✓ Plan 03: Transcript download
- ✓ Plan 04: Comprehensive error handling + recovery instructions
- ✓ Plan 04: Dual logging (file + console) with timestamps
- ✓ Plan 04: Security best practices (.gitignore, cookie storage documentation)
- ✓ Plan 04: Complete README documentation (400+ lines)
- ✓ All 58 tests passing (42 unit + 16 integration)

**Phase 1 Readiness Checklist:**
- ✓ Config validation at startup (Plan 01)
- ✓ Authentication via Panopto cookies (Plan 02)
- ✓ Video download with cleanup on failure (Plan 03)
- ✓ Video validation via ffprobe (Plan 03)
- ✓ Transcript download (Plan 03)
- ✓ Comprehensive error handling & recovery (Plan 04)
- ✓ Security practices & documentation (Plan 04)
- ✓ Comprehensive testing (58 tests, all passing - Plan 04)

---

**Phase 1 Plan 04 Completion (March 2, 2026):**
- **Duration:** 25 minutes
- **Tasks:** 4 completed (CLI orchestration, security setup, README, integration tests)
- **Tests:** 16 new integration tests (+ 42 existing = 58 total, all passing)
- **Requirements:** 1 completed (PRIV-01)
- **Commits:** 3 atomic commits

**Key Deliverables (Plan 04):**
- Improved run_week.py with comprehensive error handling
- Emoji progress indicators with Windows console fallback
- Dual logging to file and console with timestamps
- Updated .gitignore with security-first layout
- Complete README (400+ lines) with Quick Start, Configuration, Troubleshooting, Security sections
- 16 integration tests covering all major scenarios
- All error messages include recovery instructions

---

*State updated: March 2, 2026*  
*Phase 1 (Foundation) COMPLETE - All 4 Plans done. 12/12 Phase 1 requirements satisfied.*  
*Ready to begin Phase 2 (Media Processing) planning/execution.*
