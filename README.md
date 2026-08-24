# wiki-paper-refs

CLI that takes a Wikipedia article URL and prints **academic paper** references. Each item includes:

| Field | Meaning |
| --- | --- |
| `reference_id` | Wikipedia `<ref name="...">` when present, otherwise DOI / PMID / arXiv id |
| `reference_text` | Human-readable citation from the cite template |
| `wikipedia_added` | ISO timestamp of the first revision that contains this paper's identifier |
| `paper_published` | Earliest publication date from Crossref, PubMed, or arXiv |
| `doi`, `pmid`, `pmc`, `arxiv_id` | Identifiers when known |
| `work_type` | Publisher type (for example `journal-article`, `posted-content`) |

News, web pages, and most books are skipped. A reference is kept if it has a DOI, PMID, PMC, or arXiv id and looks like a paper or preprint.

Requires **Python 3.10+**. Talks to the Wikipedia API plus Crossref, PubMed, and arXiv (no API keys).

## Install

```bash
pip install wiki-paper-refs
```

That installs the `wiki-paper-refs` command. Then:

```bash
wiki-paper-refs --help
```

From a clone:

```bash
git clone https://github.com/Amannor/wiki-paper-refs.git
cd wiki-paper-refs
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

## Usage

```bash
wiki-paper-refs "https://en.wikipedia.org/wiki/CRISPR"
wiki-paper-refs "https://en.wikipedia.org/wiki/Okazaki_fragments" --format table
wiki-paper-refs "https://en.wikipedia.org/wiki/CRISPR" -o refs.json
wiki-paper-refs --help
```

| Option | Description |
| --- | --- |
| `-f`, `--format` | `json` (default), `table`, or `csv` |
| `-o`, `--output` | Write to a file instead of stdout |
| `--skip-history` | Do not look up when each reference was first added (much faster) |
| `--skip-published` | Do not look up publisher dates |
| `--mailto` | Contact email for Crossref's polite pool (or set `CROSSREF_MAILTO`) |

JSON is meant for piping into other tools. `--skip-history` is the right default while you iterate; full history walks every article's revisions and can take a long time on large pages.

If the page has no academic paper citations, the command prints a message on stderr, writes an empty list, and exits with code `2`.

### Library usage

```python
from wiki_paper_refs import collect

refs = collect(
    "https://en.wikipedia.org/wiki/Okazaki_fragments",
    skip_history=True,
)
for ref in refs:
    print(ref.reference_id, ref.paper_published)
```

## How dates are resolved

**Wikipedia added date.** The tool lists the article's revisions, then binary-searches wikitext for the first revision that contains that paper's DOI (or PMID / arXiv id). That is usually when the citation was added. If the paper was cited first without an identifier and the DOI was filled in later, the timestamp is the identifier addition, not the original footnote.

**Publication date.** For DOIs, Crossref `published-online`, `published-print`, `published`, and `issued` are compared and the earliest is used. PMID and arXiv are fallbacks when there is no usable Crossref date.

The User-Agent already identifies this tool to Wikipedia. Set `CROSSREF_MAILTO` if you run many lookups.

## Limitations

- Only English and other Wikimedia wikis reachable as `*.wikipedia.org` URLs.
- Citations without DOI / PMID / PMC / arXiv are omitted, even if they are journal articles.
- Very large articles (thousands of revisions, hundreds of papers) will be slow unless you pass `--skip-history`.

## License

MIT. See [LICENSE](LICENSE).
