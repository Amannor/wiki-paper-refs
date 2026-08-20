from __future__ import annotations

import csv
import json
import os
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from wiki_paper_refs.pipeline import collect

console = Console(stderr=True)


def main(
    url: str = typer.Argument(..., help="URL of a Wikipedia article"),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json, table, or csv"),
    skip_history: bool = typer.Option(
        False,
        "--skip-history",
        help="Do not look up when each reference was first added (much faster).",
    ),
    skip_published: bool = typer.Option(
        False,
        "--skip-published",
        help="Do not look up publisher dates from Crossref/PubMed/arXiv.",
    ),
    mailto: Optional[str] = typer.Option(
        None,
        "--mailto",
        help="Contact email for Crossref's polite pool. Defaults to CROSSREF_MAILTO.",
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write output to a file instead of stdout"),
) -> None:
    """Extract academic paper references from a Wikipedia article."""
    fmt = format.lower()
    if fmt not in {"json", "table", "csv"}:
        raise typer.BadParameter("format must be json, table, or csv")
    contact = mailto or os.environ.get("CROSSREF_MAILTO")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Fetching Wikipedia article…", total=None)

        def on_progress(stage: str, done: int, total: int) -> None:
            progress.update(task, description=f"{stage}: {done}/{total}")

        try:
            refs = collect(
                url,
                skip_history=skip_history,
                skip_published=skip_published,
                mailto=contact,
                on_progress=on_progress,
            )
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

    payload = [ref.model_dump() for ref in refs]
    rendered = _render(payload, fmt)
    if output:
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            if not rendered.endswith("\n"):
                handle.write("\n")
    else:
        sys.stdout.write(rendered)
        if not rendered.endswith("\n"):
            sys.stdout.write("\n")


def _render(payload: list[dict], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(payload, indent=2, ensure_ascii=False)
    if fmt == "csv":
        fields = [
            "reference_id",
            "reference_text",
            "wikipedia_added",
            "paper_published",
            "doi",
            "pmid",
            "pmc",
            "arxiv_id",
            "work_type",
        ]
        from io import StringIO

        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in payload:
            writer.writerow(row)
        return buffer.getvalue()

    table = Table(title=f"{len(payload)} academic references")
    table.add_column("id", overflow="fold")
    table.add_column("reference", overflow="fold")
    table.add_column("added to Wikipedia")
    table.add_column("paper published")
    for row in payload:
        table.add_row(
            row.get("reference_id") or "",
            row.get("reference_text") or "",
            row.get("wikipedia_added") or "",
            row.get("paper_published") or "",
        )
    capture = Console(record=True, width=120)
    capture.print(table)
    return capture.export_text()


def app() -> None:
    typer.run(main)


if __name__ == "__main__":
    app()
