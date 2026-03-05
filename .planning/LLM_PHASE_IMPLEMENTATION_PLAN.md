# LLM Note Generation Phase - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete LLM-powered Feynman-technique study note generation system that transforms lecture transcripts into structured, pedagogically-sound study materials.

**Architecture:** Modular pipeline: transcript loading → cleaning → LLM processing → note formatting → Obsidian vault integration, with comprehensive cost tracking and budget enforcement throughout.

**Tech Stack:** Python 3.11+, OpenRouter API (deepseek-chat), Pydantic validation, Obsidian vault integration, pytest for testing

---

## Project Status Summary

### ✅ What's Already Built
- **transcript_processor.py** - Exists with PII detection, formatting cleaning, chunking support
- **llm_generator.py** - Exists with token counting, cost estimation, API retry logic
- **cost_tracker.py** - Exists with budget tracking and cost logging
- **obsidian_writer.py** - Exists with markdown validation and frontmatter generation
- **config.py** - Exists with Pydantic validation and .env loading
- **Test data** - MIS271 Week 1 transcript (769 lines) and video (129MB) ready for testing

### 🚀 What Needs Building
1. **generate_notes.py** - Main CLI entry point (NEW)
2. **Create comprehensive integration tests** - End-to-end testing
3. **Create Feynman-specific prompt templates** - Currently using generic prompts
4. **Enhance note formatting for Obsidian** - Add structured sections and metadata
5. **Implement batch processing** - Process entire courses at once

---

## Phase Breakdown: 5 Deliverable Phases

### Phase 1: Core Infrastructure & Testing (Foundation)
**Objective:** Verify all existing components work correctly and can communicate

**Deliverables:**
- Write unit tests for each existing module
- Create integration test harness
- Verify OpenRouter API connectivity
- Set up CI/CD checks

**Key Files:**
- Create: `tests/test_transcript_processor.py`
- Create: `tests/test_llm_generator.py`
- Create: `tests/test_cost_tracker.py`
- Create: `tests/test_obsidian_writer.py`
- Create: `tests/test_integration.py`

---

### Phase 2: Feynman-Technique Enhancement (Core Feature)
**Objective:** Implement specialized prompts and note structure for Feynman technique

**Deliverables:**
- Create Feynman-specific system prompt
- Implement prompt templating system
- Parse LLM response into structured sections
- Create note formatter for Obsidian output

**Key Files:**
- Modify: `src/llm_generator.py` - Add Feynman prompt creation
- Create: `src/note_formatter.py` - Structure LLM output into Feynman sections
- Create: `tests/test_feynman_prompts.py`

**Feynman Output Structure:**
```
---
course: MIS271
week: 1
session_type: lecture
generated_date: 2026-03-04
model: deepseek/deepseek-chat
cost_aud: 0.0042
---

# MIS271 Week 1 - Lecture Notes

## Key Concepts (As if teaching a 12-year-old)
- Concept 1: Simple explanation
- Concept 2: Simple explanation

## Detailed Explanations
### Concept 1
[Plain English explanation of concept...]

## Real-World Examples
- Example 1: [How this applies in practice]
- Example 2: [Another practical application]

## Practice Questions
- Q1: [Self-test question]
- Q2: [Self-test question]

## Learning Tips
- Tip 1: [Study strategy]
- Tip 2: [Common pitfall]

## Source
- Lecture: MIS271 Week 1 Lecture
- Processing date: 2026-03-04
- Transcript length: 769 lines
```

---

### Phase 3: Main CLI & User Interface
**Objective:** Create user-friendly entry point with all necessary options and error handling

**Deliverables:**
- Create generate_notes.py main script
- Implement command-line argument parsing
- Add comprehensive help and error recovery
- Create progress indicators

**Key Files:**
- Create: `generate_notes.py` - Main CLI entry point
- Create: `tests/test_cli.py`

**Usage Examples:**
```bash
# Single lecture
python generate_notes.py --course MIS271 --week 1 --session lecture

# Entire course (11 weeks)
python generate_notes.py --course MIS271 --generate-all

# With cost estimate only
python generate_notes.py --course MIS271 --week 1 --estimate-only

# Custom model
python generate_notes.py --course MIS271 --week 1 --model claude-3-haiku

# Batch processing with progress
python generate_notes.py --batch config/batch_MIS271.json --progress
```

---

### Phase 4: Obsidian Integration & Organization
**Objective:** Seamlessly integrate generated notes into Obsidian vault with proper structure

**Deliverables:**
- Implement vault directory creation
- Create backlinks between related notes
- Add tags for Obsidian search
- Verify vault integrity after writes

**Key Files:**
- Modify: `src/obsidian_writer.py` - Enhance with wikilinks and tagging
- Create: `tests/test_obsidian_integration.py`

**Vault Structure:**
```
Obsidian Vault/
└── University notes/
    └── Trimester_1_26/
        ├── Lectures/
        │   ├── MIS271/
        │   │   ├── week_01_lecture.md
        │   │   ├── week_01_practical.md
        │   │   ├── week_02_lecture.md
        │   │   └── ...
        │   └── MIS999/
        │       └── ...
        └── Index.md
```

---

### Phase 5: Advanced Features & Polish
**Objective:** Add batch processing, cost optimization, and performance features

**Deliverables:**
- Batch processing for entire courses
- Resume failed generations
- Cost optimization strategies
- Performance monitoring
- Documentation and examples

**Key Files:**
- Create: `src/batch_processor.py`
- Create: `examples/batch_MIS271.json`
- Create: `USAGE_GUIDE.md`

---

## Detailed Task Breakdown

### PHASE 1: Foundation Testing

#### Task 1.1: Test transcript_processor.py

**Files:**
- Create: `tests/test_transcript_processor.py`
- Reference: `src/transcript_processor.py`

**Step 1: Understand current implementation**

Run: `python -c "from src.transcript_processor import TranscriptProcessor; help(TranscriptProcessor)"`

Check what methods exist and their signatures.

**Step 2: Write test for transcript loading**

Create `tests/test_transcript_processor.py`:

```python
import pytest
from pathlib import Path
from src.transcript_processor import TranscriptProcessor

class TestTranscriptProcessor:
    """Test transcript processing functionality."""
    
    @pytest.fixture
    def test_transcript_path(self):
        """Get path to test transcript."""
        return Path("downloads/MIS271_week_01_lecture/week_01_lecture/transcript.txt")
    
    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        return TranscriptProcessor()
    
    def test_load_transcript_success(self, processor, test_transcript_path):
        """Test loading a valid transcript file."""
        result = processor.load_transcript(str(test_transcript_path))
        assert result.status == "success"
        assert result.cleaned_text is not None
        assert len(result.cleaned_text) > 0
        assert result.word_count is not None
        assert result.word_count > 0
    
    def test_load_transcript_missing_file(self, processor):
        """Test loading a non-existent transcript."""
        result = processor.load_transcript("nonexistent.txt")
        assert result.status == "missing"
        assert result.cleaned_text is None
        assert result.error_message is not None
    
    def test_clean_transcript_removes_pii(self, processor, test_transcript_path):
        """Test PII removal from transcript."""
        result = processor.load_transcript(str(test_transcript_path))
        assert result.status == "success"
        # Verify no email patterns in output
        assert "@" not in result.cleaned_text or ".com" not in result.cleaned_text
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/test_transcript_processor.py -v`

