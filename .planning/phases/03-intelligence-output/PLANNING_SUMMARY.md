# Phase 03 Planning Summary

**Date:** March 2, 2026  
**Phase:** 03-intelligence-output  
**Mode:** Standard planning (mandatory discovery complete)  
**Status:** Planning Complete ✓

---

## Planning Context

**Source Material:**
- ROADMAP.md (Phase 3 goal and success criteria)
- REQUIREMENTS.md (14 Phase 3 requirements: LLM-01-06, OBS-01-04, COST-01-04)
- STATE.md (project state, prior decisions, Phase 2 complete)
- 03-RESEARCH.md (HIGH confidence, 900+ lines of technical research)

**Discovery Level:** Level 1 (Quick Verification)
- No novel external dependencies beyond phase planning
- OpenRouter/OpenAI APIs verified current in Feb-Mar 2026
- Tiktoken (official OpenAI) and tenacity (standard) are stable
- Obsidian markdown format stable

**Research Confidence:** HIGH
- OpenRouter API: Official docs verified Feb-Mar 2026
- Token pricing: Live OpenRouter dashboard March 2, 2026
- Feynman prompt structure: Research-validated in 03-RESEARCH.md
- Error handling patterns: Current industry standards

---

## Planning Decisions

### Structure: 2-Plan Phase with 2-Wave Execution

**Rationale:**
1. **Plan 03-01 (Wave 1):** LLM + Cost Control
   - Addresses: LLM-01, LLM-02, LLM-03, LLM-05, LLM-06, COST-01, COST-02, COST-03, COST-04 (9 requirements)
   - Focus: Token counting, budget enforcement, API integration, cost tracking
   - Scope: 3 tasks (token/budget/truncation, API calls + retry, cost tracking)
   - Context: ~50% (token counting + API patterns + cost tracking)

2. **Plan 03-02 (Wave 2):** Obsidian Output & Formatting
   - Depends on: 03-01 (uses LLMResult from Plan 01)
   - Addresses: LLM-04, OBS-01, OBS-02, OBS-03, OBS-04 (5 requirements)
   - Focus: Markdown formatting, vault integration, frontmatter
   - Scope: 3 tasks (markdown validation, vault writing, config + integration)
   - Context: ~50% (markdown validation + file I/O + configuration)

**Coverage:** All 14 Phase 3 requirements addressed across 2 plans. No orphaned requirements.

### Key Design Decisions

1. **Model Selection:** DeepSeek (default, $0.30/lecture) with Haiku fallback (complex content)
   - Rationale: Cost constraint (AUD $2-3/week for 4 lectures). DeepSeek verified at $0.20-0.30 per lecture.
   - Routing: Not in Phase 3 (deferred to Phase 4 multi-model strategy)

2. **Token Counting:** Official tiktoken library (OpenAI)
   - Rationale: Accurate, fast, no API calls needed
   - Alternative considered: Rough heuristics—rejected (inaccuracy risks budget overflow)

3. **Retry Strategy:** Tenacity library with exponential backoff
   - Rationale: Battle-tested, supports multiple retry patterns
   - Config: 3 attempts, 2s → 4s → 8s → 30s waits (429, 503, 504 only)
   - Fail-fast: 401 (auth) fails immediately

4. **Cost Tracking:** JSON file (no dependencies)
   - Rationale: Simple, human-readable, no database needed
   - Format: {"lectures": [...], "weekly_total": 0.0}
   - Display: ASCII box drawing for cost summaries

5. **Obsidian Output:** Direct markdown file writes (no API)
   - Rationale: Obsidian vault is local folder + markdown files. No SDK needed.
   - Frontmatter: YAML format (auto-generated tags, course/week/date/source)
   - Conflict prevention: Timestamp backups for existing files

### Deferred to Phase 4

