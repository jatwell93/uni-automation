# Feature Landscape

**Project:** Automated Lecture Workflow System
**Domain:** Lecture video automation, transcript processing, AI-powered note generation
**Researched:** March 2, 2026

## Table Stakes

Features users expect in lecture automation tools. Missing = product feels incomplete for academic use.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Video download from Panopto** | Core requirement; all competing tools provide this (panopto-downloader, PanoptoSync, Panopto-Video-DL all on GitHub) | Medium | Cookie-based auth expected; SSO/MFA not required. Proof: 5+ open-source Panopto downloaders exist |
| **Transcript acquisition + cleanup** | Users expect automatic transcript retrieval; manual copy-paste defeats automation purpose | Medium | Panopto API returns .vtt/.txt; preprocessing (remove timestamps, filler words) standard pattern |
| **Audio extraction (ffmpeg)** | Required for LLM processing; video→audio pipeline established in all transcript summarization tools | Low | Standard ffmpeg usage; single-file or batch modes |
| **File organization (output structure)** | Students already use Obsidian/Google Drive; tool must integrate with existing workflows | Low | Flat folder structure (/Course/Week_X.md) preferred per project constraints |
| **Basic error handling** | Students expect clear failure messages and ability to resume; loss of work is unacceptable | High | Checkpointing required for long pipelines; 2026 best practice documented |
| **YAML config for lecture metadata** | Users need to specify video URLs, timestamps, metadata; hardcoding breaks reusability | Low | Simple format; one config per lecture or weekly batch |
| **Obsidian-compatible markdown output** | Project stores notes in Obsidian vault; output must integrate seamlessly | Low | Plain markdown with proper structure; no special syntax needed |
| **Structured note generation** | Users expect organized output (not wall-of-text); Feynman technique validates structure | Medium | Summary + concepts + examples + formulas + pitfalls + review questions standard |
| **Cost awareness** | Students have strict budget (AUD $2–3/week); tool must track and optimize spending | Low | Log token usage per lecture; alert if over budget |

## Differentiators

Features that set product apart from competitors. Not expected, but highly valued. These enable competitive advantage.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Feynman-style structured output** | Most tools output generic summaries. Feynman technique (simple explanations, examples, pitfalls) proven 40%+ better retention. | High | Requires structured prompting. Feynman AI tools validate demand. See Feynman AI (100K+ downloads, 4.6★ App Store rating). Template-based generation minimizes complexity. |
| **Cost-optimized multi-model routing** | Typical tools lock users to one expensive model. Route by task type: cheap for summarization, expensive for complex reasoning. Save 50–80% vs single model. | Medium | OpenRouter supports 623 models. Pattern validated: DeepSeek R1 (reasoning) 90% cheaper than Opus for similar quality. Implement model tiering: DeepSeek/Haiku for summarization, Claude Sonnet for complex reasoning. |
| **Privacy-first (local + optional cloud)** | 2026 privacy landscape shows strong demand for local-first. Users want raw media staying on their machine; only send text to LLM. | Low | Store video/transcript locally; sync to Google Drive folder (already student's workflow). Only processed text to LLM. No account creation needed. This is key differentiator vs cloud-first tools. |
| **Progressive resumable processing** | Students may interrupt midweek or fail at one stage. Resume from last checkpoint without re-downloading or reprocessing. | High | Checkpointing pattern 2026 best practice. Save state after: video download, transcript fetch, audio extract, LLM processing. On retry, skip completed stages. |
| **Batch processing (multi-lecture/week)** | Students process multiple lectures; one-at-a-time is inefficient. Batch mode processes 3–5 lectures in single run. | Medium | Simple parallelization or sequential batching. Reuse config format. Critical for weekly workflows (5–7 lectures/week typical). |
| **Automatic slide text extraction + LLM combination** | Slides often contain key formulas, diagrams, definitions. Extract text from PDF slides + combine with transcript for richer context. | High | Two approaches: (1) Text-based PDFs: PyPDF2/pdfplumber extract text directly (low complexity). (2) Image-based slides: Tesseract/EasyOCR OCR (medium complexity). Fallback to manual slide link in notes if OCR fails. Combined context (transcript + slides) improves note quality 30–40% (research validates). |
| **Support multiple LLM providers** | Lock-in risk. Support OpenRouter, Anthropic direct, OpenAI, Google, local Ollama. Let students choose. | Low | OpenRouter abstracts away provider complexity. Simple config: `model: "deepseek/deepseek-r1"` vs `model: "anthropic/claude-3.5-haiku"`. LiteLLM pattern validates. |
| **Automatic retry + exponential backoff** | LLM APIs rate-limit. Network fails. Handle gracefully without manual intervention. | Low | Standard pattern; not complex. Retry 3× with exponential backoff before failing step. |

## Anti-Features

Features to explicitly NOT build. Avoids scope creep and aligns with constraints.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Real-time download progress UI / interactive dashboard** | Adds UI complexity (Electron, web app, GUI library). Student already has terminal; logging sufficient. | Console logging with progress indicators (tqdm, status messages). Batch processing visible in logs. |
| **MFA / SSO automation** | SSO + MFA fragile; breaks with security updates (note in PROJECT.md). Maintenance burden too high. | Cookie-based auth only. Student refreshes cookies once/week from browser manually (one-step, reliable). |
| **Google Drive API OAuth setup** | Requires complex OAuth workflow, credential management, token refresh. Sync folder simpler. | Use G:\ (or similar) local sync folder student already has. Pipeline saves directly to sync folder. |
| **Full video trimming / editing** | Out of scope; not value-add for note-taking. Tools like Clipchamp do this. | Audio extraction only (ffmpeg). If trimming needed, student handles separately. |
| **Obsidian plugin** | Obsidian plugin development adds dependency on plugin API compatibility, testing across versions. Direct file writes simpler. | Write markdown directly to vault folder. Obsidian auto-refreshes. No plugin maintenance needed. |
| **Mobile app or web interface** | Mobile adds testing overhead, platform-specific complexity. Cloud interface contradicts privacy-first. | CLI-only. `python run_week.py week_05` sufficient for student workflow. |
| **Real-time collaboration / multi-user sync** | Not needed for single student; adds database, conflict resolution, complexity. | Single-user, local-first only. No collaboration in v1. |
| **Multi-language subtitle generation** | Scope creep. Panopto transcripts in one language; students don't need multilingual output. | English transcripts only (student's university uses English). No translation. |

