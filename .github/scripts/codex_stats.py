#!/usr/bin/env python3
"""Public GitHub PR stats; only explicitly marked work is attributed to Codex."""
from __future__ import annotations
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

OWNER = os.getenv("CODEX_STATS_OWNER", "sunmeat")
TOKEN = os.getenv("GH_TOKEN", "")
README = Path(os.getenv("CODEX_STATS_README", "README.md"))
START = "<!--START_SECTION:codex-github-->"
END = "<!--END_SECTION:codex-github-->"
BOTS = {"chatgpt-codex-connector[bot]", "codex[bot]", "openai-codex[bot]"}
LABELS = {"codex", "ai:codex", "agent:codex", "openai-codex"}
SOURCE = re.compile(r"https?://(?:chatgpt\.com|chat\.openai\.com)/codex/(?:tasks?/|t/)", re.I)


def api(path, params=None):
    if not TOKEN:
        raise RuntimeError("Missing GH_TOKEN")
    url = "https://api.github.com" + path
    if params:
        url += "?" + urlencode(params)
    req = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "codex-readme-stats",
    })
    try:
        with urlopen(req, timeout=25) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"GitHub HTTP {exc.code}: {path}") from exc
    except (URLError, ValueError) as exc:
        raise RuntimeError(f"GitHub API failed: {path}: {exc}") from exc


def date(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else datetime.min.replace(tzinfo=timezone.utc)


def beginning_of_week(now):
    return (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def repos(since):
    # A user PAT can list owned private repos. A repository-scoped Actions
    # token cannot, so transparently fall back to public-only discovery.
    use_owned = True
    page = 1
    while page <= 10:
        path = "/user/repos" if use_owned else f"/users/{quote(OWNER)}/repos"
        params = {
            "sort": "pushed", "direction": "desc", "per_page": 100, "page": page,
        }
        if use_owned:
            params.update({"visibility": "all", "affiliation": "owner"})
        else:
            params["type"] = "owner"
        try:
            batch = api(path, params)
        except RuntimeError as exc:
            if page == 1 and use_owned and any(
                phrase in str(exc) for phrase in ("HTTP 401", "HTTP 403", "HTTP 404")
            ):
                print("Authenticated repo listing unavailable; using public repos only.", file=sys.stderr)
                use_owned = False
                continue
            raise
        if not isinstance(batch, list):
            raise RuntimeError("Invalid repositories response")
        for repo in batch:
            if ((repo.get("owner") or {}).get("login") or "").lower() != OWNER.lower():
                continue
            if date(repo.get("pushed_at")) < since:
                return
            if not repo.get("archived") and not repo.get("disabled"):
                yield repo["name"]
        if len(batch) < 100:
            return
        page += 1
    raise RuntimeError("Repository scan incomplete: >1000 entries")


def prs(name, since):
    for page in range(1, 11):
        batch = api(f"/repos/{quote(OWNER)}/{quote(name)}/pulls", {
            "state": "all", "sort": "updated", "direction": "desc", "per_page": 100, "page": page,
        })
        if not isinstance(batch, list):
            raise RuntimeError("Invalid PR response")
        for pr in batch:
            if date(pr.get("updated_at")) < since:
                return
            if date(pr.get("created_at")) >= since:
                yield pr
        if len(batch) < 100:
            return
    raise RuntimeError(f"PR scan incomplete: {name}")


def is_codex(pr):
    author = ((pr.get("user") or {}).get("login") or "").lower()
    head = ((pr.get("head") or {}).get("ref") or "").lower()
    labels = {x.get("name", "").lower() for x in pr.get("labels", [])}
    return (author in BOTS or head.startswith("codex/") or bool(labels & LABELS)
            or bool(SOURCE.search(pr.get("body") or ""))
            or (pr.get("title") or "").lower().startswith(("[codex]", "codex:")))


def collect(since):
    total = dict(prs=0, commits=0, added=0, deleted=0)
    ai = dict(prs=0, commits=0, added=0, deleted=0)
    inspected = 0
    active = set()
    identified = set()
    for name in repos(since):
        inspected += 1
        for pr in prs(name, since):
            detail = api(f"/repos/{quote(OWNER)}/{quote(name)}/pulls/{int(pr['number'])}")
            if not all(isinstance(detail.get(k), int) for k in ("commits", "additions", "deletions")):
                raise RuntimeError(f"Missing stats: {name} #{pr['number']}")
            active.add(name)
            total["prs"] += 1
            for key, source in (("commits", "commits"), ("added", "additions"), ("deleted", "deletions")):
                total[key] += detail[source]
            if is_codex(pr):
                identified.add(name)
                ai["prs"] += 1
                for key, source in (("commits", "commits"), ("added", "additions"), ("deleted", "deletions")):
                    ai[key] += detail[source]
    return total, ai, inspected, len(active), len(identified)


def render(since, now, total, ai, inspected, active, identified):
    return "\n".join([
        f"**{since:%d %b} – {now:%d %b %Y} (UTC)** · Week to date (from Monday)",
        "",
        "| Activity | Pull requests | Commits in PRs | Lines added | Lines removed |",
        "|:--|--:|--:|--:|--:|",
        f"| 🤖 Codex (explicitly identified) | **{ai['prs']:,}** | {ai['commits']:,} | +{ai['added']:,} | −{ai['deleted']:,} |",
        f"| 📦 All accessible PR activity | **{total['prs']:,}** | {total['commits']:,} | +{total['added']:,} | −{total['deleted']:,} |",
        "",
        f"Recently active repos scanned: **{inspected}** · With new PRs: **{active}** · With marked Codex PRs: **{identified}**.",
        "",
        "<sub>Only PRs opened this week in repositories accessible to the token are counted. Private-project names and details are not displayed. Commits and changed lines reflect current PR totals, not unique authored lines. Codex is identified by a bot author, codex/ branch, explicit codex label, Codex task link or [codex] title. Codex work without these markers appears only in the overall PR row. Models, tokens, session time and private data are not inferred. Add the codex label to Codex-created PRs for reliable tracking.</sub>",
    ])


def update(section):
    original = README.read_text(encoding="utf-8")
    if original.count(START) != 1 or original.count(END) != 1:
        raise RuntimeError("Missing or duplicated README markers")
    a = original.index(START) + len(START)
    b = original.index(END)
    if a >= b:
        raise RuntimeError("Reversed README markers")
    result = original[:a] + "\n" + section + "\n" + original[b:]
    if result != original:
        README.write_text(result, encoding="utf-8")
        return True
    return False


if __name__ == "__main__":
    try:
        now = datetime.now(timezone.utc)
        since = beginning_of_week(now)
        total, ai, inspected, active, identified = collect(since)
        changed = update(render(since, now, total, ai, inspected, active, identified))
        print(f"Codex: {ai}; PR activity: {total}; repos scanned: {inspected}; updated: {changed}")
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