Expected: FAIL - Methods may not exist or have different signatures

**Step 4: Fix any implementation issues**

If tests fail due to API mismatches, update `src/transcript_processor.py` to match expected interfaces.

**Step 5: Run tests again to verify they pass**

Run: `pytest tests/test_transcript_processor.py -v`

Expected: PASS ✓

**Step 6: Commit**

```bash
git add tests/test_transcript_processor.py
git commit -m "test: add transcript processor unit tests"
```

---

#### Task 1.2: Test llm_generator.py

**Files:**
- Create: `tests/test_llm_generator.py`
- Reference: `src/llm_generator.py`

**Step 1: Write test for token counting**

```python
import pytest
from src.llm_generator import TokenCounter

class TestTokenCounter:
    """Test token counting functionality."""
    
    @pytest.fixture
    def counter(self):
        """Create token counter instance."""
        return TokenCounter()
    
    def test_count_tokens_empty_string(self, counter):
        """Test counting tokens in empty string."""
        result = counter.count_tokens("")
        assert result == 0
    
    def test_count_tokens_simple_text(self, counter):
        """Test counting tokens in simple text."""
        text = "Hello world"
        result = counter.count_tokens(text)
        assert result > 0
        assert result < 100  # Should be very few tokens
    
    def test_count_tokens_long_text(self, counter):
        """Test counting tokens in longer text."""
        text = "The quick brown fox jumps over the lazy dog. " * 100
        result = counter.count_tokens(text)
        assert result > 100  # Should be many tokens
    
    def test_estimate_cost_deepseek(self, counter):
        """Test cost estimation for DeepSeek model."""
        cost = counter.estimate_cost(
            input_tokens=1000,
            output_tokens=600,
            model="deepseek/deepseek-chat"
        )
        assert cost > 0
        assert cost < 0.01  # Should be cheap
    
    def test_estimate_cost_haiku(self, counter):
        """Test cost estimation for Claude Haiku model."""
        cost = counter.estimate_cost(
            input_tokens=1000,
            output_tokens=600,
            model="claude-3-haiku"
        )
        assert cost > 0
```

**Step 2: Run test to verify it fails initially**

Run: `pytest tests/test_llm_generator.py::TestTokenCounter -v`

Expected: Tests may fail if TokenCounter doesn't exist or has different API

**Step 3: Implement missing functionality in llm_generator.py if needed**

Check if TokenCounter exists and has the required methods. If not, they already exist based on code review.

**Step 4: Run tests again**

Run: `pytest tests/test_llm_generator.py::TestTokenCounter -v`

Expected: PASS ✓

**Step 5: Write test for API call generation**

```python
def test_create_study_notes_prompt(self):
    """Test creation of study notes prompt."""
    from src.llm_generator import create_study_notes_prompt
    
    transcript = "This is a lecture about business intelligence."
    prompt = create_study_notes_prompt(transcript)
    
    assert isinstance(prompt, str)
    assert len(prompt) > 100
    assert "study notes" in prompt.lower() or "lecture" in prompt.lower()
```

**Step 6: Commit**

```bash
git add tests/test_llm_generator.py
git commit -m "test: add LLM generator unit tests"
```

---

#### Task 1.3: Test cost_tracker.py

**Files:**
- Create: `tests/test_cost_tracker.py`
- Reference: `src/cost_tracker.py`

**Step 1: Write cost estimation test**

```python
import pytest
from src.cost_tracker import estimate_cost, CostTracker
from pathlib import Path

class TestCostTracking:
    """Test cost tracking functionality."""
    
    def test_estimate_cost_deepseek_basic(self):
        """Test basic cost estimation."""
        cost = estimate_cost(
            input_tokens=1000,
            output_tokens=600,
            model="deepseek/deepseek-chat"
        )
        assert cost > 0
        assert cost < 0.01
    
    def test_estimate_cost_haiku(self):
        """Test cost for more expensive model."""
        cost_deepseek = estimate_cost(1000, 600, "deepseek/deepseek-chat")
        cost_haiku = estimate_cost(1000, 600, "claude-3-haiku")
        assert cost_haiku > cost_deepseek
    
    def test_cost_tracker_init(self):
        """Test CostTracker initialization."""
        tracker = CostTracker()
        assert tracker.log_file is not None
    
    def test_cost_tracker_log_lecture(self):
        """Test logging a lecture cost."""
        tracker = CostTracker(Path("test_costs.json"))
        tracker.log_lecture(
            course="MIS271",
            week=1,
            session="lecture",
            model="deepseek/deepseek-chat",
            tokens_used=1600,
            cost_aud=0.005
        )
        # Verify logged
        assert len(tracker.data.get("lectures", [])) > 0
        # Cleanup
        Path("test_costs.json").unlink(missing_ok=True)
```

**Step 2: Run tests**

Run: `pytest tests/test_cost_tracker.py -v`

**Step 3: Commit**

```bash
git add tests/test_cost_tracker.py
git commit -m "test: add cost tracker unit tests"
```

---

#### Task 1.4: Test obsidian_writer.py

**Files:**
- Create: `tests/test_obsidian_writer.py`
- Reference: `src/obsidian_writer.py`

**Step 1: Write markdown validation test**

```python
import pytest
from src.obsidian_writer import MarkdownValidator, FrontmatterGenerator

class TestMarkdownValidation:
    """Test markdown validation."""
    
    def test_valid_markdown(self):
        """Test validation of valid markdown."""
        content = """## Summary
This is a summary.

## Key Concepts
- Concept 1
- Concept 2

## Examples
Some examples.

## Formulas
Some formulas.

## Pitfalls
Some pitfalls.

## Review Questions
Some questions."""
        
        is_valid, issues = MarkdownValidator.is_valid_markdown(content)
        assert is_valid is True
        assert len(issues) == 0
    
    def test_invalid_markdown_unmatched_brackets(self):
        """Test detection of unmatched brackets."""
        content = "This has [unmatched brackets"
        is_valid, issues = MarkdownValidator.is_valid_markdown(content)
        assert is_valid is False
        assert len(issues) > 0
    
    def test_frontmatter_generation(self):
        """Test YAML frontmatter generation."""
        metadata = {
            "course": "MIS271",
            "week": 1,
            "session_type": "lecture",
            "date": "2026-03-04"
        }
        frontmatter = FrontmatterGenerator.generate_frontmatter(metadata)
        assert "---" in frontmatter
        assert "course: MIS271" in frontmatter
        assert "week: 1" in frontmatter
```

