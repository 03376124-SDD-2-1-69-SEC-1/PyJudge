"""Split the page text of one problem statement into chunks.

A chunk boundary is a problem boundary, never a token count: one problem per
file, split in two when the statement has an input heading (story and
constraints before it, input/output and examples from it on). A statement with
no recognisable heading stays one chunk, so no text is ever dropped.

Pure and synchronous: pages in, chunks out. Extracting the text from a PDF is
AI-02's job and storing the chunks is AI-04's.
"""

import unicodedata
from dataclasses import dataclass
from enum import StrEnum


def _normalise(line: str) -> str:
    """NFKC, no surrounding whitespace, no trailing colon.

    NFKC makes "นำ" and the decomposed "นํา" that some PDFs emit compare equal.
    """
    return unicodedata.normalize("NFKC", line).strip().rstrip(":").strip()


# Bare "Input" is not a heading: examples use it as a table column and as an
# "Input :" line inside the story.
_INPUT_HEADINGS = frozenset({_normalise("ข้อมูลนำเข้า")})


class ChunkKind(StrEnum):
    STORY = "story"
    IO_EXAMPLES = "io_examples"
    WHOLE = "whole"


@dataclass(frozen=True, slots=True)
class Chunk:
    """A contiguous slice of a problem statement.

    `page_start` and `page_end` are 1-based and inclusive; they locate the
    first and last page holding text of this chunk, for citations.
    """

    text: str
    page_start: int
    page_end: int
    kind: ChunkKind


class ChunkingError(Exception):
    """The statement has no text to chunk."""


def chunk_pages(pages: list[str]) -> list[Chunk]:
    """Chunk one problem statement given its text page by page."""
    lines = [
        (page_number, line)
        for page_number, page in enumerate(pages, start=1)
        for line in page.splitlines()
    ]
    if not any(line.strip() for _, line in lines):
        raise ChunkingError("statement has no text")

    split_at = _find_input_heading(lines)
    if split_at is None:
        return [_build_chunk(lines, ChunkKind.WHOLE)]

    story, io_examples = lines[:split_at], lines[split_at:]
    return [
        _build_chunk(story, ChunkKind.STORY),
        _build_chunk(io_examples, ChunkKind.IO_EXAMPLES),
    ]


def _find_input_heading(lines: list[tuple[int, str]]) -> int | None:
    """Index of the first input heading that has story text before it."""
    has_story = False
    for index, (_, line) in enumerate(lines):
        if _is_input_heading(line):
            return index if has_story else None
        if line.strip():
            has_story = True
    return None


def _is_input_heading(line: str) -> bool:
    return _normalise(line) in _INPUT_HEADINGS


def _build_chunk(lines: list[tuple[int, str]], kind: ChunkKind) -> Chunk:
    text_pages = [page for page, line in lines if line.strip()]
    return Chunk(
        text="\n".join(line for _, line in lines).strip(),
        page_start=text_pages[0],
        page_end=text_pages[-1],
        kind=kind,
    )
