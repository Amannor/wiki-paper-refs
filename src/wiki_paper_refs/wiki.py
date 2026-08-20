from __future__ import annotations

from dataclasses import dataclass

import httpx

from wiki_paper_refs.version import __version__

DEFAULT_CONTACT = "https://github.com/Amannor/wiki-paper-refs"
USER_AGENT = f"wiki-paper-refs/{__version__} ({DEFAULT_CONTACT})"


@dataclass
class RevisionStub:
    revid: int
    timestamp: str


class WikiClient:
    def __init__(self, origin: str, *, timeout: float = 60.0) -> None:
        self.origin = origin.rstrip("/")
        self._http = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=timeout,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> WikiClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _api(self, **params) -> dict:
        params.setdefault("action", "query")
        params.setdefault("format", "json")
        params.setdefault("formatversion", "2")
        params.setdefault("maxlag", "5")
        response = self._http.get(f"{self.origin}/w/api.php", params=params)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RuntimeError(f"MediaWiki API error: {data['error']}")
        return data

    def get_current_wikitext(self, title: str) -> str:
        data = self._api(
            titles=title,
            prop="revisions",
            rvslots="main",
            rvprop="content",
            rvlimit="1",
        )
        pages = data.get("query", {}).get("pages", [])
        if not pages or pages[0].get("missing"):
            raise FileNotFoundError(f"Wikipedia article not found: {title}")
        revisions = pages[0].get("revisions") or []
        if not revisions:
            raise FileNotFoundError(f"No revisions for Wikipedia article: {title}")
        return revisions[0]["slots"]["main"]["content"]

    def list_revisions(self, title: str) -> list[RevisionStub]:
        stubs: list[RevisionStub] = []
        cont: dict[str, str] = {}
        while True:
            data = self._api(
                titles=title,
                prop="revisions",
                rvprop="ids|timestamp",
                rvlimit="max",
                rvdir="newer",
                **cont,
            )
            pages = data.get("query", {}).get("pages", [])
            if not pages or pages[0].get("missing"):
                raise FileNotFoundError(f"Wikipedia article not found: {title}")
            for rev in pages[0].get("revisions") or []:
                stubs.append(RevisionStub(revid=rev["revid"], timestamp=rev["timestamp"]))
            if "continue" in data:
                cont = {k: str(v) for k, v in data["continue"].items()}
            else:
                break
        return stubs

    def get_wikitext_by_revid(self, revid: int) -> str:
        data = self._api(
            revids=str(revid),
            prop="revisions",
            rvslots="main",
            rvprop="content",
        )
        pages = data.get("query", {}).get("pages", [])
        revisions = (pages[0].get("revisions") or []) if pages else []
        if not revisions:
            return ""
        slot = revisions[0].get("slots", {}).get("main", {})
        return slot.get("content") or ""