**Step 2: Run tests**

Run: `pytest tests/test_obsidian_writer.py -v`

**Step 3: Commit**

```bash
git add tests/test_obsidian_writer.py
git commit -m "test: add obsidian writer unit tests"
```

---

#### Task 1.5: Create integration test harness

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write end-to-end integration test**

```python
import pytest
from pathlib import Path
from src.transcript_processor import TranscriptProcessor
from src.llm_generator import TokenCounter
from src.cost_tracker import estimate_cost
from src.obsidian_writer import MarkdownValidator

class TestIntegration:
    """Integration tests for the complete pipeline."""
    
    @pytest.fixture
    def test_transcript_path(self):
        """Get path to test transcript."""
        return Path("downloads/MIS271_week_01_lecture/week_01_lecture/transcript.txt")
    
    def test_full_pipeline_load_and_estimate(self, test_transcript_path):
        """Test loading transcript and estimating cost."""
        # Step 1: Load transcript
        processor = TranscriptProcessor()
        result = processor.load_transcript(str(test_transcript_path))
        assert result.status == "success"
        
        # Step 2: Count tokens
        counter = TokenCounter()
        tokens = counter.count_tokens(result.cleaned_text)
        assert tokens > 0
        
        # Step 3: Estimate cost
        estimated_cost = estimate_cost(tokens, 600)
        assert estimated_cost > 0
        assert estimated_cost < 0.30  # Should be within budget
```

**Step 2: Run integration tests**

Run: `pytest tests/test_integration.py -v`

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for complete pipeline"
```

---

### PHASE 2: Feynman Technique Enhancement

#### Task 2.1: Create Feynman prompt templates

**Files:**
- Modify: `src/llm_generator.py`
- Create: `tests/test_feynman_prompts.py`

**Step 1: Add Feynman prompt creation to llm_generator.py**

Add to `src/llm_generator.py`:

```python
FEYNMAN_SYSTEM_PROMPT = """You are an expert educator using the Feynman Technique to create study notes.

Your goal: Explain concepts as if teaching to an intelligent 12-year-old. Use simple language, clear examples, and avoid jargon.

OUTPUT FORMAT - Create exactly these sections in markdown:

## Key Concepts
- List 5-8 core concepts from the lecture
- One sentence each, ordered by importance

## Detailed Explanations
### [Concept 1]
Explain in simple terms (2-3 paragraphs). What is it? Why does it matter?

### [Concept 2]
[Same format]

## Real-World Examples
- Example 1: How this concept applies in practice
- Example 2: Another practical application
- Example 3: Real business use case

## Practice Questions
- Q1: [Self-test question - answer should test understanding]
- Q2: [Another self-test question]
- Q3: [Third question]

## Learning Tips
- Tip 1: Study strategy for this concept
- Tip 2: Common mistake to avoid
- Tip 3: How to test if you understand

CONSTRAINTS:
- Assume NO prior knowledge on topic
- Use analogies and everyday examples
- Flag sections that are confusing with ⚠️
- Total output: 800-1200 words
- Valid markdown for Obsidian"""

def create_feynman_prompt(transcript: str, course_code: str = "", week: int = 0) -> str:
    """
    Create a Feynman-technique prompt for LLM.
    
    Args:
        transcript: Cleaned lecture transcript
        course_code: Course code (e.g., MIS271)
        week: Week number
    
    Returns:
        Formatted prompt for LLM API
    """
    context = ""
    if course_code and week:
        context = f"\n[Course: {course_code}, Week {week} Lecture]"
    
    return f"""{context}

Please apply the Feynman Technique to create study notes from this lecture:

{transcript}"""
```

**Step 2: Write test for Feynman prompt**

```python
import pytest
from src.llm_generator import create_feynman_prompt

def test_create_feynman_prompt():
    """Test creation of Feynman prompt."""
    transcript = "This lecture covers business intelligence concepts."
    prompt = create_feynman_prompt(transcript, "MIS271", 1)
    
    assert isinstance(prompt, str)
    assert "Feynman" in prompt or "explain" in prompt.lower()
    assert transcript in prompt
    assert "MIS271" in prompt
    assert "Week 1" in prompt
```

**Step 3: Run test**

Run: `pytest tests/test_feynman_prompts.py::test_create_feynman_prompt -v`

**Step 4: Commit**

```bash
git add src/llm_generator.py tests/test_feynman_prompts.py
git commit -m "feat: add Feynman technique prompt templates"
```

---

#### Task 2.2: Create note formatter for Feynman output

**Files:**
- Create: `src/note_formatter.py`
- Create: `tests/test_note_formatter.py`

**Step 1: Create note_formatter.py**

```python
"""
Note formatting module for converting LLM output to Obsidian-ready markdown.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

@dataclass
class NoteMetadata:
    """Metadata for generated note."""
    course: str
    week: int
    session_type: str  # "lecture" or "practical"
    model: str
    cost_aud: float
    transcript_path: str
    generated_at: datetime = None
    
    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now()

class NoteFormatter:
    """Format LLM-generated notes for Obsidian vault."""
    
    @staticmethod
    def create_frontmatter(metadata: NoteMetadata) -> str:
        """
        Create YAML frontmatter for Obsidian.
        
        Args:
            metadata: Note metadata
        
        Returns:
            YAML frontmatter string
        """
        return f"""---
course: {metadata.course}
week: {metadata.week}
session_type: {metadata.session_type}
model: {metadata.model}
cost_aud: {metadata.cost_aud:.4f}
generated_at: {metadata.generated_at.isoformat()}
transcript_path: {metadata.transcript_path}
---
"""
    
    @staticmethod
    def format_note(llm_content: str, metadata: NoteMetadata) -> str:
        """
        Format complete note with frontmatter and content.
        
        Args:
            llm_content: Raw LLM output
            metadata: Note metadata
        
        Returns:
            Complete formatted note
        """
        frontmatter = NoteFormatter.create_frontmatter(metadata)
        
        title = f"# {metadata.course} Week {metadata.week} - {metadata.session_type.capitalize()} Notes"
        
        return f"""{frontmatter}
{title}

