#!/usr/bin/env python3
"""
Generate Feynman-technique study notes from downloaded lecture transcripts.

Usage:
    python generate_notes.py --course MIS271 --week 1 --session lecture
    python generate_notes.py --course MIS271 --week 1 --estimate-only
    python generate_notes.py --course MIS271 --week 1 --session prac --model claude-3-haiku-20240307
    python generate_notes.py --course MIS271 --weeks 1-5 --session lecture

Exit codes: 0 on success, 1 on error.
"""

import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path

# Force UTF-8 output on Windows (avoids UnicodeEncodeError for checkmarks etc.)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv()

from src.cost_tracker import CostTracker, estimate_cost
from src.course_manager import CourseManager
from src.llm_generator import LLMGenerator, TokenCounter
from src.obsidian_writer import FrontmatterGenerator, MarkdownValidator
from src.slide_extractor import SlideExtractor
from src.transcript_processor import TranscriptProcessor
from src.url_fetcher import fetch_url_to_file, url_to_filename

logging.basicConfig(
    level=logging.WARNING,  # Suppress verbose src/ logs; print progress directly
    format="%(name)s [%(levelname)s] %(message)s",
)

DEFAULT_OBSIDIAN_VAULT = r"C:\Users\josha\OneDrive\Documents\Obsidian Vault\University notes\Trimester_1_26"
DEFAULT_MODEL = "deepseek/deepseek-chat"


def _print(symbol: str, message: str) -> None:
    """Print progress with ASCII-safe symbol fallback for Windows console."""
    try:
        print(f"{symbol} {message}")
    except UnicodeEncodeError:
        fallback = {"✓": "[OK]", "✗": "[ERR]", "~": "[WARN]", "→": "->"}
        print(f"{fallback.get(symbol, '[*]')} {message}")


def _parse_week_range(value: str) -> list[int]:
    """Parse '1-11' or '3' into a list of week numbers."""
    if "-" in value:
        parts = value.split("-", 1)
        try:
            start, end = int(parts[0]), int(parts[1])
            return list(range(start, end + 1))
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"Invalid week range '{value}'. Use format: 1-11 or single number."
            )
    try:
        return [int(value)]
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid week '{value}'. Use a number or range like 1-11."
        )


def gather_supplementary_context(session_dir: Path) -> tuple[str, list[str]]:
    """
    Collect slides and extra reading files from the session folder.

    Looks for:
    - slides.pdf       → labelled SLIDES (listed first)
    - any other .pdf   → labelled READING: <filename>
    - any extra .txt   → labelled NOTES: <filename> (skips transcript.*)

    Returns:
        (combined_context_string, list_of_found_filenames)
    """
    SKIP_NAMES = {"transcript.txt", "transcript.vtt"}
    extractor = SlideExtractor()
    sections: list[str] = []
    found: list[str] = []

    # Collect PDFs: slides.pdf first, then everything else
    pdfs = sorted(session_dir.glob("*.pdf"), key=lambda p: (p.name != "slides.pdf", p.name))
    for pdf in pdfs:
        label = "SLIDES" if pdf.name == "slides.pdf" else f"READING: {pdf.name}"
        result = extractor.extract_slide_text(pdf)
        if result.status == "success" and result.slide_text:
            sections.append(f"--- {label} ---\n{result.slide_text}")
            found.append(pdf.name)
        else:
            found.append(f"{pdf.name} (unreadable — skipped)")

    # Extra .txt files (not transcript)
    for txt in sorted(session_dir.glob("*.txt")):
        if txt.name.lower() in SKIP_NAMES:
            continue
        try:
            content = txt.read_text(encoding="utf-8", errors="replace").strip()
            if content:
                sections.append(f"--- NOTES: {txt.name} ---\n{content}")
                found.append(txt.name)
        except OSError:
            found.append(f"{txt.name} (unreadable — skipped)")

    # Fetched URL content saved as .md files by url_fetcher
    for md in sorted(session_dir.glob("*.md")):
        try:
            content = md.read_text(encoding="utf-8", errors="replace").strip()
            if content:
                sections.append(f"--- READING: {md.name} ---\n{content}")
                found.append(md.name)
        except OSError:
            found.append(f"{md.name} (unreadable — skipped)")

    return "\n\n".join(sections), found


