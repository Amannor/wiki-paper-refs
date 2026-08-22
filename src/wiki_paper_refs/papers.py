from __future__ import annotations

from datetime import date

import httpx

from wiki_paper_refs.models import AcademicReference
from wiki_paper_refs.wiki import USER_AGENT

ACADEMIC_WORK_TYPES = {
    "journal-article",
    "proceedings-article",
    "posted-content",
    "dissertation",
    "report",
    "peer-review",
    "book-chapter",
    "dataset",
}


def _date_parts_to_str(parts: list | None) -> str | None:
    if not parts:
        return None
    first = parts[0] if isinstance(parts[0], list) else parts
    if not first:
        return None
    year = int(first[0])
    month = int(first[1]) if len(first) > 1 else None
    day = int(first[2]) if len(first) > 2 else None
    if month and day:
        return date(year, month, day).isoformat()
    if month:
        return f"{year:04d}-{month:02d}"
    return f"{year:04d}"


def _earliest(*values: str | None) -> str | None:
    present = [v for v in values if v]
    if not present:
        return None

    def key(value: str) -> tuple[int, int, int]:
        parts = [int(p) for p in value.split("-")]
        year = parts[0]
        month = parts[1] if len(parts) > 1 else 1
        day = parts[2] if len(parts) > 2 else 1
        return (year, month, day)

    return min(present, key=key)


class PaperClient:
    def __init__(self, *, timeout: float = 30.0, mailto: str | None = None) -> None:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        self._mailto = mailto
        self._http = httpx.Client(headers=headers, timeout=timeout, follow_redirects=True)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> PaperClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def enrich(self, ref: AcademicReference) -> AcademicReference:
        published = None
        work_type = ref.work_type
        title_from_meta = None

        if ref.doi:
            meta = self._crossref(ref.doi)
            if meta:
                published = meta.get("published")
                work_type = meta.get("type") or work_type
                title_from_meta = meta.get("title")
        if not published and ref.pmid:
            meta = self._pubmed(ref.pmid)
            if meta:
                published = published or meta.get("published")
                work_type = work_type or "journal-article"
                title_from_meta = title_from_meta or meta.get("title")
                if not ref.doi and meta.get("doi"):
                    ref.doi = meta["doi"]
        if not published and ref.arxiv_id:
            meta = self._arxiv(ref.arxiv_id)
            if meta:
                published = published or meta.get("published")
                work_type = work_type or "posted-content"
                title_from_meta = title_from_meta or meta.get("title")

        ref.paper_published = published
        ref.work_type = work_type
        if title_from_meta and (not ref.reference_text or ref.reference_text.startswith("{{")):
            ref.reference_text = title_from_meta
        return ref

    def is_academic(self, ref: AcademicReference) -> bool:
        if ref.pmid or ref.arxiv_id or ref.pmc:
            return True
        if ref.work_type:
            return ref.work_type in ACADEMIC_WORK_TYPES
        return bool(ref.doi)

    def _crossref(self, doi: str) -> dict | None:
        params = {}
        if self._mailto:
            params["mailto"] = self._mailto
        try:
            response = self._http.get(f"https://api.crossref.org/works/{doi}", params=params)
            if response.status_code in {400, 404}:
                return None
            response.raise_for_status()
        except httpx.HTTPError:
            return None
        message = response.json().get("message") or {}
        dates = [
            _date_parts_to_str((message.get("published-online") or {}).get("date-parts")),
            _date_parts_to_str((message.get("published-print") or {}).get("date-parts")),
            _date_parts_to_str((message.get("published") or {}).get("date-parts")),
            _date_parts_to_str((message.get("issued") or {}).get("date-parts")),
        ]
        titles = message.get("title") or []
        return {
            "published": _earliest(*dates),
            "type": message.get("type"),
            "title": titles[0] if titles else None,
        }

    def _pubmed(self, pmid: str) -> dict | None:
        try:
            response = self._http.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                params={"db": "pubmed", "id": pmid, "retmode": "json"},
            )
            if response.status_code in {400, 404}:
                return None
            response.raise_for_status()
        except httpx.HTTPError:
            return None
        result = (response.json().get("result") or {}).get(pmid) or {}
        if not result:
            return None
        published = None
        for field in ("epubdate", "pubdate", "sortpubdate"):
            value = (result.get(field) or "").strip()
            if value:
                published = _parse_pubmed_date(value)
                if published:
                    break
        article_ids = {item.get("idtype"): item.get("value") for item in result.get("articleids") or []}
        return {
            "published": published,
            "title": result.get("title"),
            "doi": article_ids.get("doi"),
        }

    def _arxiv(self, arxiv_id: str) -> dict | None:
        try:
            response = self._http.get(
                "https://export.arxiv.org/api/query",
                params={"id_list": arxiv_id},
                headers={"Accept": "application/atom+xml"},
            )
            if response.status_code in {400, 404}:
                return None
            response.raise_for_status()
        except httpx.HTTPError:
            return None
        xml = response.text
        published = _xml_tag(xml, "published") or _xml_tag(xml, "updated")
        title = _xml_tag(xml, "title")
        if published:
            published = published[:10]
        if title:
            title = " ".join(title.split())
        if not published and not title:
            return None
        return {"published": published, "title": title}


def _parse_pubmed_date(value: str) -> str | None:
    value = value.replace("/", "-").strip()
    months = {
        "jan": "01",
        "feb": "02",
        "mar": "03",
        "apr": "04",
        "may": "05",
        "jun": "06",
        "jul": "07",
        "aug": "08",
        "sep": "09",
        "oct": "10",
        "nov": "11",
        "dec": "12",
    }
    parts = value.replace(",", " ").split()
    if len(parts) >= 1 and parts[0].isdigit() and len(parts[0]) == 4:
        year = parts[0]
        if len(parts) == 1:
            return year
        month = months.get(parts[1][:3].lower())
        if not month:
            return year
        if len(parts) >= 3 and parts[2].isdigit():
            return f"{year}-{month}-{int(parts[2]):02d}"
        return f"{year}-{month}"
    if len(value) >= 10 and value[4] == "-" and value[7] == "-":
        return value[:10]
    return None


def _xml_tag(xml: str, tag: str) -> str | None:
    start = xml.find(f"<{tag}>")
    end = xml.find(f"</{tag}>")
    if start == -1 or end == -1 or end <= start:
        return None
    return xml[start + len(tag) + 2 : end].strip()