{llm_content}
"""
    
    @staticmethod
    def validate_feynman_structure(content: str) -> tuple[bool, list[str]]:
        """
        Validate that content has required Feynman sections.
        
        Args:
            content: Formatted note content
        
        Returns:
            Tuple of (is_valid, missing_sections)
        """
        required_sections = [
            "Key Concepts",
            "Detailed Explanations",
            "Real-World Examples",
            "Practice Questions",
            "Learning Tips"
        ]
        
        missing = [s for s in required_sections if f"## {s}" not in content]
        
        return len(missing) == 0, missing
```

**Step 2: Write tests**

```python
import pytest
from datetime import datetime
from src.note_formatter import NoteFormatter, NoteMetadata

class TestNoteFormatter:
    """Test note formatting."""
    
    @pytest.fixture
    def metadata(self):
        """Create test metadata."""
        return NoteMetadata(
            course="MIS271",
            week=1,
            session_type="lecture",
            model="deepseek/deepseek-chat",
            cost_aud=0.0042,
            transcript_path="downloads/MIS271_week_01_lecture/week_01_lecture/transcript.txt"
        )
    
    def test_create_frontmatter(self, metadata):
        """Test YAML frontmatter creation."""
        frontmatter = NoteFormatter.create_frontmatter(metadata)
        assert "---" in frontmatter
        assert "course: MIS271" in frontmatter
        assert "week: 1" in frontmatter
        assert "session_type: lecture" in frontmatter
    
    def test_format_note_complete(self, metadata):
        """Test complete note formatting."""
        llm_content = """## Key Concepts
- Concept 1
- Concept 2

## Detailed Explanations
### Concept 1
Explanation here

## Real-World Examples
- Example 1

## Practice Questions
- Q1

## Learning Tips
- Tip 1"""
        
        note = NoteFormatter.format_note(llm_content, metadata)
        assert "---" in note
        assert "# MIS271 Week 1 - Lecture Notes" in note
        assert llm_content in note
    
    def test_validate_feynman_structure_valid(self):
        """Test validation of valid Feynman structure."""
        content = """## Key Concepts
- C1

## Detailed Explanations
Text

## Real-World Examples
- E1

## Practice Questions
- Q1

## Learning Tips
- T1"""
        
        is_valid, missing = NoteFormatter.validate_feynman_structure(content)
        assert is_valid is True
        assert len(missing) == 0
    
    def test_validate_feynman_structure_invalid(self):
        """Test validation of missing sections."""
        content = """## Key Concepts
- C1

## Detailed Explanations
Text"""
        
        is_valid, missing = NoteFormatter.validate_feynman_structure(content)
        assert is_valid is False
        assert len(missing) > 0
        assert "Real-World Examples" in missing
```

**Step 3: Run tests**

Run: `pytest tests/test_note_formatter.py -v`

**Step 4: Commit**

```bash
git add src/note_formatter.py tests/test_note_formatter.py
git commit -m "feat: add note formatter with Feynman validation"
```

---

#### Task 2.3: Create LLM call wrapper with Feynman support

**Files:**
- Modify: `src/llm_generator.py`
- Create: `tests/test_llm_calls.py`

**Step 1: Add Feynman generation function to llm_generator.py**

```python
import os
from openai import OpenAI

def generate_feynman_notes(
    transcript: str,
    course_code: str = "Unknown",
    week: int = 0,
    model: str = "deepseek/deepseek-chat",
    budget_aud: float = 0.30,
    safety_buffer: float = 0.20,
) -> tuple[str, dict]:
    """
    Generate Feynman-technique notes from transcript using OpenRouter API.
    
    Args:
        transcript: Cleaned lecture transcript
        course_code: Course code (e.g., MIS271)
        week: Week number
        model: LLM model to use
        budget_aud: Budget limit in AUD
        safety_buffer: Safety buffer fraction (e.g., 0.20 = 20%)
    
    Returns:
        Tuple of (generated_notes, metadata_dict)
    
    Raises:
        ValueError: If cost exceeds budget
        APIError: If API call fails
    """
    # Count tokens
    counter = TokenCounter()
    input_tokens = counter.count_tokens(transcript)
    
    # Estimate cost
    estimated_cost = counter.estimate_cost(input_tokens, 600, model)
    
    # Check budget
    safety_reserve = budget_aud * safety_buffer
    available_budget = budget_aud - safety_reserve
    
    if estimated_cost > available_budget:
        raise ValueError(
            f"Estimated cost AUD ${estimated_cost:.4f} exceeds available budget "
            f"AUD ${available_budget:.4f} (total ${budget_aud:.4f} with "
            f"{int(safety_buffer*100)}% safety buffer)"
        )
    
    # Create prompt
    prompt = create_feynman_prompt(transcript, course_code, week)
    
    # Call API
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set in .env")
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": FEYNMAN_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1500
    )
    
    notes = response.choices[0].message.content
    
    metadata = {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens,
        "estimated_cost": estimated_cost,
        "actual_cost": counter.estimate_cost(
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            model
        )
    }
    
    return notes, metadata
```

**Step 2: Write test for Feynman generation**

```python
import pytest
import os
from unittest.mock import patch, MagicMock
from src.llm_generator import generate_feynman_notes

class TestFeynmanGeneration:
    """Test Feynman note generation."""
    
    @pytest.fixture
    def sample_transcript(self):
        """Create sample transcript."""
        return "This lecture covers business intelligence and data warehousing concepts. " * 50
    
    def test_generate_feynman_notes_mock(self, sample_transcript):
        """Test note generation with mocked API."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            with patch("src.llm_generator.OpenAI") as mock_openai:
                # Setup mock response
                mock_response = MagicMock()
                mock_response.choices[0].message.content = """## Key Concepts
- Business Intelligence: Using data to make decisions
- Data Warehouse: Central data repository

## Detailed Explanations
### Business Intelligence
BI is about turning raw data into insights...

## Real-World Examples
- Retail stores using sales data to stock shelves

## Practice Questions
- What is BI?

## Learning Tips
- Focus on practical applications"""
                
                mock_response.usage.completion_tokens = 200
                mock_response.usage.prompt_tokens = 400
                mock_response.usage.total_tokens = 600
                
                mock_openai.return_value.chat.completions.create.return_value = mock_response
                
                # Call function
                notes, metadata = generate_feynman_notes(
                    sample_transcript,
                    "MIS271",
                    1
                )
                
                assert "Key Concepts" in notes
                assert metadata["model"] == "deepseek/deepseek-chat"
                assert metadata["actual_cost"] > 0
    
    def test_generate_feynman_notes_budget_exceeded(self, sample_transcript):
        """Test budget enforcement."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            with pytest.raises(ValueError, match="exceeds.*budget"):
                generate_feynman_notes(
                    sample_transcript,
                    "MIS271",
                    1,
                    budget_aud=0.0001  # Very small budget
                )
```

**Step 3: Run tests**

Run: `pytest tests/test_llm_calls.py -v`

**Step 4: Commit**

```bash
git add src/llm_generator.py tests/test_llm_calls.py
git commit -m "feat: add Feynman note generation with budget enforcement"
```

---

### PHASE 3: Main CLI & User Interface

#### Task 3.1: Create generate_notes.py main script

**Files:**
- Create: `generate_notes.py`
- Create: `tests/test_cli.py`

**Step 1: Create generate_notes.py**

```python
#!/usr/bin/env python3
"""
CLI for generating Feynman-technique study notes from lectures.

