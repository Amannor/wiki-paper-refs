from __future__ import annotations

from wiki_paper_refs.ids import (
    ACADEMIC_TEMPLATES,
    normalize_arxiv_id,
    normalize_doi,
    normalize_pmid,
    template_name,
)
from wiki_paper_refs.models import AcademicReference

try:
    import mwparserfromhell
except ImportError as exc:  # pragma: no cover
    raise ImportError("mwparserfromhell is required to parse Wikipedia wikitext") from exc


def param(template, *names: str) -> str | None:
    for name in names:
        if template.has(name, ignore_empty=True):
            value = template.get(name).value
            text = value.strip_code().strip() if hasattr(value, "strip_code") else str(value).strip()
            if text:
                return text
    return None


def _collect_authors(template) -> str | None:
    author = param(template, "author", "authors")
    if author:
        return author
    names: list[str] = []
    for index in range(1, 9):
        suffix = "" if index == 1 else str(index)
        last = param(template, f"last{suffix}", f"author{suffix}")
        first = param(template, f"first{suffix}")
        if last and first:
            names.append(f"{last}, {first}")
        elif last:
            names.append(last)
        elif not last and index > 1:
            break
    if names:
        if len(names) > 3:
            return f"{names[0]} et al."
        return "; ".join(names)
    return None


def format_citation(template) -> str:
    parts: list[str] = []
    authors = _collect_authors(template)
    year = param(template, "year", "date")
    title = param(template, "title", "chapter")
    journal = param(template, "journal", "work", "conference", "booktitle", "publisher")
    if authors:
        parts.append(authors)
    if year:
        parts.append(f"({year})")
    if title:
        parts.append(title)
    if journal:
        parts.append(journal)
    if not parts:
        return str(template).strip()
    text = " ".join(parts[:2]) if authors and year else (parts[0] if parts else "")
    rest = parts[2:] if authors and year else parts[1:]
    if rest:
        text = f"{text}. " + ". ".join(rest) if text else ". ".join(rest)
    return text.rstrip(".") + "."


def identifiers_from_template(template) -> dict[str, str]:
    found: dict[str, str] = {}
    doi = normalize_doi(param(template, "doi", "DOI") or "") if param(template, "doi", "DOI") else None
    if not doi:
        url = param(template, "url", "URL") or ""
        doi = normalize_doi(url)
    if doi:
        found["doi"] = doi

    pmid_raw = param(template, "pmid", "PMID")
    if pmid_raw:
        pmid = normalize_pmid(pmid_raw)
        if pmid:
            found["pmid"] = pmid

    pmc_raw = param(template, "pmc", "PMC")
    if pmc_raw:
        digits = pmc_raw.upper().replace("PMC", "").strip()
        if digits.isdigit():
            found["pmc"] = digits

    arxiv_raw = param(template, "arxiv", "eprint", "arXiv")
    archive = (param(template, "archive") or "").lower()
    if arxiv_raw and (template_name(template) in {"cite arxiv", "cite biorxiv", "cite medrxiv"} or archive in {"arxiv", "biorxiv", "medrxiv"} or normalize_arxiv_id(arxiv_raw)):
        arxiv_id = normalize_arxiv_id(arxiv_raw)
        if arxiv_id:
            found["arxiv_id"] = arxiv_id
    url = param(template, "url", "URL") or ""
    if "arxiv_id" not in found:
        arxiv_id = normalize_arxiv_id(url)
        if arxiv_id:
            found["arxiv_id"] = arxiv_id
    return found


def is_academic_template(template) -> bool:
    name = template_name(template)
    if name in ACADEMIC_TEMPLATES:
        return True
    if name in {"citation", "cite"} and identifiers_from_template(template):
        return True
    return False


def _ref_name(tag) -> str | None:
    if not getattr(tag, "has", None):
        return None
    for attr in ("name", "Name"):
        if tag.has(attr):
            raw = str(tag.get(attr).value).strip().strip("\"'")
            return raw or None
    return None


def extract_references(wikitext: str) -> list[AcademicReference]:
    code = mwparserfromhell.parse(wikitext)
    refs: list[AcademicReference] = []
    seen: set[tuple[str, str]] = set()

    def add(reference: AcademicReference) -> None:
        key = (
            reference.doi or "",
            reference.pmid or reference.arxiv_id or reference.pmc or reference.reference_id,
        )
        if key in seen:
            return
        if not (reference.doi or reference.pmid or reference.pmc or reference.arxiv_id):
            return
        seen.add(key)
        refs.append(reference)

    unnamed = 0
    for tag in code.filter_tags(matches=lambda node: str(node.tag).lower() == "ref"):
        contents = str(tag.contents) if tag.contents else ""
        if not contents.strip():
            continue
        inner = mwparserfromhell.parse(contents)
        name = _ref_name(tag)
        for template in inner.filter_templates():
            if not is_academic_template(template) and not identifiers_from_template(template):
                continue
            ids = identifiers_from_template(template)
            if not ids:
                continue
            unnamed += 1 if not name else 0
            add(
                AcademicReference(
                    reference_id=name or ids.get("doi") or ids.get("pmid") or ids.get("arxiv_id") or str(unnamed),
                    reference_text=format_citation(template),
                    **ids,
                )
            )

    for template in code.filter_templates():
        if not is_academic_template(template) and not identifiers_from_template(template):
            continue
        ids = identifiers_from_template(template)
        if not ids:
            continue
        add(
            AcademicReference(
                reference_id=ids.get("doi") or ids.get("pmid") or ids.get("arxiv_id") or param(template, "title") or "untitled",
                reference_text=format_citation(template),
                **ids,
            )
        )

    return refs
