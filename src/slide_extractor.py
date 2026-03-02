"""Slide text extraction module supporting text-based and image-based PDFs."""

import logging
from pathlib import Path
from typing import Dict, Optional
import pdfplumber

from src.models import SlideExtractionResult, SlideExtractionError

logger = logging.getLogger(__name__)


class SlideExtractor:
    """Extract text from PDF slides (text-based and image-based)."""

    def __init__(self):
        """Initialize SlideExtractor with lazy-loaded OCR reader."""
        self.reader = None  # EasyOCR reader, lazy-loaded if needed

    def extract_slide_text(
        self, pdf_path: Path, use_ocr_fallback: bool = True
    ) -> SlideExtractionResult:
        """
        Extract text from PDF slide file.

        Strategy:
        1. Try pdfplumber (fast, good for text-based PDFs)
        2. If < 50% of pages yield text, try OCR fallback (for image-based PDFs)
        3. Combine results: [page 1 text], [page 2 text], ...

        Args:
            pdf_path: Path to PDF file
            use_ocr_fallback: If True, use EasyOCR for image-based slides

        Returns:
            SlideExtractionResult with organized page text

        Raises:
            SlideExtractionError: If file not found or unreadable
        """
        # Case 1: File missing
        if not pdf_path.exists():
            return SlideExtractionResult(
                status="missing",
                error_message=f"Slide file not found at {pdf_path}. Notes can be generated without slides. Check config slide_path.",
            )

        # Case 2: File not a PDF
        if pdf_path.suffix.lower() != ".pdf":
            return SlideExtractionResult(
                status="error",
                error_message=f"File is not PDF (found {pdf_path.suffix}). Check slide_path in config.",
            )

        try:
            # Try pdfplumber first
            pdfplumber_results = self.extract_text_pdfplumber(pdf_path)

            # Check if we got meaningful text
            text_pages = sum(
                1
                for text in pdfplumber_results.values()
                if text and len(text.strip()) > 10
            )
            total_pages = len(pdfplumber_results)

            # If < 50% pages have text and OCR enabled, try OCR
            used_ocr = False
            if (
                use_ocr_fallback
                and (text_pages / total_pages if total_pages > 0 else 0) < 0.5
            ):
                logger.info("[INFO] Mostly image-based slides detected. Using OCR...")
                ocr_results = self.extract_text_ocr(pdf_path)
                # Merge results: prefer pdfplumber text, fall back to OCR
                final_results = {
                    page: (pdfplumber_results.get(page) or ocr_results.get(page, ""))
                    for page in pdfplumber_results
                }
                used_ocr = True
            else:
                final_results = pdfplumber_results

            # Organize by page and return
            organized_text = "\n\n".join(
                [
                    f"[Page {i}]\n{text}"
                    for i, text in enumerate(final_results.values(), 1)
                ]
            )

            return SlideExtractionResult(
                status="success",
                slide_text=organized_text,
                page_count=total_pages,
                text_pages=text_pages,
                used_ocr=used_ocr,
            )

        except Exception as e:
            logger.error(f"Error extracting slides: {str(e)}")
            return SlideExtractionResult(
                status="error",
                error_message=f"Cannot read PDF: {str(e)}. Notes can be generated without slides.",
            )

    def detect_image_slides(self, pdf_path: Path) -> bool:
        """
        Detect if PDF contains mostly image-based pages (scanned).

        Returns True if > 50% of pages have no extractable text (indicates scans).

        Args:
            pdf_path: Path to PDF file

        Returns:
            True if majority of pages are image-based, False otherwise
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                if total_pages == 0:
                    return False

                image_pages = 0
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text or len(text.strip()) == 0:
                        image_pages += 1

                ratio = image_pages / total_pages
                return ratio > 0.5
        except Exception as e:
            logger.error(f"Error detecting image slides: {str(e)}")
            return False

    def extract_text_pdfplumber(self, pdf_path: Path) -> Dict[int, str]:
        """
        Extract text from text-based PDF using pdfplumber.

        Returns: {page_num: text_content} dict

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary mapping page numbers to extracted text
        """
        try:
            results = {}
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    results[page_num] = text if text else ""
            return results
        except FileNotFoundError:
            raise SlideExtractionError(f"PDF file not found: {pdf_path}")
        except Exception as e:
            raise SlideExtractionError(
                f"Cannot read PDF. File may be corrupted or unsupported format: {str(e)}"
            )

    def extract_text_ocr(self, pdf_path: Path) -> Dict[int, str]:
        """
        Extract text from image-based PDF using EasyOCR.

        Returns: {page_num: text_content} dict

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary mapping page numbers to OCR-extracted text
        """
        try:
            import fitz  # PyMuPDF
            import easyocr

            # Lazy-load reader
            if self.reader is None:
                logger.info("[INFO] Loading EasyOCR (first run, ~100MB download)...")
                self.reader = easyocr.Reader(["en"])

            results = {}
            doc = fitz.open(pdf_path)

            for page_num, page in enumerate(doc, 1):
                try:
                    # Convert PDF page to image
                    pix = page.get_pixmap(
                        matrix=fitz.Matrix(2, 2)
                    )  # 2x zoom for clarity
                    image_bytes = pix.tobytes("ppm")

                    # OCR
                    ocr_results = self.reader.readtext(image_bytes)

                    # Extract text (filter by confidence > 0.3)
                    text_lines = [
                        result[1] for result in ocr_results if result[2] > 0.3
                    ]
                    results[page_num] = "\n".join(text_lines)
                except Exception as e:
                    logger.warning(
                        f"OCR timeout on page {page_num}. Text may be incomplete: {str(e)}"
                    )
                    results[page_num] = f"[OCR failed: {str(e)}]"

            doc.close()
            return results

        except ImportError as e:
            if "easyocr" in str(e):
                raise SlideExtractionError(
                    "EasyOCR not installed. Install with: pip install easyocr"
                )
            elif "fitz" in str(e):
                raise SlideExtractionError(
                    "PDF → Image conversion failed. Install: pip install pymupdf"
                )
            else:
                raise SlideExtractionError(f"Missing dependency: {str(e)}")
        except Exception as e:
            logger.error(f"Error during OCR extraction: {str(e)}")
            raise SlideExtractionError(f"OCR extraction failed: {str(e)}")


def extract_slide_text(
    pdf_path: Path, use_ocr_fallback: bool = True
) -> SlideExtractionResult:
    """
    Module-level function to extract slide text.

    Args:
        pdf_path: Path to PDF file
        use_ocr_fallback: If True, use EasyOCR for image-based slides

    Returns:
        SlideExtractionResult with organized page text
    """
    extractor = SlideExtractor()
    return extractor.extract_slide_text(pdf_path, use_ocr_fallback)


def detect_image_slides(pdf_path: Path) -> bool:
    """
    Module-level function to detect image-based slides.

    Args:
        pdf_path: Path to PDF file

    Returns:
        True if majority of pages are image-based
    """
    extractor = SlideExtractor()
    return extractor.detect_image_slides(pdf_path)