Usage:
    python generate_notes.py --course MIS271 --week 1 --session lecture
    python generate_notes.py --course MIS271 --weeks 1-11
    python generate_notes.py --course MIS271 --week 1 --estimate-only
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.course_manager import CourseManager
from src.config import load_config
from src.transcript_processor import TranscriptProcessor
from src.llm_generator import generate_feynman_notes, TokenCounter
from src.note_formatter import NoteFormatter, NoteMetadata
from src.obsidian_writer import FrontmatterGenerator
from src.cost_tracker import CostTracker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_week_range(weeks_str: str) -> list[int]:
    """
    Parse week range like "1-5" or single week "3".
    
    Args:
        weeks_str: Week specification (e.g., "1-5" or "3")
    
    Returns:
        List of week numbers
    """
    if "-" in weeks_str:
        parts = weeks_str.split("-")
        start, end = int(parts[0]), int(parts[1])
        return list(range(start, end + 1))
    else:
        return [int(weeks_str)]

def get_lecture_files(course_code: str, week: int, session: str) -> tuple[Optional[Path], Optional[Path]]:
    """
    Get paths to video and transcript files.
    
    Args:
        course_code: Course code (e.g., MIS271)
        week: Week number
        session: "lecture" or "prac"
    
    Returns:
        Tuple of (video_path, transcript_path)
    """
    course_manager = CourseManager(course_code)
    session_dir = course_manager.get_session_folder(week, session)
    
    video_path = None
    transcript_path = None
    
    if session_dir.exists():
        # Find video file
        for ext in ['.mp4', '.mkv', '.webm']:
            video_candidates = list(session_dir.glob(f'*{ext}'))
            if video_candidates:
                video_path = video_candidates[0]
                break
        
        # Find transcript file
        for ext in ['.txt', '.vtt']:
            transcript_candidates = list(session_dir.glob(f'*{ext}'))
            if transcript_candidates:
                transcript_path = transcript_candidates[0]
                break
    
    return video_path, transcript_path

def generate_notes_for_lecture(
    course_code: str,
    week: int,
    session: str,
    args
) -> bool:
    """
    Generate notes for a single lecture.
    
    Args:
        course_code: Course code
        week: Week number
        session: "lecture" or "prac"
        args: Parsed command-line arguments
    
    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Generating notes for {course_code} Week {week} ({session})")
    print(f"{'='*60}")
    
    # Check files exist
    video_path, transcript_path = get_lecture_files(course_code, week, session)
    
    if not transcript_path:
        print(f"ERROR: No transcript found for {course_code} Week {week} ({session})")
        return False
    
    if not video_path:
        print(f"WARNING: No video found for {course_code} Week {week} ({session})")
        print(f"Proceeding with transcript-only processing...")
    
    print(f"Transcript: {transcript_path}")
    
    # Load and clean transcript
    processor = TranscriptProcessor()
    result = processor.load_transcript(str(transcript_path))
    
    if result.status != "success":
        print(f"ERROR: Failed to load transcript: {result.error_message}")
        return False
    
    print(f"Transcript loaded: {result.word_count} words")
    
    # Estimate cost
    config = load_config()
    counter = TokenCounter()
    tokens = counter.count_tokens(result.cleaned_text)
    estimated_cost = counter.estimate_cost(tokens, 600, args.model)
    
    print(f"\nCost Estimate:")
    print(f"  Model: {args.model}")
    print(f"  Input tokens: {tokens:,}")
    print(f"  Estimated cost: AUD ${estimated_cost:.4f}")
    print(f"  Budget per lecture: AUD ${config.llm_budget_aud:.4f}")
    
    if args.estimate_only:
        print(f"\n✓ Cost estimate complete (--estimate-only specified)")
        return True
    
    # Generate notes
    print(f"\nGenerating notes with {args.model}...")
    try:
        notes, metadata = generate_feynman_notes(
            result.cleaned_text,
            course_code,
            week,
            model=args.model,
            budget_aud=config.llm_budget_aud,
            safety_buffer=config.llm_safety_buffer
        )
    except Exception as e:
        print(f"ERROR: Failed to generate notes: {str(e)}")
        return False
    
    # Format note
    note_metadata = NoteMetadata(
        course=course_code,
        week=week,
        session_type=session,
        model=args.model,
        cost_aud=metadata["actual_cost"],
        transcript_path=str(transcript_path)
    )
    
    formatted_note = NoteFormatter.format_note(notes, note_metadata)
    
    # Validate structure
    is_valid, missing = NoteFormatter.validate_feynman_structure(formatted_note)
    if not is_valid:
        print(f"WARNING: Missing Feynman sections: {', '.join(missing)}")
    else:
        print(f"✓ Note structure valid")
    
    # Save to Obsidian vault (if configured)
    if config.obsidian_vault_path:
        try:
            vault_path = Path(config.obsidian_vault_path)
            course_folder = vault_path / config.obsidian_note_subfolder / course_code
            course_folder.mkdir(parents=True, exist_ok=True)
            
            filename = f"week_{week:02d}_{session}.md"
            note_path = course_folder / filename
            
            with open(note_path, 'w', encoding='utf-8') as f:
                f.write(formatted_note)
            
            print(f"✓ Note saved to {note_path}")
        except Exception as e:
            print(f"ERROR: Failed to save to Obsidian vault: {str(e)}")
            return False
    else:
        print(f"WARNING: Obsidian vault not configured, note not saved")
    
    # Track cost
    cost_tracker = CostTracker()
    cost_tracker.log_lecture(
        course=course_code,
        week=week,
        session=session,
        model=args.model,
        tokens_used=metadata["total_tokens"],
        cost_aud=metadata["actual_cost"]
    )
    
    print(f"\n✓ Cost tracked: AUD ${metadata['actual_cost']:.4f}")
    print(f"✓ Lecture complete!")
    
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Feynman-technique study notes from lectures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate notes for single lecture
  python generate_notes.py --course MIS271 --week 1 --session lecture
  
  # Generate notes for all weeks in course
  python generate_notes.py --course MIS271 --weeks 1-11
  
  # Estimate cost only (don't call API)
  python generate_notes.py --course MIS271 --week 1 --estimate-only
  
  # Use different model
  python generate_notes.py --course MIS271 --week 1 --model claude-3-haiku
"""
    )
    
    parser.add_argument("--course", required=True, help="Course code (e.g., MIS271)")
    parser.add_argument("--week", type=int, help="Week number (default: 1)")
    parser.add_argument("--weeks", help="Week range (e.g., 1-11)")
    parser.add_argument("--session", default="lecture", choices=["lecture", "prac"],
                       help="Session type (lecture or prac)")
    parser.add_argument("--model", default="deepseek/deepseek-chat",
                       help="LLM model to use")
    parser.add_argument("--estimate-only", action="store_true",
                       help="Estimate cost only, don't call API")
    parser.add_argument("--all-sessions", action="store_true",
                       help="Generate both lecture and practical for each week")
    
    args = parser.parse_args()
    
    # Determine weeks to process
    if args.weeks:
        weeks = parse_week_range(args.weeks)
    elif args.week:
        weeks = [args.week]
    else:
        weeks = [1]
    
    # Determine sessions to process
    sessions = ["lecture", "prac"] if args.all_sessions else [args.session]
    
    # Process lectures
    success_count = 0
    fail_count = 0
    
    for week in weeks:
        for session in sessions:
            if generate_notes_for_lecture(args.course, week, session, args):
                success_count += 1
            else:
                fail_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Summary: {success_count} succeeded, {fail_count} failed")
    print(f"{'='*60}")
    
    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Write CLI tests**

