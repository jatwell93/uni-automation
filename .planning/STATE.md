# Project State: Automated Lecture Workflow

**Last Updated:** March 2, 2026  
**Project Phase:** Roadmap Complete  
**Mode:** YOLO (solo implementation)

---

## Project Reference

**Core Value:** Enable a business analytics student to process weekly lectures in one command, with all media privately stored locally and structured notes ready for review—without manual video cutting, uploads, or prompting.

**Key Constraint:** Cost stays under AUD $2–3/week using cheaper LLM models (DeepSeek ~$0.30/lecture, Claude Haiku ~$0.50/lecture).

**Success Metric:** Student processes 1 lecture with `python run_week.py week_05`, outputs appear in Obsidian vault in < 2 min, cost ≤ AUD $0.50, no manual intervention after setup (besides weekly cookie refresh).

---

## Current Position

**Current Focus:** Roadmap + Research Phase Complete  
**Next Step:** Begin Phase 1 (Foundation) planning via `/gsd-plan-phase 1`

| Metric | Status |
|--------|--------|
| **Roadmap** | ✓ Complete (4 phases, 46 reqs mapped) |
| **Research** | ✓ Complete (HIGH confidence) |
| **Phase 1 Planned** | ⏳ Pending |
| **Phase 1 In Progress** | — |
| **Phase 1 Complete** | — |

---

## Phase Progress

| Phase | Goal | Reqs | Status |
|-------|------|------|--------|
| 1 | Foundation (Config, Auth, Download) | 12 | Not Started |
| 2 | Media Processing (Transcript, Audio, Slides) | 14 | Not Started |
| 3 | Intelligence & Output (LLM, Obsidian, Cost) | 14 | Not Started |
| 4 | Reliability & Recovery (State, Error, Privacy, Sync) | 6 | Not Started |

**Overall Progress:** 0% (0 requirements completed)

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

## Next Checkpoint

**Action:** Begin Phase 1 planning with `/gsd-plan-phase 1`

**Inputs needed:**
- Phase 1 scope confirmed (12 requirements across auth, download, config)
- Phase 1 success criteria validated (5 observable behaviors)

**Outputs expected:**
- Phase 1 implementation plan with concrete tasks
- Decomposed into 3–5 subtasks with estimated effort
- Risk flags for cookie validation, Windows path handling, ffprobe integration

---

*State initialized: March 2, 2026*  
*Ready for Phase 1 planning*
