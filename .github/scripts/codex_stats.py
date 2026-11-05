#!/usr/bin/env python3
"""Public GitHub PR stats; only explicitly marked work is attributed to Codex."""
from __future__ import annotations
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
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

# Explicit attribution only; an agent name in ordinary prose is not evidence.
AGENT_ORDER = ("codex", "claude", "copilot", "cursor", "gemini")
AGENT_TITLES = {
    "codex": "🤖 OpenAI Codex",
    "claude": "🟠 Claude Code",
    "copilot": "🟣 GitHub Copilot",
    "cursor": "🔵 Cursor",
    "gemini": "💎 Gemini",
}
AGENT_LABELS = {
    "claude": {"claude", "claude-code", "ai:claude", "agent:claude"},
    "copilot": {"copilot", "github-copilot", "ai:copilot", "agent:copilot"},
    "cursor": {"cursor", "cursor-agent", "ai:cursor", "agent:cursor"},
    "gemini": {"gemini", "gemini-cli", "ai:gemini", "agent:gemini"},
}
AGENT_BOTS = {
    "claude": {"claude[bot]", "claude-code[bot]"},
    "copilot": {"copilot-swe-agent[bot]"},
    "cursor": {"cursor[bot]", "cursor-agent[bot]"},
    "gemini": {"gemini-code-assist[bot]"},
}
AGENT_PREFIXES = {
    "claude": ("claude/",),
    "copilot": ("copilot/",),
    "cursor": ("cursor/",),
    "gemini": ("gemini/",),
}
AGENT_TITLE_MARKERS = {
    "claude": ("[claude]", "[claude code]"),
    "copilot": ("[copilot]", "[github copilot]"),
    "cursor": ("[cursor]",),
    "gemini": ("[gemini]", "[gemini cli]"),
}
AGENT_BODY_MARKERS = {
    "claude": re.compile(r"generated with\s+(?:\[claude code\]|claude code\b)|https?://(?:claude\.ai/code|claude\.com/claude-code)(?:\b|/)", re.I),
    "copilot": re.compile(r"generated with\s+(?:\[github copilot\]|github copilot\b)", re.I),
    "cursor": re.compile(r"generated with\s+(?:\[cursor\]|cursor cloud agent\b)", re.I),
    "gemini": re.compile(r"generated with\s+(?:\[gemini cli\]|gemini cli\b)", re.I),
}
TRAILER = re.compile(r"(?im)^\s*(co-authored-by|ai-tool):\s*(.+?)\s*$")
AUTOMATED_PROFILE_REPO = OWNER.lower()


class EmptyRepositoryError(RuntimeError):
    """GitHub returns HTTP 409 when an initialized repository has no commits."""


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
        # Only an explicit "Git Repository is empty." response for the
        # repository-level commits endpoint is safely skippable. Other 409s
        # must still fail the collection instead of hiding incomplete data.
        if exc.code == 409 and re.fullmatch(r"/repos/[^/]+/[^/]+/commits", path):
            try:
                error_body = json.load(exc)
            except (OSError, ValueError):
                error_body = {}
            message = error_body.get("message", "") if isinstance(error_body, dict) else ""
            if isinstance(message, str) and message.strip().rstrip(".").lower() == "git repository is empty":
                raise EmptyRepositoryError(f"Repository has no commits: {path}") from exc
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


def identified_pr_agents(pr):
    """Return only agents supported by explicit PR metadata."""
    agents = {"codex"} if is_codex(pr) else set()
    author = ((pr.get("user") or {}).get("login") or "").lower()
    head = ((pr.get("head") or {}).get("ref") or "").lower()
    title = (pr.get("title") or "").lower()
    labels = {str(label.get("name") or "").lower() for label in (pr.get("labels") or [])}
    body = pr.get("body") or ""
    for agent in AGENT_ORDER[1:]:
        if (author in AGENT_BOTS[agent]
                or any(head.startswith(prefix) for prefix in AGENT_PREFIXES[agent])
                or bool(labels & AGENT_LABELS[agent])
                or title.startswith(AGENT_TITLE_MARKERS[agent])
                or bool(AGENT_BODY_MARKERS[agent].search(body))):
            agents.add(agent)
    return agents