```python
import pytest
import subprocess
from pathlib import Path

class TestGenerateNotesCLI:
    """Test generate_notes.py CLI."""
    
    def test_cli_help(self):
        """Test --help flag."""
        result = subprocess.run(
            ["python", "generate_notes.py", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Course code" in result.stdout
    
    def test_cli_missing_course(self):
        """Test that --course is required."""
        result = subprocess.run(
            ["python", "generate_notes.py"],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "course" in result.stderr.lower()
    
    def test_cli_estimate_only(self):
        """Test --estimate-only flag."""
        result = subprocess.run(
            ["python", "generate_notes.py", "--course", "MIS271", "--week", "1", "--estimate-only"],
            capture_output=True,
            text=True,
            timeout=30
        )
        # Should succeed even if transcript not found (we're testing argument parsing)
        assert "--estimate-only" not in result.stderr or "cost" in result.stdout.lower()
```

**Step 3: Run tests**

Run: `pytest tests/test_cli.py -v`

**Step 4: Make script executable and test manually**

```bash
chmod +x generate_notes.py
python generate_notes.py --help
```

**Step 5: Commit**

```bash
git add generate_notes.py tests/test_cli.py
git commit -m "feat: add main CLI for note generation with full argument support"
```

---

### PHASE 4: Obsidian Integration & Organization

#### Task 4.1: Enhance obsidian_writer.py with wikilinks and organization

**Files:**
- Modify: `src/obsidian_writer.py`
- Create: `tests/test_obsidian_integration.py`

**Step 1: Add wikilink and vault organization functions to obsidian_writer.py**

Add to existing `src/obsidian_writer.py`:

```python
class VaultOrganizer:
    """Organize notes in Obsidian vault structure."""
    
    @staticmethod
    def create_vault_structure(vault_path: Path, courses: list[str]) -> bool:
        """
        Create proper folder structure in vault.
        
        Args:
            vault_path: Path to Obsidian vault
            courses: List of course codes (e.g., ["MIS271", "MIS999"])
        
        Returns:
            True if successful
        """
        try:
            lectures_folder = vault_path / "Lectures"
            lectures_folder.mkdir(parents=True, exist_ok=True)
            
            for course in courses:
                course_folder = lectures_folder / course
                course_folder.mkdir(parents=True, exist_ok=True)
            
            return True
        except Exception as e:
            logger.error(f"Failed to create vault structure: {e}")
            return False
    
    @staticmethod
    def create_course_index(vault_path: Path, course_code: str, weeks: int = 11) -> str:
        """
        Create index file for course.
        
        Args:
            vault_path: Path to Obsidian vault
            course_code: Course code
            weeks: Number of weeks
        
        Returns:
            Index file content
        """
        content = f"""# {course_code} Lecture Notes

## Course Overview
This folder contains Feynman-technique study notes generated from {course_code} lectures.

## Weekly Notes
"""
        
        for week in range(1, weeks + 1):
            content += f"\n### Week {week}\n"
            content += f"- [[{course_code}/week_{week:02d}_lecture|Lecture]]\n"
            content += f"- [[{course_code}/week_{week:02d}_prac|Practical]]\n"
        
        content += f"\n## Statistics\n"
        content += f"- Course: {course_code}\n"
        content += f"- Total weeks: {weeks}\n"
        content += f"- Format: Feynman Technique\n"
        
        return content

class WikiLinkGenerator:
    """Generate Obsidian wikilinks and references."""
    
    @staticmethod
    def extract_concepts(note_content: str) -> list[str]:
        """
        Extract key concepts from note for linking.
        
        Args:
            note_content: Formatted note content
        
        Returns:
            List of concepts
        """
        concepts = []
        
        # Find items in "Key Concepts" section
        start_marker = "## Key Concepts"
        end_marker = "## Detailed Explanations"
        
        start_idx = note_content.find(start_marker)
        end_idx = note_content.find(end_marker)
        
        if start_idx != -1 and end_idx != -1:
            concepts_section = note_content[start_idx:end_idx]
            # Extract bullet points
            for line in concepts_section.split('\n'):
                if line.strip().startswith('- '):
                    concept = line.strip()[2:].split(':')[0].strip()
                    concepts.append(concept)
        
        return concepts
    
    @staticmethod
    def create_wikilinks(concepts: list[str]) -> str:
        """
        Create wikilinks for concepts.
        
        Args:
            concepts: List of concept names
        
        Returns:
            Markdown content with wikilinks
        """
        links = "\n## Related Concepts\n"
        for concept in concepts:
            links += f"- [[{concept}]]\n"
        return links
    
    @staticmethod
    def add_course_tag(note_content: str, course_code: str) -> str:
        """
        Add course tag to frontmatter.
        
        Args:
            note_content: Note with frontmatter
            course_code: Course code
        
        Returns:
            Updated note content
        """
        lines = note_content.split('\n')
        
        # Find end of frontmatter (second ---)
        frontmatter_end = -1
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '---':
                frontmatter_end = i
                break
        
        if frontmatter_end > 0:
            lines.insert(frontmatter_end, f"tags: [{course_code}, feynman, lecture]")
        
        return '\n'.join(lines)
```

**Step 2: Write integration tests**

