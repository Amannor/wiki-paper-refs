from __future__ import annotations

from pydantic import BaseModel, Field


class AcademicReference(BaseModel):
    reference_id: str = Field(description="Wikipedia ref name, or a stable identifier such as the DOI.")
    reference_text: str = Field(description="Human-readable citation text from the article or publisher metadata.")
    wikipedia_added: str | None = Field(
        default=None,
        description="ISO timestamp of the first revision that contains this paper's identifier.",
    )
    paper_published: str | None = Field(
        default=None,
        description="Earliest publication date from Crossref, PubMed, or arXiv (year, year-month, or full date).",
    )
    doi: str | None = None
    pmid: str | None = None
    pmc: str | None = None
    arxiv_id: str | None = None
    work_type: str | None = Field(
        default=None,
        description="Publisher work type when known, e.g. journal-article or posted-content.",
    )

    def lookup_keys(self) -> list[str]:
        """Unique strings used to find this citation in historical wikitext."""
        keys: list[str] = []
        if self.doi:
            keys.append(self.doi)
            if "/" in self.doi:
                keys.append(self.doi.split("/", 1)[1])
        if self.arxiv_id:
            keys.append(self.arxiv_id)
        if self.pmid:
            keys.append(self.pmid)
        if self.pmc:
            keys.append(self.pmc)
        return keys
