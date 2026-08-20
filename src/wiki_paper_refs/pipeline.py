from __future__ import annotations

from wiki_paper_refs.extract import extract_references
from wiki_paper_refs.history import first_added_dates
from wiki_paper_refs.ids import parse_wiki_url
from wiki_paper_refs.models import AcademicReference
from wiki_paper_refs.papers import PaperClient
from wiki_paper_refs.wiki import WikiClient


def collect(
    url: str,
    *,
    skip_history: bool = False,
    skip_published: bool = False,
    mailto: str | None = None,
    on_progress=None,
) -> list[AcademicReference]:
    page = parse_wiki_url(url)
    with WikiClient(page.origin) as wiki:
        wikitext = wiki.get_current_wikitext(page.title)
        refs = extract_references(wikitext)
        if not skip_published:
            with PaperClient(mailto=mailto) as papers:
                enriched: list[AcademicReference] = []
                for index, ref in enumerate(refs, start=1):
                    if on_progress:
                        on_progress("publication dates", index, len(refs))
                    papers.enrich(ref)
                    if papers.is_academic(ref):
                        enriched.append(ref)
                refs = enriched
        if not skip_history and refs:
            def history_progress(fetched: int, total: int) -> None:
                if on_progress:
                    on_progress("wikipedia history", fetched, total)

            dates = first_added_dates(
                wiki, page.title, refs, on_progress=history_progress
            )
            for index, ref in enumerate(refs):
                ref.wikipedia_added = dates.get(index)
        return refs