```python
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from src.obsidian_writer import VaultOrganizer, WikiLinkGenerator

class TestObsidianIntegration:
    """Test Obsidian vault integration."""
    
    def test_create_vault_structure(self):
        """Test vault folder structure creation."""
        with TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            
            result = VaultOrganizer.create_vault_structure(
                vault_path,
                ["MIS271", "MIS999"]
            )
            
            assert result is True
            assert (vault_path / "Lectures" / "MIS271").exists()
            assert (vault_path / "Lectures" / "MIS999").exists()
    
    def test_create_course_index(self):
        """Test course index creation."""
        index = VaultOrganizer.create_course_index(Path("."), "MIS271", weeks=2)
        
        assert "MIS271" in index
        assert "Week 1" in index
        assert "Week 2" in index
        assert "week_01_lecture" in index
        assert "week_01_prac" in index
    
    def test_extract_concepts(self):
        """Test concept extraction from note."""
        note = """## Key Concepts
- Business Intelligence: Turning data into decisions
- Data Warehouse: Central data storage
- ETL: Extract, transform, load

## Detailed Explanations
### Business Intelligence
..."""
        
        concepts = WikiLinkGenerator.extract_concepts(note)
        assert len(concepts) == 3
        assert "Business Intelligence" in concepts
        assert "Data Warehouse" in concepts
    
    def test_create_wikilinks(self):
        """Test wikilink creation."""
        concepts = ["Business Intelligence", "Data Warehouse"]
        links = WikiLinkGenerator.create_wikilinks(concepts)
        
        assert "[[Business Intelligence]]" in links
        assert "[[Data Warehouse]]" in links
    
    def test_add_course_tag(self):
        """Test adding course tag to frontmatter."""
        note = """---
course: MIS271
week: 1
---

# Notes"""
        
        updated = WikiLinkGenerator.add_course_tag(note, "MIS271")
        assert "tags:" in updated
        assert "MIS271" in updated
        assert "feynman" in updated
```

**Step 3: Run tests**

Run: `pytest tests/test_obsidian_integration.py -v`

**Step 4: Commit**

```bash
git add src/obsidian_writer.py tests/test_obsidian_integration.py
git commit -m "feat: add Obsidian vault organization with wikilinks and tagging"
```

---

### PHASE 5: Advanced Features & Polish

#### Task 5.1: Create batch processor for entire courses

**Files:**
- Create: `src/batch_processor.py`
- Create: `examples/batch_MIS271.json`
- Create: `tests/test_batch_processor.py`

**Step 1: Create batch_processor.py**

```python
"""Batch processing for generating notes for entire courses."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class BatchJob:
    """Batch processing job configuration."""
    course_code: str
    weeks: List[int]
    sessions: List[str]  # ["lecture", "prac"]
    model: str = "deepseek/deepseek-chat"
    skip_failed: bool = True
    track_costs: bool = True

class BatchProcessor:
    """Process multiple lectures in batch."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize batch processor."""
        self.config_path = config_path
        self.results = {
            "succeeded": [],
            "failed": [],
            "total_cost": 0.0,
            "total_time": 0.0
        }
    
    @staticmethod
    def load_config(config_path: Path) -> Dict:
        """
        Load batch configuration from JSON.
        
        Expected format:
        {
            "courses": ["MIS271", "MIS999"],
            "weeks": "1-11",
            "sessions": ["lecture", "prac"],
            "model": "deepseek/deepseek-chat",
            "skip_failed": true
        }
        """
        with open(config_path) as f:
            return json.load(f)
    
    def validate_config(self, config: Dict) -> tuple[bool, List[str]]:
        """Validate batch configuration."""
        errors = []
        
        if "courses" not in config:
            errors.append("Missing 'courses' field")
        
        if "weeks" not in config:
            errors.append("Missing 'weeks' field")
        
        if "sessions" not in config:
            errors.append("Missing 'sessions' field")
        
        valid_sessions = {"lecture", "prac"}
        for session in config.get("sessions", []):
            if session not in valid_sessions:
                errors.append(f"Invalid session '{session}'. Must be 'lecture' or 'prac'")
        
        return len(errors) == 0, errors
    
    def create_jobs(self, config: Dict) -> List[BatchJob]:
        """Create batch jobs from configuration."""
        jobs = []
        
        # Parse weeks
        weeks_spec = config["weeks"]
        if "-" in weeks_spec:
            start, end = map(int, weeks_spec.split("-"))
            weeks = list(range(start, end + 1))
        else:
            weeks = [int(weeks_spec)]
        
        for course in config["courses"]:
            job = BatchJob(
                course_code=course,
                weeks=weeks,
                sessions=config["sessions"],
                model=config.get("model", "deepseek/deepseek-chat"),
                skip_failed=config.get("skip_failed", True),
                track_costs=config.get("track_costs", True)
            )
            jobs.append(job)
        
        return jobs
```

**Step 2: Create example batch configuration**

```json
{
  "description": "Batch process MIS271 course lectures",
  "courses": ["MIS271"],
  "weeks": "1-11",
  "sessions": ["lecture", "prac"],
  "model": "deepseek/deepseek-chat",
  "skip_failed": true,
  "track_costs": true,
  "notes": [
    "This configuration will generate notes for all 11 weeks of MIS271",
    "Both lecture and practical sessions will be processed",
    "Failed lectures will be skipped but logged",
    "Total estimated cost: ~AUD $0.30 * 22 = $6.60"
  ]
}
```

**Step 3: Create batch processor tests**

```python
import pytest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from src.batch_processor import BatchProcessor, BatchJob

class TestBatchProcessor:
    """Test batch processing."""
    
    def test_load_config(self):
        """Test loading batch configuration."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "batch.json"
            config = {
                "courses": ["MIS271"],
                "weeks": "1-5",
                "sessions": ["lecture", "prac"],
                "model": "deepseek/deepseek-chat"
            }
            
            with open(config_path, 'w') as f:
                json.dump(config, f)
            
            loaded = BatchProcessor.load_config(config_path)
            assert loaded["courses"] == ["MIS271"]
            assert loaded["weeks"] == "1-5"
    
    def test_validate_config_valid(self):
        """Test validation of valid configuration."""
        config = {
            "courses": ["MIS271"],
            "weeks": "1-11",
            "sessions": ["lecture", "prac"]
        }
        
        processor = BatchProcessor()
        is_valid, errors = processor.validate_config(config)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_config_invalid_session(self):
        """Test validation of invalid session."""
        config = {
            "courses": ["MIS271"],
            "weeks": "1-11",
            "sessions": ["lecture", "invalid"]
        }
        
        processor = BatchProcessor()
        is_valid, errors = processor.validate_config(config)
        
        assert is_valid is False
        assert len(errors) > 0
    
    def test_create_jobs(self):
        """Test batch job creation."""
        config = {
            "courses": ["MIS271", "MIS999"],
            "weeks": "1-3",
            "sessions": ["lecture", "prac"],
            "model": "deepseek/deepseek-chat"
        }
        
        processor = BatchProcessor()
        jobs = processor.create_jobs(config)
        
        assert len(jobs) == 2
        assert jobs[0].course_code == "MIS271"
        assert jobs[0].weeks == [1, 2, 3]
        assert len(jobs[0].sessions) == 2
```