def process_lecture(
    course_code: str,
    week: int,
    session: str,
    model: str,
    api_key: str,
    vault_path: Path,
    estimate_only: bool,
    urls: list[str] | None = None,
) -> bool:
    """
    Process a single lecture: transcript → LLM → Obsidian.

    Returns True on success, False on failure.
    """
    label = f"{course_code} Week {week:02d} {session}"
    print(f"\n--- {label} ---")

    # 1. Find transcript
    manager = CourseManager()
    transcript_path = manager.find_transcript(course_code, week, session)

    if transcript_path is None:
        _print(
            "✗",
            f"Transcript not found for {label}.\n"
            f"  Expected: downloads/{course_code}_week_{week:02d}_{session}/week_{week:02d}_{session}/transcript.txt",
        )
        return False

    _print("✓", f"Transcript: {transcript_path}")

    # 2. Fetch external URLs into session folder (if provided)
    session_dir = transcript_path.parent
    if urls:
        for url in urls:
            filename = url_to_filename(url)
            dest = session_dir / filename
            if dest.exists():
                _print("✓", f"URL cached: {filename}")
            else:
                _print("→", f"Fetching {url} ...")
                ok = fetch_url_to_file(url, dest)
                if ok:
                    _print("✓", f"Saved: {filename}")
                else:
                    _print("~", f"Could not fetch {url} — skipped")

    # 3. Gather supplementary context (slides, readings, fetched URLs) from the session folder
    supplementary_context, found_files = gather_supplementary_context(session_dir)
    if found_files:
        _print("✓", f"Supplementary context: {', '.join(found_files)}")
    else:
        _print("~", "No slides or readings found in session folder (transcript only)")

    # 4. Clean transcript
    processor = TranscriptProcessor()
    result = processor.process(transcript_path)

    if result.status == "error":
        _print("✗", f"Transcript processing failed: {result.error_message}")
        return False

    if result.error_message:
        _print("~", f"Warning: {result.error_message}")

    transcript_text = result.cleaned_text
    _print(
        "✓",
        f"Transcript cleaned: {result.word_count:,} words "
        f"(from {result.original_word_count:,})",
    )

    # 5. Cost estimate (transcript + supplementary context)
    token_counter = TokenCounter()
    input_tokens = token_counter.count_tokens(transcript_text + supplementary_context)
    estimated_cost = estimate_cost(input_tokens, 600, model)
    print(
        f"  Cost estimate: {input_tokens:,} tokens -> AUD ${estimated_cost:.4f} "
        f"(budget: $0.30)"
    )

    if estimate_only:
        return True

    # 6. Generate notes
    _print("→", f"Calling {model}...")
    generator = LLMGenerator({"openrouter_api_key": api_key})
    llm_result = generator.generate_notes(transcript_text, supplementary_context, model)

    if llm_result.status != "success":
        _print("✗", f"LLM generation failed: {llm_result.error_message}")
        return False

    _print(
        "✓",
        f"Notes generated: {llm_result.input_tokens:,} input, "
        f"{llm_result.output_tokens:,} output tokens",
    )

    # 7. Build complete note (frontmatter + content)
    fm_gen = FrontmatterGenerator()
    frontmatter = fm_gen.generate_frontmatter(
        {
            "course": course_code,
            "week": week,
            "date": date.today().isoformat(),
            "panopto_url": "",
            "title": f"{course_code} Week {week:02d} {session.title()}",
        }
    )
    complete_note = frontmatter + "\n" + llm_result.content

    # Validate markdown (warn only — LLM output may vary slightly)
    validator = MarkdownValidator()
    validation_result = validator.is_valid_markdown(complete_note)
    try:
        is_valid, issues = validation_result
    except (TypeError, ValueError):
        is_valid, issues = True, []
    if not is_valid:
        _print("~", f"Markdown validation warnings: {', '.join(issues)}")

    # 8. Write to Obsidian vault
    note_dir = vault_path / "Lectures" / course_code
    note_dir.mkdir(parents=True, exist_ok=True)

    note_path = note_dir / f"Week_{week:02d}_{session}.md"

    if note_path.exists():
        from datetime import datetime

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        note_path = note_dir / f"Week_{week:02d}_{session}__{ts}.md"
        _print("~", f"Note already exists; saving as {note_path.name}")

    try:
        note_path.write_text(complete_note, encoding="utf-8")
        _print("✓", f"Saved: {note_path}")
    except OSError as e:
        _print("✗", f"Failed to write note: {e}")
        return False

    # 9. Track cost
    tracker = CostTracker()
    tracker.log_lecture(
        lecture_name=label,
        input_tokens=llm_result.input_tokens,
        output_tokens=llm_result.output_tokens,
        model=model,
        cost_aud=llm_result.cost_aud,
    )

    budget_result = tracker.alert_if_over_budget(llm_result.cost_aud)
    try:
        over_budget, budget_msg = budget_result
    except (TypeError, ValueError):
        over_budget, budget_msg = False, ""
    if budget_msg:
        print(f"  {budget_msg}")

    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Feynman study notes from lecture transcripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_notes.py --course MIS271 --week 1 --session lecture
  python generate_notes.py --course MIS271 --week 1 --estimate-only
  python generate_notes.py --course MIS271 --weeks 1-5 --session lecture
  python generate_notes.py --course MIS999 --week 3 --model claude-3-haiku-20240307
        """,
    )
    parser.add_argument("--course", required=True, help="Course code (e.g., MIS271)")
    parser.add_argument(
        "--week",
        type=int,
        help="Week number (1-11). Use --weeks for a range.",
    )
    parser.add_argument(
        "--weeks",
        help="Week range (e.g., 1-11). Overrides --week.",
    )
    parser.add_argument(
        "--session",
        default="lecture",
        choices=["lecture", "prac"],
        help="Session type (default: lecture)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"LLM model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--estimate-only",
        action="store_true",
        help="Show cost estimate without calling the API",
    )
    parser.add_argument(
        "--urls",
        nargs="*",
        default=[],
        metavar="URL",
        help="External URLs to fetch and include as reading context (space-separated)",
    )

    args = parser.parse_args()

    # Resolve model
    model = args.model or os.getenv("LLM_MODEL", DEFAULT_MODEL)

    # Resolve week(s)
    if args.weeks:
        weeks = _parse_week_range(args.weeks)
    elif args.week:
        weeks = [args.week]
    else:
        parser.error("Specify --week N or --weeks N-M")

    # Validate course code
    if not CourseManager.is_valid_course_code(args.course):
        print(
            f"[ERR] Invalid course code '{args.course}'. "
            "Expected format: 3 letters + 3 digits (e.g., MIS271)"
        )
        return 1

    # Load API key (skip if estimate-only)
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key and not args.estimate_only:
        print(
            "[ERR] OPENROUTER_API_KEY not set. "
            "Add it to your .env file or set the environment variable."
        )
        return 1

    # Resolve Obsidian vault
    vault_str = os.getenv("OBSIDIAN_VAULT_PATH", DEFAULT_OBSIDIAN_VAULT)
    vault_path = Path(vault_str)
    if not args.estimate_only and not vault_path.exists():
        print(
            f"[ERR] Obsidian vault not found: {vault_path}\n"
            "  Set OBSIDIAN_VAULT_PATH in .env or check that the vault folder exists."
        )
        return 1

    # Run
    successes = 0
    failures = 0
    for week in weeks:
        ok = process_lecture(
            course_code=args.course,
            week=week,
            session=args.session,
            model=model,
            api_key=api_key,
            vault_path=vault_path,
            estimate_only=args.estimate_only,
            urls=args.urls,
        )
        if ok:
            successes += 1
        else:
            failures += 1

    # Summary
    total = successes + failures
    print(f"\n{'='*40}")
    if args.estimate_only:
        print(f"Estimate complete: {total} lecture(s) checked")
    else:
        print(f"Done: {successes}/{total} succeeded")
        if failures:
            print("  Run again for failed lectures after fixing the issue above.")

        # Show weekly cost summary if any lectures processed
        if successes > 0:
            tracker = CostTracker()
            print("\n" + tracker.format_weekly_summary())

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
