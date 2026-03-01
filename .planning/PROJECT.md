# Automated Lecture Workflow

## What This Is

A Python-based automation pipeline that transforms university lecture videos (Panopto), transcripts, and slides into structured Feynman-style study notes in an Obsidian vault. Reduces manual work by 70%+ by automating downloads, audio extraction, file organization, and AI-powered note generation. Designed for Windows, cost-efficient (AUD $2–3/week), and highly reliable.

## Core Value

Enable a business analytics student to process weekly lectures in one command, with all media privately stored locally and structured notes ready for review—without manual video cutting, uploads, or prompting.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Download Panopto videos authenticated with stored cookies (no SSO automation)
- [ ] Extract/download Panopto transcripts automatically
- [ ] Extract audio from video using ffmpeg locally
- [ ] Pre-process transcripts (remove timestamps, filler words, redundancy)
- [ ] Copy audio, slides, and transcripts to local Google Drive sync folder
- [ ] Call LLM (DeepSeek or Claude Haiku via OpenRouter) with transcript + slide text
- [ ] Generate Feynman-style notes (summary, key concepts, examples, formulas, pitfalls, review questions)
- [ ] Save notes as Markdown in Obsidian vault (flat structure: /CourseName/Week_X.md)
- [ ] Handle failures gracefully (clear errors, save progress, allow re-runs from failure point)
- [ ] Cost stays under AUD $2–3/week using cheaper LLM models
- [ ] Support mixed (text-based + image-based) PDF slides with fallback to manual OCR if needed
- [ ] Run from single command: `python run_week.py week_05`
- [ ] Read lecture config from YAML (URLs, file paths, metadata)

### Out of Scope

- Real-time download progress UI (console logging is sufficient)
- MFA/SSO automation (cookie-based auth only)
- Automated Google Drive API OAuth setup (local folder sync simpler & more reliable)
- Full video trimming/editing (audio extraction only)
- Obsidian plugin integration (direct Markdown file writes)
- Mobile app or web interface (CLI-only)

## Context

**Student workflow challenges:**
- Current process: 45–60 min/week per lecture manually cutting video, uploading files, prompting LLM, organizing notes
- Pain points: Clipchamp crashes, manual uploads error-prone, MFA login fragile, fragmented notes
- Solution: Single Python script orchestrates entire pipeline with sensible defaults

**Technical environment:**
- Windows 10/11 (Surface laptop)
- Google Drive synced locally (G:\ or similar)
- Obsidian vault already exists (local folder structure)
- OpenRouter API for LLM access (cheaper than direct Claude/OpenAI)
- University LMS provides Panopto video & transcript links

**Key ecosystem facts:**
- Panopto cookies expire weekly; student will refresh from browser once/week
- Transcripts available as .vtt or .txt via Panopto API
- ffmpeg available on Windows (or installed via script)
- DeepSeek or Claude 3.5 Haiku via OpenRouter costs ~0.30–0.50 AUD per lecture (well under $2–3 budget)

## Constraints

- **Cost**: Must stay under AUD $2–3/week (DeepSeek: ~0.30 AUD/lecture, Claude Haiku: ~0.50 AUD/lecture)
- **Reliability**: Better to fail fast with clear error than silently break
- **Privacy**: Raw media, transcripts stay local or on personal Google Drive; only text sent to LLM
- **Setup**: Must be simple enough for someone comfortable with Python but not an expert
- **OS**: Windows-primary (but should not use Windows-only APIs if avoidable)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use cookies for Panopto auth instead of SSO automation | SSO with MFA is fragile and breaks with security updates; cookies stable and manageable | — Pending |
| Local Google Drive sync folder instead of Google Drive API | Simpler setup, more reliable, no OAuth complexity, student already has sync folder | — Pending |
| DeepSeek or Claude Haiku via OpenRouter instead of Sonnet | Keeps cost under budget while maintaining note quality | — Pending |
| Pre-process transcripts before LLM (remove timestamps, filler) | Reduces token count, keeps cost low, improves note clarity | — Pending |
| Save progress between pipeline stages (cache video/transcript) | Allows re-running only failed steps without re-downloading | — Pending |
| Flat Obsidian structure (/CourseName/Week_X.md) over nested | Simpler organization, easier to manage, cleaner backlinks | — Pending |
| Include full Feynman elements (summary, concepts, examples, formulas, pitfalls, questions) | Maximizes study value without bloating tokens too much | — Pending |

---
*Last updated: 2026-03-02 after deep questioning*