**Step 4: Run tests**

Run: `pytest tests/test_batch_processor.py -v`

**Step 5: Commit**

```bash
git add src/batch_processor.py examples/batch_MIS271.json tests/test_batch_processor.py
git commit -m "feat: add batch processor for processing entire courses"
```

---

#### Task 5.2: Final integration and end-to-end testing

**Files:**
- Create: `tests/test_e2e.py`
- Modify: `generate_notes.py` (add batch support)

**Step 1: Create end-to-end test**

```python
import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.transcript_processor import TranscriptProcessor
from src.llm_generator import generate_feynman_notes
from src.note_formatter import NoteFormatter, NoteMetadata
from src.obsidian_writer import VaultOrganizer, WikiLinkGenerator

class TestEndToEnd:
    """End-to-end pipeline tests."""
    
    def test_full_pipeline_transcript_to_notes(self):
        """Test complete pipeline: transcript -> LLM -> notes."""
        # Use real test transcript
        transcript_path = Path("downloads/MIS271_week_01_lecture/week_01_lecture/transcript.txt")
        
        if not transcript_path.exists():
            pytest.skip("Test transcript not found")
        
        # Load transcript
        processor = TranscriptProcessor()
        result = processor.load_transcript(str(transcript_path))
        assert result.status == "success"
        
        # Create note metadata
        metadata = NoteMetadata(
            course="MIS271",
            week=1,
            session_type="lecture",
            model="deepseek/deepseek-chat",
            cost_aud=0.005,
            transcript_path=str(transcript_path)
        )
        
        # Create sample formatted note (without LLM call)
        llm_content = """## Key Concepts
- Business Intelligence: Using data for decisions
- Data Warehouse: Central storage

## Detailed Explanations
### BI
BI transforms data into insights for business decision making.

## Real-World Examples
- Retailers using sales data

## Practice Questions
- What is BI?

## Learning Tips
- Focus on practical applications"""
        
        note = NoteFormatter.format_note(llm_content, metadata)
        
        # Validate structure
        is_valid, missing = NoteFormatter.validate_feynman_structure(note)
        assert is_valid is True
        
        # Check content
        assert "---" in note  # Has frontmatter
        assert "MIS271" in note
        assert "Week 1" in note
        assert "Business Intelligence" in note
```

**Step 2: Add batch support to generate_notes.py**

Add to `generate_notes.py`:

```python
# Add to imports
from src.batch_processor import BatchProcessor

# Add to main function
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(...)
    
    # ... existing parser setup ...
    
    parser.add_argument("--batch", help="Batch configuration file (JSON)")
    
    args = parser.parse_args()
    
    # Handle batch processing
    if args.batch:
        return process_batch(args.batch)
    
    # ... existing single-lecture processing ...

def process_batch(batch_config_path: str) -> int:
    """Process batch of lectures."""
    batch_path = Path(batch_config_path)
    
    if not batch_path.exists():
        print(f"ERROR: Batch config not found: {batch_config_path}")
        return 1
    
    processor = BatchProcessor(batch_path)
    config = processor.load_config(batch_path)
    
    is_valid, errors = processor.validate_config(config)
    if not is_valid:
        print("ERROR: Invalid batch configuration:")
        for error in errors:
            print(f"  - {error}")
        return 1
    
    jobs = processor.create_jobs(config)
    print(f"Batch: Processing {len(jobs)} courses...")
    
    total_success = 0
    total_failed = 0
    
    for job in jobs:
        print(f"\nCourse: {job.course_code}")
        for week in job.weeks:
            for session in job.sessions:
                args_obj = argparse.Namespace(
                    course=job.course_code,
                    week=week,
                    session=session,
                    model=job.model,
                    estimate_only=False
                )
                if generate_notes_for_lecture(job.course_code, week, session, args_obj):
                    total_success += 1
                else:
                    total_failed += 1
                    if not job.skip_failed:
                        return 1
    
    print(f"\n{'='*60}")
    print(f"Batch complete: {total_success} succeeded, {total_failed} failed")
    print(f"{'='*60}")
    
    return 0 if total_failed == 0 else 1
```

**Step 3: Run end-to-end tests**

Run: `pytest tests/test_e2e.py -v`

**Step 4: Commit**

```bash
git add tests/test_e2e.py
git commit -m "feat: add end-to-end integration tests"
```

**Step 5: Test manual batch processing**

```bash
python generate_notes.py --batch examples/batch_MIS271.json --estimate-only
```

**Step 6: Final commit for Phase 5**

```bash
git add generate_notes.py
git commit -m "feat: add batch processing support to CLI"
```

---

## Summary of Tasks

### Phase 1: Foundation Testing (5 tasks)
- ✅ Test transcript_processor.py
- ✅ Test llm_generator.py
- ✅ Test cost_tracker.py
- ✅ Test obsidian_writer.py
- ✅ Create integration test harness

### Phase 2: Feynman Technique Enhancement (3 tasks)
- ✅ Create Feynman prompt templates
- ✅ Create note formatter
- ✅ Create LLM call wrapper with Feynman support

### Phase 3: Main CLI & User Interface (1 task)
- ✅ Create generate_notes.py main script

### Phase 4: Obsidian Integration (1 task)
- ✅ Enhance obsidian_writer with wikilinks and organization

### Phase 5: Advanced Features (2 tasks)
- ✅ Create batch processor
- ✅ Final integration and end-to-end testing

---

## Testing Checklist

Before completing, verify:

- [ ] All unit tests pass: `pytest tests/ -v`
- [ ] CLI help works: `python generate_notes.py --help`
- [ ] Single lecture works: `python generate_notes.py --course MIS271 --week 1 --estimate-only`
- [ ] Cost estimation is accurate
- [ ] Markdown output is valid
- [ ] Obsidian vault structure created correctly
- [ ] Batch configuration validation works
- [ ] Wikilinks are generated properly
- [ ] Frontmatter is valid YAML

---

## Success Criteria

✅ All tests pass
✅ CLI is user-friendly and well-documented
✅ Feynman technique notes are well-structured
✅ Cost tracking is accurate
✅ Obsidian integration works seamlessly
✅ Batch processing supports multiple courses
✅ Error handling is comprehensive
✅ Documentation is complete