The following are explicitly NOT in Phase 3 (research confirms they're reliability concerns):
- Checkpoint/resume logic (error recovery)
- PII scrubbing at LLM call boundary (Phase 2 handles this)
- Google Drive sync (separate from Obsidian output)
- State management across runs

---

## Plan Structure

### Plan 03-01: LLM Integration & Cost Control

| Aspect | Detail |
|--------|--------|
| **Wave** | 1 (parallel root) |
| **Tasks** | 3 |
| **Files Created** | src/llm_generator.py, src/cost_tracker.py, tests/test_*.py |
| **Files Modified** | src/models.py |
| **Requirements** | LLM-01, LLM-02, LLM-03, LLM-05, LLM-06, COST-01, COST-02, COST-03, COST-04 |
| **Autonomous** | Yes |

**Tasks:**
1. Token counting, budget validation, truncation (TokenCounter, BudgetValidator, TranscriptTruncator classes)
2. OpenRouter API integration with retry logic (LLMGenerator.generate_notes with @retry decorator)
3. Cost tracking with budget alerts (CostTracker class, weekly summary, per-lecture logging)

**Test Coverage:**
- TokenCounter: 4 tests (empty, short, long, unicode)
- BudgetValidator: 3 tests (pass, fail, buffer edge cases)
- TranscriptTruncator: 4 tests (no truncation, sampling, halving, coherence)
- LLMGenerator: 8+ tests (success, retry logic, errors, cost calculation, markdown output)
- CostTracker: 12+ tests (logging, summaries, budget alerts, estimation)

### Plan 03-02: Obsidian Output & Formatting

| Aspect | Detail |
|--------|--------|
| **Wave** | 2 (depends on 03-01) |
| **Tasks** | 3 |
| **Files Created** | src/obsidian_writer.py, tests/test_obsidian_writer.py, tests/test_integration.py |
| **Files Modified** | src/models.py, src/config.py |
| **Requirements** | LLM-04, OBS-01, OBS-02, OBS-03, OBS-04 |
| **Autonomous** | Yes |

**Tasks:**
1. Markdown validation and frontmatter generation (MarkdownValidator, FrontmatterGenerator, SectionValidator classes)
2. Vault file writing with error handling (VaultWriter class, atomic writes, conflict prevention)
3. Config integration + end-to-end pipeline (new config fields, run_lecture_pipeline orchestrator)

**Test Coverage:**
- MarkdownValidator: 4 tests (valid/invalid, unmatched brackets/fences, missing sections)
- FrontmatterGenerator: 4 tests (YAML format, tags, optional fields)
- SectionValidator: 3 tests (all sections present, missing sections, line numbers)
- VaultWriter: 8+ tests (vault existence, subfolder creation, file conflicts, permissions, unicode)
- ObsidianWriter: 4+ tests (end-to-end, error handling)
- Integration: 8+ tests (LLM→Obsidian pipeline, error paths)
- Config: 5+ tests (new fields, validation)

---

## Requirement Coverage

**All 14 Phase 3 requirements mapped to plans:**

| Requirement | Plan | Task | Addressed By |
|-------------|------|------|--------------|
| LLM-01 | 03-01 | Task 1 | TokenCounter.count_tokens() |
| LLM-02 | 03-01 | Task 1 | BudgetValidator.validate_token_budget() + TranscriptTruncator |
| LLM-03 | 03-01 | Task 2 | LLMGenerator.generate_notes() (OpenRouter API call) |
| LLM-04 | 03-02 | Task 1 | SYSTEM_PROMPT with 6 sections (verified in task 2 output) |
| LLM-05 | 03-01 | Task 2 | call_llm_with_retry() + error handling (RateLimitError, APIError, etc.) |
| LLM-06 | 03-01 | Task 1 | DeepSeek model selection + cost estimation |
| OBS-01 | 03-02 | Task 2 | VaultWriter.write_notes() |
| OBS-02 | 03-02 | Task 2 | Filename generation + subfolder support |
| OBS-03 | 03-02 | Task 2 | Error messages for vault/subfolder/permissions failures |
| OBS-04 | 03-02 | Task 1 | MarkdownValidator + 6-section structure |
| COST-01 | 03-01 | Task 3 | CostTracker (weekly JSON log) |
| COST-02 | 03-01 | Task 1 | BudgetValidator (pre-flight cost estimate) |
| COST-03 | 03-01 | Task 3 | CostTracker.log_lecture() |
| COST-04 | 03-01 | Task 3 | CostTracker.alert_if_over_budget() |

**Coverage:** 14/14 requirements ✓ (0 orphaned)

---

## Dependency Graph

```
Phase 02 outputs:
  - transcript_processor.py (cleaned transcript)
  - slide_extractor.py (extracted slide text)
  
Plan 03-01 (Wave 1):
  ├─ Task 1: Token counting, budget validation, truncation
  │  └─ Creates: LLMGenerator inputs (token counts, truncated text)
  ├─ Task 2: OpenRouter API integration + retry
  │  └─ Creates: LLMResult (status, content, tokens, cost)
  └─ Task 3: Cost tracking
     └─ Reads: LLMResult from Task 2
     └─ Creates: cost_tracking.json

Plan 03-02 (Wave 2, depends_on=[03-01]):
  ├─ Task 1: Markdown validation, frontmatter
  │  └─ Reads: LLMResult.content from Plan 03-01
  │  └─ Creates: ObsidianNote (frontmatter + content)
  ├─ Task 2: Vault writing
  │  └─ Reads: ObsidianNote + config (vault_path)
  │  └─ Creates: Week_NN.md in Obsidian vault
  └─ Task 3: Config + integration
     └─ Reads: All prior components
     └─ Creates: run_lecture_pipeline() orchestrator

Phase 04 (depends_on=[03-01, 03-02]):
  - Checkpoi
