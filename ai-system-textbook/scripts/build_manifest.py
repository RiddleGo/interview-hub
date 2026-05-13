#!/usr/bin/env python3
"""Build manifest.json for AI-System Textbook reader from GitHub git tree API."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote

OWNER, REPO, BRANCH = "microsoft", "AI-System", "main"
USER_AGENT = "ai-system-textbook-manifest/1.0"


def http_json(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def github_blob_url(repo_path: str) -> str:
    enc = "/".join(quote(seg, safe="") for seg in repo_path.split("/"))
    return f"https://github.com/{OWNER}/{REPO}/blob/{BRANCH}/{enc}"


def raw_url(repo_path: str) -> str:
    enc = "/".join(quote(seg, safe="") for seg in repo_path.split("/"))
    return f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}/{enc}"


def github_tree_url(folder_path: str) -> str:
    enc = "/".join(quote(seg, safe="") for seg in folder_path.split("/"))
    return f"https://github.com/{OWNER}/{REPO}/tree/{BRANCH}/{enc}"


def main() -> None:
    commit = http_json(f"https://api.github.com/repos/{OWNER}/{REPO}/commits/{BRANCH}")
    tree_sha = commit["commit"]["tree"]["sha"]
    tree = http_json(
        f"https://api.github.com/repos/{OWNER}/{REPO}/git/trees/{tree_sha}?recursive=1"
    )
    if tree.get("truncated"):
        raise SystemExit("Git tree truncated; cannot build full manifest.")

    md_paths: list[str] = []
    for ent in tree.get("tree", []):
        if ent.get("type") != "blob":
            continue
        p = ent.get("path") or ""
        if p.startswith("Textbook/") and p.endswith(".md"):
            md_paths.append(p)

    chapter_re = re.compile(r"^Textbook/(第\d+章[^/]+)/")

    def chapter_key(p: str) -> tuple[int, str]:
        m = chapter_re.match(p)
        if not m:
            return (999, p)
        num_m = re.search(r"第(\d+)章", m.group(1))
        n = int(num_m.group(1)) if num_m else 999
        return (n, m.group(1))

    md_paths.sort(key=lambda p: (chapter_key(p), p))

    documents: list[dict] = []
    for p in md_paths:
        parts = p.split("/")
        name = parts[-1]
        title = name[:-3] if name.endswith(".md") else name
        m = chapter_re.match(p)
        chapter_folder: str | None = m.group(1) if m else None
        chapter_github = github_tree_url(f"Textbook/{chapter_folder}") if chapter_folder else github_tree_url("Textbook")
        documents.append(
            {
                "path": p,
                "title": title,
                "chapterFolder": chapter_folder,
                "raw": raw_url(p),
                "github": github_blob_url(p),
                "chapterGithub": chapter_github,
            }
        )

    out = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": f"https://github.com/{OWNER}/{REPO}/tree/{BRANCH}/Textbook",
        "documents": documents,
    }

    out_path = Path(__file__).resolve().parent.parent / "manifest.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(documents)} documents to {out_path}")

    base = out_path.parent
    inject_manifest_into_index(base, out)


def inject_manifest_into_index(base: Path, out: dict) -> None:
    """Write compact JSON inside index.html textarea so file:// works without a local server."""
    html_path = base / "index.html"
    html = html_path.read_text(encoding="utf-8")
    token = 'id="textbook-manifest-json"'
    i = html.find(token)
    if i == -1:
        raise SystemExit("index.html: missing textarea#textbook-manifest-json")
    i = html.find(">", i)
    if i == -1:
        raise SystemExit("index.html: malformed textarea open tag")
    i += 1
    j = html.find("</textarea>", i)
    if j == -1:
        raise SystemExit("index.html: missing closing </textarea>")
    payload = json.dumps(out, ensure_ascii=False)
    if "</textarea>" in payload.casefold():
        raise SystemExit("manifest JSON contains </textarea>; cannot embed safely")
    html_path.write_text(html[:i] + payload + html[j:], encoding="utf-8")
    print(f"Embedded manifest into {html_path}")


if __name__ == "__main__":
    main()