def agent_from_name(name, email="", login=""):
    """Require a credible author/co-author marker, not a vague text mention."""
    name = (name or "").strip().lower()
    email = (email or "").strip().lower()
    login = (login or "").strip().lower()
    if login in BOTS or name in {"openai codex", "codex[bot]"}:
        return "codex"
    if login in AGENT_BOTS["copilot"] or name in {"github copilot", "copilot-swe-agent[bot]", "copilot"}:
        return "copilot"
    if login in AGENT_BOTS["cursor"] or name in {"cursor agent", "cursor cloud agent", "cursor[bot]"}:
        return "cursor"
    if login in AGENT_BOTS["gemini"] or name in {"gemini cli", "gemini code assist", "gemini-code-assist[bot]"}:
        return "gemini"
    if login in AGENT_BOTS["claude"] or (
        (name.startswith("claude ") or name == "claude") and email.endswith("@anthropic.com")
    ) or name == "claude code":
        return "claude"
    return None


def identified_commit_agents(commit):
    """Inspect Git commit author and explicit Co-Authored-By / AI-Tool trailers."""
    result = set()
    raw = commit.get("commit") or {}
    author = raw.get("author") or {}
    login = (commit.get("author") or {}).get("login") or ""
    detected = agent_from_name(author.get("name"), author.get("email"), login)
    if detected:
        result.add(detected)
    for key, value in TRAILER.findall(raw.get("message") or ""):
        if key.lower() == "ai-tool":
            marker = value.strip().lower()
            for agent, values in {
                "codex": {"codex", "openai codex"},
                "claude": {"claude", "claude code"},
                "copilot": {"copilot", "github copilot"},
                "cursor": {"cursor", "cursor cloud agent"},
                "gemini": {"gemini", "gemini cli", "gemini code assist"},
            }.items():
                if marker in values:
                    result.add(agent)
        else:
            coauthor = re.fullmatch(r"(.+?)\s*<([^>]+)>", value)
            if coauthor:
                detected = agent_from_name(coauthor.group(1), coauthor.group(2))
                if detected:
                    result.add(detected)
    return result


def commits(path, since=None):
    """Enumerate commit lists; fail closed rather than silently truncating."""
    params = {"per_page": 100}
    if since is not None:
        params["since"] = since.isoformat().replace("+00:00", "Z")
    for page in range(1, 11):
        try:
            batch = api(path, {**params, "page": page})
        except EmptyRepositoryError as exc:
            if page != 1:
                raise RuntimeError(f"Unexpected empty repository after page 1: {path}") from exc
            print(f"Skipping empty Git repository in commit scan: {path}", file=sys.stderr)
            return
        if not isinstance(batch, list):
            raise RuntimeError(f"Invalid commit list response: {path}")
        yield from batch
        if len(batch) < 100:
            return
    raise RuntimeError(f"Commit scan incomplete: {path}")


def empty_agents():
    return {agent: dict(prs=0, commits=0, added=0, deleted=0, default_commits=0)
            for agent in AGENT_ORDER}


