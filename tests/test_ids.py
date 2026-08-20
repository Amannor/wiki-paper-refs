from wiki_paper_refs.ids import normalize_arxiv_id, normalize_doi, normalize_pmid, parse_wiki_url
from wiki_paper_refs.papers import _earliest, _parse_pubmed_date


def test_parse_wiki_url():
    page = parse_wiki_url("https://en.wikipedia.org/wiki/CRISPR")
    assert page.title == "CRISPR"
    assert page.lang == "en"
    assert page.origin == "https://en.wikipedia.org"


def test_parse_wiki_url_underscores_and_query():
    page = parse_wiki_url("https://en.wikipedia.org/w/index.php?title=Messenger_RNA")
    assert page.title == "Messenger RNA"


def test_normalize_doi():
    assert normalize_doi("https://doi.org/10.1126/science.1258096") == "10.1126/science.1258096"
    assert normalize_doi("doi:10.1038/nature12373.") == "10.1038/nature12373"


def test_normalize_pmid_and_arxiv():
    assert normalize_pmid("https://pubmed.ncbi.nlm.nih.gov/24926016/") == "24926016"
    assert normalize_arxiv_id("https://arxiv.org/abs/1406.1455v2") == "1406.1455"


def test_earliest_publication_date():
    assert _earliest("2019-06-01", "2019", "2018-12") == "2018-12"


def test_parse_pubmed_date():
    assert _parse_pubmed_date("2014 Jun 13") == "2014-06-13"
    assert _parse_pubmed_date("2014 Jun") == "2014-06"
