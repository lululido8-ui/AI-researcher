"""Data models for academic paper research pipeline."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PaperRecord:
    """Normalized metadata for a paper candidate."""

    title: str
    abstract: str
    url: str
    source: str
    doi: str | None = None
    year: int | None = None
    venue: str | None = None
    oa_pdf_url: str | None = None
    is_open_access: bool = False
    citation_count: int | None = None
    relevance_score: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PaperFullText:
    """Fetched and parsed full text for a paper."""

    title: str
    content: str
    source_url: str
    doi: str | None = None
    chunks: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PaperSummary:
    """Structured summary artifacts for a long paper."""

    title: str
    source_url: str
    query_focused_summary: str
    global_summary: str
    chunk_summaries: list[str] = field(default_factory=list)
    doi: str | None = None


@dataclass(slots=True)
class AcademicPipelineResult:
    """Output of academic research pipeline."""

    context: str
    papers: list[PaperRecord] = field(default_factory=list)
    summaries: list[PaperSummary] = field(default_factory=list)
