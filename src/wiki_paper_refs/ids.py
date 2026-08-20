from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

DOI_RE = re.compile(r"10\.\d{4,9}/\S+", re.IGNORECASE)
PMID_URL_RE = re.compile(
    r"(?:pubmed\.ncbi\.nlm\.nih\.gov|ncbi\.nlm\.nih\.gov/pubmed)/(\d+)",
    re.IGNORECASE,
)
PMC_RE = re.compile(r"\bPMC(\d+)\b", re.IGNORECASE)
ARXIV_ID_RE = re.compile(
    r"(?:arXiv:)?((?:\d{4}\.\d{4,5})(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?",
    re.IGNORECASE,
)
ARXIV_URL_RE = re.compile(
    r"arxiv\.org/(?:abs|pdf|html)/([^\s?#]+)",
    re.IGNORECASE,
)

ACADEMIC_TEMPLATES = {
    "cite journal",
    "cite conference",
    "cite conference paper",
    "cite arxiv",
    "cite biorxiv",
    "cite medrxiv",
    "cite ssrn",
    "cite thesis",
    "cite dissertation",
    "cite report",
}


@dataclass(frozen=True)
class WikiPage:
    origin: str
    lang: str
    title: str


def parse_wiki_url(url: str) -> WikiPage:
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        parsed = urlparse("https://" + url.strip())
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if "wikipedia.org" not in host and "wikimedia.org" not in host:
        raise ValueError(f"Not a Wikipedia URL: {url}")

    lang = host.split(".")[0] if host.endswith(".wikipedia.org") else "en"
    origin = f"{parsed.scheme}://{parsed.netloc}"

    title = None
    if parsed.path.startswith("/wiki/"):
        title = unquote(parsed.path[len("/wiki/") :])
    else:
        qs = parse_qs(parsed.query)
        if "title" in qs:
            title = qs["title"][0]
    if not title:
        raise ValueError(f"Could not parse article title from URL: {url}")
    title = title.replace("_", " ")
    if not title:
        raise ValueError(f"Empty article title in URL: {url}")
    return WikiPage(origin=origin, lang=lang, title=title)


def normalize_doi(raw: str) -> str | None:
    text = unquote(raw.strip())
    text = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)\s*", "", text, flags=re.IGNORECASE)
    match = DOI_RE.search(text)
    if not match:
        return None
    doi = match.group(0)
    doi = doi.rstrip(").,;\"'")
    doi = doi.split("#")[0].split("?")[0]
    return doi.lower()


def normalize_arxiv_id(raw: str) -> str | None:
    text = unquote(raw.strip()).removesuffix(".pdf")
    url_match = ARXIV_URL_RE.search(text)
    if url_match:
        text = url_match.group(1)
    match = ARXIV_ID_RE.search(text)
    if not match:
        return None
    arxiv_id = match.group(1).rstrip(").,;\"'")
    arxiv_id = re.sub(r"v\d+$", "", arxiv_id, flags=re.IGNORECASE)
    return arxiv_id


def normalize_pmid(raw: str) -> str | None:
    text = raw.strip()
    url_match = PMID_URL_RE.search(text)
    if url_match:
        return url_match.group(1)
    digits = re.sub(r"\D", "", text)
    if digits and 4 <= len(digits) <= 8:
        return digits
    return None


def template_name(template) -> str:
    return str(template.name).strip().lower().replace("_", " ")
