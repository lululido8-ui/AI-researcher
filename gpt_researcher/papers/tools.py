"""Tooling components for domain-specific academic research."""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
from dataclasses import asdict
from typing import Iterable

import requests
from bs4 import BeautifulSoup
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..utils.llm import create_chat_completion
from .cache import PaperCache
from .models import PaperFullText, PaperRecord, PaperSummary


class CommDomainQueryPlanner:
    """Expand a research query using communication-domain terminology."""

    _DOMAIN_TERMS = [
        "5G NR", "6G", "massive MIMO", "beamforming", "OFDM", "channel estimation",
        "mmWave", "sub-6GHz", "terahertz", "RIS", "O-RAN", "Open RAN", "ISAC",
        "network slicing", "MEC", "NTN", "V2X", "URLLC", "eMBB", "mMTC",
    ]

    def plan(self, query: str, max_queries: int = 4) -> list[str]:
        query_lower = query.lower()
        chosen_terms = [term for term in self._DOMAIN_TERMS if term.lower() in query_lower][:2]
        planned = [query]
        for term in chosen_terms:
            planned.append(f"{query} {term}")
            planned.append(f"{term} survey")
        # Add a robust fallback communication-focused query.
        planned.append(f"{query} wireless communications research paper")
        deduped: list[str] = []
        for q in planned:
            if q not in deduped:
                deduped.append(q)
            if len(deduped) >= max_queries:
                break
        return deduped


class PaperDedupRanker:
    """Deduplicate and rank paper records."""

    @staticmethod
    def _normalize_title(title: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", title.lower())).strip()

    @staticmethod
    def _extract_arxiv_id(url: str) -> str | None:
        match = re.search(r"arxiv\.org/(?:abs|pdf)/([^/?#]+)", url or "", flags=re.IGNORECASE)
        if not match:
            return None
        return match.group(1).replace(".pdf", "")

    def deduplicate(self, records: Iterable[PaperRecord]) -> list[PaperRecord]:
        unique: dict[str, PaperRecord] = {}
        for record in records:
            key = ""
            if record.doi:
                key = f"doi:{record.doi.lower()}"
            elif (arxiv_id := self._extract_arxiv_id(record.url)):
                key = f"arxiv:{arxiv_id.lower()}"
            else:
                year = record.year if record.year is not None else 0
                key = f"title:{self._normalize_title(record.title)}|year:{year}"

            prev = unique.get(key)
            if prev is None:
                unique[key] = record
                continue

            # Prefer richer metadata and OA urls.
            prev_score = int(bool(prev.abstract)) + int(bool(prev.doi)) + int(bool(prev.oa_pdf_url))
            current_score = int(bool(record.abstract)) + int(bool(record.doi)) + int(bool(record.oa_pdf_url))
            if current_score >= prev_score:
                unique[key] = record

        return list(unique.values())

    def rank(self, records: list[PaperRecord], query: str, max_papers: int) -> list[PaperRecord]:
        query_terms = {t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2}
        for record in records:
            text = f"{record.title} {record.abstract}".lower()
            overlap = sum(1 for t in query_terms if t in text)
            year_score = (record.year or 2000) / 2100.0
            oa_boost = 0.4 if (record.is_open_access or record.oa_pdf_url) else 0.0
            citation_boost = min((record.citation_count or 0) / 200.0, 1.0)
            record.relevance_score = overlap + year_score + oa_boost + citation_boost
        return sorted(records, key=lambda r: r.relevance_score, reverse=True)[:max_papers]


class FullTextFetcher:
    """Fetch and cache full text from paper urls."""

    def __init__(self, cache: PaperCache, timeout: int = 20):
        self.cache = cache
        self.timeout = timeout

    def _cache_key(self, record: PaperRecord) -> str:
        return f"{record.doi or ''}|{record.oa_pdf_url or ''}|{record.url}"

    def fetch(self, record: PaperRecord) -> PaperFullText | None:
        cache_key = self._cache_key(record)
        cached = self.cache.get_text("fulltext", cache_key)
        if cached:
            return PaperFullText(
                title=record.title,
                content=cached,
                source_url=record.oa_pdf_url or record.url,
                doi=record.doi,
            )

        source_url = record.oa_pdf_url or record.url
        if not source_url:
            return None

        try:
            if source_url.lower().endswith(".pdf") or "arxiv.org/pdf/" in source_url.lower():
                content = self._fetch_pdf_text(source_url)
            else:
                content = self._fetch_html_text(source_url)
        except Exception:
            return None

        if not content:
            return None

        self.cache.set_text("fulltext", cache_key, content)
        return PaperFullText(
            title=record.title,
            content=content,
            source_url=source_url,
            doi=record.doi,
        )

    def _fetch_pdf_text(self, url: str) -> str:
        response = requests.get(url, timeout=self.timeout, stream=True)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_path = temp_file.name
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)

        try:
            pages = PyMuPDFLoader(temp_path).load()
            page_texts = []
            max_chars = int(os.getenv("ACADEMIC_PDF_MAX_CHARS", "180000"))
            for idx, page in enumerate(pages, start=1):
                text = page.page_content.strip()
                if not text:
                    continue
                page_texts.append(f"[Page {idx}]\n{text}")
                if sum(len(p) for p in page_texts) > max_chars:
                    break
            return "\n\n".join(page_texts)
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    def _fetch_html_text(self, url: str) -> str:
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return re.sub(r"\n{2,}", "\n\n", text)[:120000]


