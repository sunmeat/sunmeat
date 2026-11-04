#!/usr/bin/env python3
"""Show the top 10 GitHub Linguist languages across all owned repositories."""
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

OWNER = os.getenv("REPO_LANGUAGES_OWNER", "sunmeat")
TOKEN = os.getenv("GH_TOKEN", "")
README = Path(os.getenv("REPO_LANGUAGES_README", "README.md"))
START = "<!--START_SECTION:repo-languages-->"
END = "<!--END_SECTION:repo-languages-->"


def api(path, params=None):
    url = "https://api.github.com" + path
    if params:
        url += "?" + urlencode(params)
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
               "User-Agent": "github-owned-repo-language-report"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=headers), timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            temporary = exc.code in (429, 500, 502, 503, 504) or (
                exc.code == 403 and (exc.headers.get("Retry-After")
                                     or exc.headers.get("X-RateLimit-Remaining") == "0"))
            if temporary and attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            raise RuntimeError(f"GitHub HTTP {exc.code}: {path}") from exc
        except (URLError, ValueError) as exc:
            if attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            raise RuntimeError(f"GitHub request failed: {path}: {exc}") from exc
    raise RuntimeError("Retry limit exceeded")


def paged(path, params):
    for page in range(1, 101):
        batch = api(path, {**params, "page": page, "per_page": 100})
        if not isinstance(batch, list):
            raise RuntimeError(f"Unexpected repository response at {path}")
        yield from batch
        if len(batch) < 100:
            return
    raise RuntimeError(f"Incomplete repository listing: {path}")


def owned_repositories():
    # Include public repositories outside a repository-scoped GitHub Actions token.
    candidates = {}
    for repo in paged(f"/users/{quote(OWNER, safe='')}/repos",
                      {"type": "owner", "sort": "full_name", "direction": "asc"}):
        if ((repo.get("owner") or {}).get("login") or "").casefold() == OWNER.casefold():
            candidates[repo["name"]] = repo

    # A broad PAT also exposes owned private repositories.
    if TOKEN:
        try:
            additional = list(paged("/user/repos",
                                    {"affiliation": "owner", "visibility": "all",
                                     "sort": "full_name", "direction": "asc"}))
        except RuntimeError as exc:
            if any(code in str(exc) for code in ("HTTP 401", "HTTP 403", "HTTP 404")):
                print("Cannot list private repos with this token; public-only data.", file=sys.stderr)
                additional = []
            else:
                raise
        for repo in additional:
            if ((repo.get("owner") or {}).get("login") or "").casefold() == OWNER.casefold():
                candidates[repo["name"]] = repo
    return [candidates[name] for name in sorted(candidates, key=str.casefold)]


def collect():
    totals, repo_counts = Counter(), Counter()
    repositories = owned_repositories()
    nonempty = private = forks = 0
    for repo in repositories:
        name = repo["name"]
        langs = api(f"/repos/{quote(OWNER, safe='')}/{quote(name, safe='')}/languages")
        if not isinstance(langs, dict):
            raise RuntimeError(f"Invalid languages object: {name}")
        private += int(bool(repo.get("private")))
        forks += int(bool(repo.get("fork")))
        present = False
        for lang, size in langs.items():
            if not isinstance(lang, str) or not isinstance(size, int) or size < 0:
                raise RuntimeError(f"Invalid language size: {name}")
            if size:
                totals[lang] += size
                repo_counts[lang] += 1
                present = True
        nonempty += int(present)
    return totals, repo_counts, len(repositories), nonempty, private, forks


def size_label(size):
    for threshold, suffix in ((1024**3, "GiB"), (1024**2, "MiB"), (1024, "KiB")):
        if size >= threshold:
            return f"{size / threshold:,.2f} {suffix}"
    return f"{size:,} B"


def render(totals, repo_counts, scanned, nonempty, private, forks, now):
    ordered = sorted(totals.items(), key=lambda item: (-item[1], item[0].casefold()))
    grand_total = sum(totals.values())
    kyiv = now.astimezone(ZoneInfo("Europe/Kyiv"))
    rows = []
    for n, (lang, count) in enumerate(ordered[:10], 1):
        percentage = count * 100 / grand_total if grand_total else 0
        filled = min(20, round(percentage / 5))
        bar = "█" * filled + "░" * (20 - filled)
        rows.append(f"| {n} | {lang.replace('|', '&#124;')} | **{percentage:.2f}%** "
                    f"| {bar} | {repo_counts[lang]:,} | {size_label(count)} |")
    if not rows:
        rows.append("| — | No language data | — | — | — | — |")
    other = sum(value for _, value in ordered[10:])
    other_percent = other * 100 / grand_total if grand_total else 0
    return "\n".join([
        "**Top 10 languages across all my GitHub repositories**", "",
        "| # | Language | Share of code | Distribution | Repositories | Detected size |",
        "|--:|:--|--:|:--|--:|--:|", *rows, "",
        f"**Languages found:** {len(ordered):,} · **Repositories scanned:** {scanned:,} "
        f"({nonempty:,} with language data, {private:,} accessible private, {forks:,} forks) · "
        f"**Detected code:** {size_label(grand_total)}.",
        f"**Other {max(len(ordered)-10, 0):,} languages:** {other_percent:.2f}% of detected code.",
        "",
        f"**Last successful refresh:** {now:%d %b %Y, %H:%M:%S} UTC · "
        f"{kyiv:%d %b %Y, %H:%M:%S %Z} (Kyiv)", "",
        "<sub>Data: GitHub Linguist /languages API. Percentages use detected file bytes "
        "across all languages (not only the top ten), not repository counts, lines "
        "written, or time spent. All accessible owned repositories are included, "
        "including forks and archived repos. Private repos require a permitted token; "
        "only aggregate statistics are exposed. GitHub Linguist can exclude generated "
        "and vendor code. Scheduled hourly.</sub>"
    ])


def update(section):
    old = README.read_text(encoding="utf-8")
    if old.count(START) != 1 or old.count(END) != 1:
        raise RuntimeError("Missing or duplicate README language-section markers")
    first, last = old.index(START) + len(START), old.index(END)
    if first >= last:
        raise RuntimeError("Reversed README language-section markers")
    revised = old[:first] + "\n" + section + "\n" + old[last:]
    if revised == old:
        return False
    README.write_text(revised, encoding="utf-8")
    return True


if __name__ == "__main__":
    try:
        totals, repo_counts, scanned, nonempty, private, forks = collect()
        changed = update(render(totals, repo_counts, scanned, nonempty, private, forks,
                                datetime.now(timezone.utc)))
        print(f"Repositories={scanned}, languages={len(totals)}, updated={changed}")
    except (RuntimeError, OSError, ValueError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        sys.exit(1)
