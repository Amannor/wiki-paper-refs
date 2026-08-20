from wiki_paper_refs.extract import extract_references
from wiki_paper_refs.history import identifier_in_wikitext
from wiki_paper_refs.models import AcademicReference

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


def test_identifier_in_wikitext_requires_pmid_context():
    ref = AcademicReference(reference_id="x", reference_text="x", pmid="12345")
    assert not identifier_in_wikitext(ref, "random 12345 in the article")
    assert identifier_in_wikitext(ref, "{{cite journal |pmid=12345}}")