class PaperParser:
    """Convert full text to chunks for map-reduce summarization."""

    def __init__(self, chunk_size: int = 2600, chunk_overlap: int = 250):
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def parse(self, fulltext: PaperFullText, max_chunks: int = 8) -> PaperFullText:
        chunks = self.splitter.split_text(fulltext.content)
        fulltext.chunks = chunks[:max_chunks]
        return fulltext


class LongPaperSummarizer:
    """Map-reduce summarizer for long paper text."""

    def __init__(self, researcher):
        self.researcher = researcher

    async def summarize(self, paper: PaperFullText, query: str) -> PaperSummary | None:
        if not paper.chunks:
            return None

        chunk_summaries: list[str] = []
        for idx, chunk in enumerate(paper.chunks, start=1):
            prompt = self.researcher.prompt_family.generate_paper_chunk_summary_prompt(
                query=query,
                chunk_text=chunk,
                chunk_index=idx,
                total_chunks=len(paper.chunks),
                source_title=paper.title,
            )
            try:
                summary = await create_chat_completion(
                    model=self.researcher.cfg.fast_llm_model,
                    messages=[{"role": "user", "content": prompt}],
                    llm_provider=self.researcher.cfg.fast_llm_provider,
                    max_tokens=min(1200, self.researcher.cfg.fast_token_limit),
                    llm_kwargs=self.researcher.cfg.llm_kwargs,
                    cost_callback=self.researcher.add_costs,
                )
            except Exception:
                summary = chunk[:900]
            chunk_summaries.append(summary)

        global_prompt = self.researcher.prompt_family.generate_paper_global_summary_prompt(
            query=query,
            source_title=paper.title,
            chunk_summaries=chunk_summaries,
        )
        query_prompt = self.researcher.prompt_family.generate_paper_query_focused_summary_prompt(
            query=query,
            source_title=paper.title,
            global_summary_input="\n\n".join(chunk_summaries),
        )

        try:
            global_summary, query_focused = await asyncio.gather(
                create_chat_completion(
                    model=self.researcher.cfg.smart_llm_model,
                    messages=[{"role": "user", "content": global_prompt}],
                    llm_provider=self.researcher.cfg.smart_llm_provider,
                    max_tokens=min(1600, self.researcher.cfg.smart_token_limit),
                    llm_kwargs=self.researcher.cfg.llm_kwargs,
                    cost_callback=self.researcher.add_costs,
                ),
                create_chat_completion(
                    model=self.researcher.cfg.smart_llm_model,
                    messages=[{"role": "user", "content": query_prompt}],
                    llm_provider=self.researcher.cfg.smart_llm_provider,
                    max_tokens=min(1200, self.researcher.cfg.smart_token_limit),
                    llm_kwargs=self.researcher.cfg.llm_kwargs,
                    cost_callback=self.researcher.add_costs,
                ),
            )
        except Exception:
            global_summary = "\n".join(chunk_summaries[:3])
            query_focused = "\n".join(chunk_summaries[:2])

        return PaperSummary(
            title=paper.title,
            source_url=paper.source_url,
            query_focused_summary=query_focused,
            global_summary=global_summary,
            chunk_summaries=chunk_summaries,
            doi=paper.doi,
        )

    def to_cache_payload(self, summary: PaperSummary) -> dict:
        return asdict(summary)

    @staticmethod
    def from_cache_payload(payload: dict) -> PaperSummary:
        return PaperSummary(
            title=payload.get("title", ""),
            source_url=payload.get("source_url", ""),
            query_focused_summary=payload.get("query_focused_summary", ""),
            global_summary=payload.get("global_summary", ""),
            chunk_summaries=payload.get("chunk_summaries", []),
            doi=payload.get("doi"),
        )