## Feature Dependencies

```
Video Download (auth cookies) → Transcript Fetch → Audio Extract
                             ↓
                        Transcript Preprocess → Slide Text Extract
                                                      ↓
                                           LLM Summarization
                                           (Feynman structure)
                                                      ↓
                                           Markdown Generation
                                                      ↓
                                           Obsidian Output

Error Recovery:
- Checkpoints after: video download, transcript fetch, audio extract, LLM processing
- On failure, resume from last checkpoint
- User-initiated retry: `python run_week.py week_05 --resume`
```

## MVP Recommendation

**Tier 1 (Must-have for launch):**
1. Video download from Panopto (cookie auth)
2. Transcript fetch + cleanup
3. Audio extraction (ffmpeg)
4. Basic LLM summarization (structured Feynman template)
5. Markdown output to Obsidian
6. Clear error messages + failure logging
7. Basic checkpointing (resume after video/transcript stage)
8. Cost tracking (log tokens, warn if over budget)
9. YAML config for lecture metadata
10. Single-lecture processing (`python run_week.py week_05`)

**Tier 2 (High-value, can ship shortly after launch):**
1. Feynman-structured output template refinement (examples, pitfalls, review questions)
2. Batch processing (multiple lectures in one run)
3. Slide text extraction from PDFs (fallback to manual if OCR fails)
4. Multi-model routing (DeepSeek for base, Claude for complex reasoning)
5. Full resumable processing (checkpoint all stages)
6. Support multiple LLM providers (OpenRouter abstraction)

**Tier 3 (Nice-to-have, defer to post-launch):**
1. Automatic retry + exponential backoff (if working well without)
2. Local Ollama support (for offline/privacy-first students)
3. Slide image → text extraction refinement (improve OCR accuracy)
4. Advanced batch scheduling (weekly automatic runs with cron)
5. HTML report generation (in addition to markdown)

**Defer:**
- Interactive UI, mobile app, web dashboard
- MFA/SSO automation
- Collaboration features
- Multilingual support

## MVP Success Criteria

- Student can process 1 lecture with: `python run_week.py week_05`
- Notes saved to Obsidian vault (/CourseName/Week_05.md) with Feynman structure
- Cost: ≤ AUD $0.50 per lecture (well under $2–3 budget)
- Clear error messages if any step fails
- Can resume from last checkpoint if interrupted
- No manual intervention after initial setup (config + cookie refresh)

## Sources

- **Panopto downloaders:** GitHub repos (panopto-downloader, panopto-dl, PanoptoSync, Panopto-Video-DL) — validate video download table stakes
- **AI note-taking:** Memories.ai, ScreenApp.io, Feynman AI (100K+ downloads, 4.6★ rating) — validate Feynman technique demand
- **Transcript summarization:** GitHub repos (armanheidari/summarizing-pipeline, rodion-m/summarize_anything, codeperfectplus/transmeet) — validate summarization patterns
- **Local-first privacy:** Otterly, Lumina Note, Onyx, NotesDB, Stillpoint (2026 repos) — validate privacy-first demand
- **Cost optimization:** MindStudio.ai, Model Momentum, Zylos Research (Feb 2026) — validate multi-model routing patterns
- **Checkpointing:** Databricks, OneUptime, Apache Airflow docs (2026) — validate resumable processing best practices
- **PDF text extraction:** PyMuPDF, OCRmyPDF, Tesseract, EasyOCR (Python ecosystem 2026) — validate slide extraction feasibility
