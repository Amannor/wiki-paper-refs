from pathlib import Path

from wiki_paper_refs.extract import extract_references
from wiki_paper_refs.history import identifier_in_wikitext
from wiki_paper_refs.models import AcademicReference

FIXTURES = Path(__file__).parent / "fixtures"
CIRCADIAN_RHYTHM_URL = "https://en.wikipedia.org/wiki/Circadian_rhythm"

WIKITEXT = """
Some prose.<ref name="Doudna2014">{{cite journal |last=Doudna |first=Jennifer |title=The new frontier of genome engineering |journal=Science |year=2014 |doi=10.1126/science.1258096 |pmid=24926016}}</ref>
News should be ignored.<ref>{{cite news |title=A magazine story |url=https://example.com |date=2020}}</ref>
{{cite journal |title=Standalone bibliography item |journal=Nature |year=2012 |doi=10.1038/nature12373}}
"""


def test_extract_only_academic_with_ids():
    refs = extract_references(WIKITEXT)
    dois = {ref.doi for ref in refs}
    assert "10.1126/science.1258096" in dois
    assert "10.1038/nature12373" in dois
    assert all(ref.doi for ref in refs)
    named = next(ref for ref in refs if ref.doi == "10.1126/science.1258096")
    assert named.reference_id == "Doudna2014"
    assert "Doudna" in named.reference_text
    assert named.pmid == "24926016"


def test_circadian_rhythm_excerpt_keeps_papers_drops_news():
    wikitext = (FIXTURES / "circadian_rhythm.wiki").read_text(encoding="utf-8")
    assert CIRCADIAN_RHYTHM_URL in wikitext
    refs = extract_references(wikitext)
    dois = {ref.doi for ref in refs}
    assert dois == {"10.1093/hmg/ddl207"}
    assert refs[0].reference_id == "Ko2006"
    assert refs[0].pmid == "16987893"


def test_nonacademic_article_excerpt_has_no_papers():
    wikitext = (FIXTURES / "nonacademic_article.wiki").read_text(encoding="utf-8")
    assert extract_references(wikitext) == []


def test_news_url_is_not_treated_as_arxiv_paper():
    wikitext = """
<ref>{{Cite news |title=Reinsdyr uten døgnrytme |url=http://www.forskning.no/Artikler/2005/desember/1135264557.29 |date=December 2005}}</ref>
"""
    assert extract_references(wikitext) == []


def test_identifier_in_wikitext_requires_pmid_context():
    ref = AcademicReference(reference_id="x", reference_text="x", pmid="12345")
    assert not identifier_in_wikitext(ref, "random 12345 in the article")
    assert identifier_in_wikitext(ref, "{{cite journal |pmid=12345}}")
