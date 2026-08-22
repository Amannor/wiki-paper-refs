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
# Pre-2007 ids are archive/YYMMNNN, not arbitrary word/digit paths (e.g. /desember/1135264).
ARXIV_ARCHIVES = frozenset(
    {
        "acc-phys",
        "adap-org",
        "alg-geom",
        "ao-sci",
        "astro-ph",
        "atom-ph",
        "bayes-an",
        "chao-dyn",
        "chem-ph",
        "cmp-lg",
        "comp-gas",
        "cond-mat",
        "cs",
        "dg-ga",
        "econ",
        "eess",
        "funct-an",
        "gr-qc",
        "hep-ex",
        "hep-lat",
        "hep-ph",
        "hep-th",
        "math",
        "math-ph",
        "mtrl-th",
        "nlin",
        "nucl-ex",
        "nucl-th",
        "patt-sol",
        "physics",
        "plasm-ph",
        "q-alg",
        "q-bio",
        "q-fin",
        "quant-ph",
        "solv-int",
        "stat",
    }
)
ARXIV_URL_RE = re.compile(
    r"arxiv\.org/(?:abs|pdf|html)/([^\s?#]+)",
    re.IGNORECASE,
)
ARXIV_NEW_ID_RE = re.compile(r"^\d{4}\.\d{4,5}(?:v\d+)?$", re.IGNORECASE)
ARXIV_OLD_ID_RE = re.compile(
    r"^([a-z]{1,16}(?:-[a-z]{1,16})?)(?:\.[a-z]{2,4})?/\d{7}(?:v\d+)?$",
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


def _parse_arxiv_identifier(text: str) -> str | None:
    candidate = unquote(text.strip()).rstrip(").,;\"'")
    candidate = re.sub(r"\.pdf$", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"^arxiv:", "", candidate, flags=re.IGNORECASE).strip()
    if ARXIV_NEW_ID_RE.match(candidate):
        return re.sub(r"v\d+$", "", candidate, flags=re.IGNORECASE)
    old = ARXIV_OLD_ID_RE.match(candidate)
    if old and old.group(1).lower() in ARXIV_ARCHIVES:
        return re.sub(r"v\d+$", "", candidate, flags=re.IGNORECASE)
    return None


def normalize_arxiv_id(raw: str) -> str | None:
    if not raw or not raw.strip():
        return None
    text = unquote(raw.strip())
    url_match = ARXIV_URL_RE.search(text)
    if url_match:
        return _parse_arxiv_identifier(url_match.group(1))
    if re.search(r"://", text) and "arxiv.org" not in text.lower():
        return None
    return _parse_arxiv_identifier(text)


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
