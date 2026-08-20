from __future__ import annotations

import re

from wiki_paper_refs.models import AcademicReference
from wiki_paper_refs.wiki import WikiClient


def identifier_in_wikitext(ref: AcademicReference, wikitext: str) -> bool:
    text = wikitext.lower()
    if ref.doi:
        doi = ref.doi.lower()
        if doi in text:
            return True
        suffix = doi.split("/", 1)[1] if "/" in doi else doi
        if len(suffix) >= 8 and suffix in text:
            return True
    if ref.arxiv_id:
        arxiv = ref.arxiv_id.lower()
        if arxiv in text:
            return True
    if ref.pmc:
        if re.search(rf"\bpmc\s*{ref.pmc}\b", text):
            return True
    if ref.pmid:
        if re.search(rf"pmid\s*=\s*{ref.pmid}\b", text) or re.search(
            rf"pubmed(?:\.ncbi\.nlm\.nih\.gov)?/(?:pubmed/)?{ref.pmid}\b", text
        ):
            return True
    return False


def first_added_dates(
    client: WikiClient,
    title: str,
    refs: list[AcademicReference],
    *,
    on_progress=None,
) -> dict[int, str]:
    """Map ref index -> ISO timestamp of the earliest revision containing the paper id."""
    if not refs:
        return {}
    revisions = client.list_revisions(title)
    if not revisions:
        return {}

    cache: dict[int, str] = {}

    def text_at(index: int) -> str:
        revid = revisions[index].revid
        if revid not in cache:
            cache[revid] = client.get_wikitext_by_revid(revid)
            if on_progress:
                on_progress(len(cache), len(refs))
        return cache[revid]

    dates: dict[int, str] = {}
    remaining = list(range(len(refs)))

    def search(lo: int, hi: int, indexes: list[int]) -> None:
        if not indexes or lo > hi:
            return
        if lo == hi:
            wikitext = text_at(lo)
            timestamp = revisions[lo].timestamp
            for i in indexes:
                if identifier_in_wikitext(refs[i], wikitext):
                    dates[i] = timestamp
            return
        mid = (lo + hi) // 2
        wikitext = text_at(mid)
        present: list[int] = []
        absent: list[int] = []
        for i in indexes:
            if identifier_in_wikitext(refs[i], wikitext):
                present.append(i)
            else:
                absent.append(i)
        search(lo, mid, present)
        search(mid + 1, hi, absent)

    latest = text_at(len(revisions) - 1)
    remaining = [i for i in remaining if identifier_in_wikitext(refs[i], latest)]
    search(0, len(revisions) - 1, remaining)
    return dates