class PaperExistenceValidator:
    """Validate that paper records point to real, existing publications.

    Uses DOI resolution via Crossref and URL reachability checks to filter out
    hallucinated or dead-link papers before they enter downstream summarization.
    """

    CROSSREF_WORKS_URL = "https://api.crossref.org/works/"
    REQUEST_HEADERS = {
        "User-Agent": "GPT-Researcher/1.0 (academic-paper-validator)",
    }

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    async def validate_batch(self, records: list[PaperRecord]) -> list[PaperRecord]:
        """Validate all records concurrently, returning only verified papers."""
        tasks = [self._validate_one(r) for r in records]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        verified: list[PaperRecord] = []
        for record, result in zip(records, results):
            if isinstance(result, Exception):
                continue
            if result:
                verified.append(record)
        return verified

    async def _validate_one(self, record: PaperRecord) -> bool:
        """Return True if the paper can be confirmed to exist."""
        if record.doi:
            if await self._verify_doi(record.doi):
                return True

        url = record.oa_pdf_url or record.url
        if url:
            if await self._verify_url(url):
                return True

        return False

    async def _verify_doi(self, doi: str) -> bool:
        """Check DOI existence via Crossref API (HTTP 200 = exists)."""
        def _request():
            resp = requests.get(
                f"{self.CROSSREF_WORKS_URL}{doi}",
                timeout=self.timeout,
                headers=self.REQUEST_HEADERS,
            )
            return resp.status_code == 200

        try:
            return await asyncio.to_thread(_request)
        except Exception:
            return False

    async def _verify_url(self, url: str) -> bool:
        """Check URL reachability via HEAD with GET fallback."""
        def _request():
            try:
                resp = requests.head(
                    url, timeout=self.timeout, allow_redirects=True,
                    headers=self.REQUEST_HEADERS,
                )
                if resp.status_code < 400:
                    return True
            except requests.RequestException:
                pass
            try:
                resp = requests.get(
                    url, timeout=self.timeout, allow_redirects=True,
                    headers=self.REQUEST_HEADERS, stream=True,
                )
                ok = resp.status_code < 400
                resp.close()
                return ok
            except requests.RequestException:
                return False

        try:
            return await asyncio.to_thread(_request)
        except Exception:
            return False


class CitationGraphAnalyzer:
    """Placeholder for future citation-network analysis."""

    def analyze(self, records: list[PaperRecord]) -> list[PaperRecord]:
        return records