def collect(since):
    total = dict(prs=0, commits=0, added=0, deleted=0)
    agent_stats = empty_agents()
    inspected = 0
    active = set()
    identified_repos = set()
    branch_repos_scanned = 0
    for name in repos(since):
        inspected += 1
        for pr in prs(name, since):
            pr_path = f"/repos/{quote(OWNER)}/{quote(name)}/pulls/{int(pr['number'])}"
            detail = api(pr_path)
            if not all(isinstance(detail.get(k), int) for k in ("commits", "additions", "deletions")):
                raise RuntimeError(f"Missing stats: {name} #{pr['number']}")
            active.add(name)
            total["prs"] += 1
            for key, source in (("commits", "commits"), ("added", "additions"), ("deleted", "deletions")):
                total[key] += detail[source]
            agents = identified_pr_agents(pr)
            # Git trailers can identify Claude Code (and other agents) even when
            # the PR itself was created manually and has no agent label.
            for commit in commits(pr_path + "/commits"):
                agents.update(identified_commit_agents(commit))
            if agents:
                identified_repos.add(name)
            for agent in agents:
                stats = agent_stats[agent]
                stats["prs"] += 1
                for key, source in (("commits", "commits"), ("added", "additions"), ("deleted", "deletions")):
                    stats[key] += detail[source]

        # Profile README auto-updates every five minutes. Exclude this repo
        # from default-branch commit attribution to avoid self-inflating metrics.
        if name.lower() == AUTOMATED_PROFILE_REPO:
            continue
        branch_repos_scanned += 1
        for commit in commits(f"/repos/{quote(OWNER)}/{quote(name)}/commits", since):
            raw = commit.get("commit") or {}
            committer = (raw.get("committer") or {}).get("date")
            if committer and date(committer) < since:
                continue
            for agent in identified_commit_agents(commit):
                agent_stats[agent]["default_commits"] += 1
    return total, agent_stats, inspected, len(active), len(identified_repos), branch_repos_scanned


def render(since, now, total, agent_stats, inspected, active, identified, branch_repos):
    # This timestamp follows a fully successful API collection.
    utc_now = now.astimezone(timezone.utc)
    kyiv_now = utc_now.astimezone(ZoneInfo("Europe/Kyiv"))
    rows = []
    for agent in AGENT_ORDER:
        stats = agent_stats[agent]
        rows.append(
            f"| {AGENT_TITLES[agent]} | **{stats['prs']:,}** | {stats['commits']:,} "
            f"| {stats['default_commits']:,} | +{stats['added']:,} | −{stats['deleted']:,} |"
        )
    return "\n".join([
        f"**{since:%d %b} – {now:%d %b %Y} (UTC)** · Week to date (from Monday)",
        "",
        "| AI agent / activity | PRs | Commits in linked PRs | Marked default-branch commits | Lines added (PRs) | Lines removed (PRs) |",
        "|:--|--:|--:|--:|--:|--:|",
        *rows,
        f"| 📦 All accessible PR activity | **{total['prs']:,}** | {total['commits']:,} | — | +{total['added']:,} | −{total['deleted']:,} |",
        "",
        f"Recently active repos scanned: **{inspected}** · With new PRs: **{active}** "
        f"· With AI-marked PRs: **{identified}** · Default-branch commit scans: **{branch_repos}**.",
        "",
        f"**Last successful data refresh:** {utc_now:%d %b %Y, %H:%M:%S} UTC · {kyiv_now:%d %b %Y, %H:%M:%S %Z} (Kyiv)",
        "",
        "<sub>Only PRs opened this week in repositories accessible to the token are counted. "
        "AI attribution is conservative: explicit bot/branch/label/PR metadata or commit author, "
        "Co-Authored-By and AI-Tool trailers. The PR columns show whole PR totals, "
        "not uniquely AI-authored lines. A PR can appear in more than one AI row, "
        "and default-branch commits can also be in PRs; columns must not be added together. "
        "Default-branch commits use the week's commit timestamps; the auto-updating profile "
        "repository is excluded from this separate scan. Local IDE/chat assistance without "
        "Git markers cannot be detected, including ordinary claude.ai chats. "
        "Use PR labels codex / claude-code / copilot / cursor / gemini, "
        "or an AI-Tool: Claude Code (etc.) commit trailer, for reliable attribution. "
        "No models, tokens or session time are inferred. Private repository names and content are not displayed.</sub>",
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
        total, agent_stats, inspected, active, identified, branch_repos = collect(since)
        completed_at = datetime.now(timezone.utc)
        changed = update(render(since, completed_at, total, agent_stats, inspected, active, identified, branch_repos))
        print(f"AI agents: {agent_stats}; PR activity: {total}; repos scanned: {inspected}; updated: {changed}")
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
