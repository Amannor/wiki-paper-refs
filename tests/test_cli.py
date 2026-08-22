import typer
from typer.testing import CliRunner

from wiki_paper_refs import cli
from wiki_paper_refs.models import AcademicReference

CIRCADIAN_RHYTHM_URL = "https://en.wikipedia.org/wiki/Circadian_rhythm"


def _app():
    app = typer.Typer()
    app.command()(cli.main)
    return app


def test_nonacademic_article_exits_with_message(monkeypatch):
    monkeypatch.setattr(cli, "collect", lambda *args, **kwargs: [])
    result = CliRunner().invoke(_app(), ["https://en.wikipedia.org/wiki/Example"])
    if result.exit_code == 2 and "Missing argument" in (result.output or ""):
        result = CliRunner().invoke(_app(), ["main", "https://en.wikipedia.org/wiki/Example"])
    assert result.exit_code == 2
    assert "No academic paper references found" in result.output
    assert "[]" in result.stdout


def test_academic_article_does_not_push_back(monkeypatch):
    monkeypatch.setattr(
        cli,
        "collect",
        lambda *args, **kwargs: [
            AcademicReference(
                reference_id="Ko2006",
                reference_text="Ko CH, Takahashi JS. Molecular components.",
                doi="10.1093/hmg/ddl207",
            )
        ],
    )
    result = CliRunner().invoke(_app(), [CIRCADIAN_RHYTHM_URL])
    if result.exit_code != 0:
        result = CliRunner().invoke(_app(), ["main", CIRCADIAN_RHYTHM_URL])
    assert result.exit_code == 0
    assert "10.1093/hmg/ddl207" in result.stdout
    assert "No academic paper references found" not in result.output
