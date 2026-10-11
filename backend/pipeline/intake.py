#!/usr/bin/env python3
"""
Document intake for PlainTalk.

Turns an uploaded discharge sheet, lab report, or medication guide into
paragraphs with stable identifiers.

NO LANGUAGE MODEL IS USED. Splitting is deterministic because paragraph IDs
must be stable: the patient asks to simplify "paragraph 4", the citation
highlights "paragraph 4", and the gate compares against "paragraph 4". If a
model re-segmented the document on each upload, none of those would line up.

Clinical documents are not prose. They mix headers, numbered steps, and
bulleted lists, and a blank-line-only splitter mangles all three. The rules
below were written against the structure of real discharge instructions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# Structural patterns
# --------------------------------------------------------------------------
RE_BULLET = re.compile(r"^\s*[\u2022\u25cf\u25aa\u2043*\-\u2013]\s+")
RE_NUMBERED = re.compile(r"^\s*\(?(\d{1,2})[.)]\s+")
RE_LETTERED = re.compile(r"^\s*\(?([a-z])[.)]\s+", re.I)
RE_PAGE_NOISE = re.compile(
    r"^\s*(page\s+\d+(\s+of\s+\d+)?|\d+\s*/\s*\d+|-\s*\d+\s*-)\s*$", re.I
)

# A header is short, has no terminal punctuation, and is often all-caps.
def is_header(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > 70:
        return False
    if s.endswith((".", ",", ";", ":")) and not s.isupper():
        return False
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return False
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    return upper_ratio > 0.7 or (len(s.split()) <= 6 and not s.endswith("."))


def is_list_item(line: str) -> bool:
    return bool(RE_BULLET.match(line) or RE_NUMBERED.match(line)
                or RE_LETTERED.match(line))


@dataclass
class Paragraph:
    para_id: int
    text: str
    kind: str = "body"          # body | header | list_item
    page: int | None = None

    @property
    def is_content(self) -> bool:
        """Headers carry no instruction, so they are not simplified."""
        return self.kind != "header"


@dataclass
class Document:
    doc_id: str
    paragraphs: list[Paragraph] = field(default_factory=list)
    source_name: str = ""
    n_pages: int = 0

    def get(self, para_id: int) -> Paragraph | None:
        for p in self.paragraphs:
            if p.para_id == para_id:
                return p
        return None

    def content(self) -> list[Paragraph]:
        return [p for p in self.paragraphs if p.is_content]

    def texts(self) -> list[str]:
        return [p.text for p in self.paragraphs]


# --------------------------------------------------------------------------
# Splitting
# --------------------------------------------------------------------------
def split_paragraphs(text: str) -> list[Paragraph]:
    """
    Split raw text into paragraphs.

    Rules, in order of precedence:
      - a blank line ends the current paragraph
      - a header stands alone
      - each list item is its own paragraph, so "Hold metformin..." can be
        simplified without dragging in the four steps around it
      - a wrapped continuation line joins the paragraph above
      - page furniture is dropped
    """
    paras: list[Paragraph] = []
    buf: list[str] = []
    buf_kind = "body"

    def flush():
        nonlocal buf, buf_kind
        if buf:
            joined = " ".join(" ".join(buf).split())
            if joined:
                paras.append(Paragraph(len(paras), joined, buf_kind))
        buf, buf_kind = [], "body"

    for raw in text.splitlines():
        line = raw.rstrip()

        if not line.strip():
            flush()
            continue
        if RE_PAGE_NOISE.match(line):
            continue

        if is_header(line):
            flush()
            paras.append(Paragraph(len(paras), " ".join(line.split()), "header"))
            continue

        if is_list_item(line):
            flush()
            buf, buf_kind = [line.strip()], "list_item"
            continue

        # continuation of whatever is open, or the start of a body paragraph
        buf.append(line.strip())

    flush()
    return paras


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------
def read_pdf(path: str | Path) -> tuple[str, int]:
    """Extract text from a PDF. Returns (text, page_count)."""
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
            return "\n\n".join(pages), len(pages)
    except ImportError:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        pages = [p.extract_text() or "" for p in reader.pages]
        return "\n\n".join(pages), len(pages)


def load_document(path: str | Path, doc_id: str | None = None) -> Document:
    """
    Load a .pdf or .txt into a Document.

    A PDF with no extractable text is a scanned image. OCR is out of scope, so
    this raises rather than returning an empty document that would silently
    produce nothing to simplify.
    """
    path = Path(path)
    doc_id = doc_id or path.stem
    if path.suffix.lower() == ".pdf":
        text, n_pages = read_pdf(path)
    else:
        text, n_pages = path.read_text(encoding="utf-8", errors="ignore"), 0

    if not text.strip():
        raise ValueError(
            f"{path.name} contains no extractable text. It is probably a "
            f"scanned image; OCR intake is out of scope for this project."
        )

    return Document(doc_id, split_paragraphs(text), path.name, n_pages)


def load_text(text: str, doc_id: str = "doc1") -> Document:
    """Build a Document from a string. Used by tests and by pasted input."""
    return Document(doc_id, split_paragraphs(text), "", 0)
