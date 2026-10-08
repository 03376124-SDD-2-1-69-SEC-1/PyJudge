"""Tests for the problem-statement chunker.

The fixtures are the page text of ten seed problems (programming.in.th, OPS-17)
extracted once from their PDFs; pages are separated by a form feed line. The
expected chunks were labelled by reading each file, not by running the chunker.
"""

from pathlib import Path

import pytest

from questly.ai.ingestion.chunking import Chunk, ChunkingError, ChunkKind, chunk_pages

FIXTURES = Path(__file__).parents[2] / "fixtures" / "ai"

STORY = ChunkKind.STORY
IO = ChunkKind.IO_EXAMPLES
WHOLE = ChunkKind.WHOLE

# fixture -> (kind, page_start, page_end) per expected chunk
EXPECTED: dict[str, list[tuple[ChunkKind, int, int]]] = {
    "0001": [(STORY, 1, 1), (IO, 1, 2)],
    "0004": [(STORY, 1, 1), (IO, 1, 1)],
    # the input heading opens page 2, so the story stays on page 1
    "0012": [(STORY, 1, 1), (IO, 2, 2)],
    "0030": [(STORY, 1, 1), (IO, 1, 2)],
    "1000": [(STORY, 1, 1), (IO, 1, 2)],
    "1087": [(STORY, 1, 1), (IO, 1, 2)],
    "codecube_001": [(STORY, 1, 1), (IO, 1, 1)],
    # these two spell the heading with a decomposed sara am
    "codecube_055": [(STORY, 1, 1), (IO, 1, 1)],
    "codecube_087": [(STORY, 1, 1), (IO, 1, 1)],
    # no Thai input heading, only "Input :" lines inside the story
    "codecube_009": [(WHOLE, 1, 2)],
}


def _pages(name: str) -> list[str]:
    text = (FIXTURES / f"pith_{name}.txt").read_text(encoding="utf-8")
    return text.split("\n\f\n")


def _shape(chunks: list[Chunk]) -> list[tuple[ChunkKind, int, int]]:
    return [(c.kind, c.page_start, c.page_end) for c in chunks]


@pytest.mark.parametrize("name", EXPECTED)
def test_fixture_is_chunked_as_labelled(name: str) -> None:
    assert _shape(chunk_pages(_pages(name))) == EXPECTED[name]


def test_at_least_80_percent_of_fixtures_match_their_labels() -> None:
    matches = sum(
        _shape(chunk_pages(_pages(name))) == expected
        for name, expected in EXPECTED.items()
    )

    assert matches / len(EXPECTED) >= 0.8


@pytest.mark.parametrize("name", EXPECTED)
def test_no_line_of_text_is_lost(name: str) -> None:
    pages = _pages(name)

    chunks = chunk_pages(pages)

    original = [line.strip() for page in pages for line in page.splitlines()]
    kept = [line.strip() for c in chunks for line in c.text.splitlines()]
    assert [line for line in original if line] == [line for line in kept if line]


def test_story_chunk_ends_before_the_input_heading() -> None:
    story, io = chunk_pages(["เรื่องราว\nข้อกำหนด\nข้อมูลนำเข้า\nn\nข้อมูลส่งออก\nm"])

    assert story.text == "เรื่องราว\nข้อกำหนด"
    assert io.text.startswith("ข้อมูลนำเข้า")


def test_heading_with_a_trailing_colon_still_splits() -> None:
    chunks = chunk_pages(["โจทย์\nข้อมูลนำเข้า :\nn"])

    assert [c.kind for c in chunks] == [STORY, IO]


def test_statement_without_a_heading_is_one_whole_chunk() -> None:
    chunks = chunk_pages(["โจทย์ข้อหนึ่ง\nไม่มีหัวข้อ", "หน้าสอง"])

    assert chunks == [
        Chunk(
            text="โจทย์ข้อหนึ่ง\nไม่มีหัวข้อ\nหน้าสอง",
            page_start=1,
            page_end=2,
            kind=WHOLE,
        )
    ]


def test_heading_with_no_story_before_it_is_one_whole_chunk() -> None:
    chunks = chunk_pages(["\n  \nข้อมูลนำเข้า\nn"])

    assert [c.kind for c in chunks] == [WHOLE]


def test_bare_english_input_is_not_a_heading() -> None:
    chunks = chunk_pages(["story\nInput\nOutput\n1\n2"])

    assert [c.kind for c in chunks] == [WHOLE]


def test_blank_trailing_page_does_not_widen_the_page_range() -> None:
    chunks = chunk_pages(["story\nข้อมูลนำเข้า\nn", "  \n"])

    assert _shape(chunks) == [(STORY, 1, 1), (IO, 1, 1)]


@pytest.mark.parametrize("pages", [[], [""], ["  \n\t", "\n"]])
def test_statement_with_no_text_raises(pages: list[str]) -> None:
    with pytest.raises(ChunkingError):
        chunk_pages(pages)
