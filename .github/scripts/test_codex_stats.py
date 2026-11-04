"""Offline regression tests for Codex/GitHub README stats."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import codex_stats


class StatsTests(unittest.TestCase):
    def test_identification_requires_explicit_codex_marker(self):
        self.assertTrue(codex_stats.is_codex({"head": {"ref": "codex/fix"}}))
        self.assertTrue(codex_stats.is_codex({"labels": [{"name": "Codex"}]}))
        self.assertTrue(codex_stats.is_codex({"user": {"login": "chatgpt-codex-connector[bot]"}}))
        self.assertFalse(codex_stats.is_codex({"title": "Add codex medieval theme", "head": {"ref": "feat/codex-medieval"}}))
        self.assertFalse(codex_stats.is_codex({"user": {"login": "sunmeat"}, "head": {"ref": "feat/japanese-ui"}}))

    def test_monday_utc_boundary(self):
        d = datetime(2026, 11, 5, 14, 30, tzinfo=timezone.utc)
        self.assertEqual(codex_stats.beginning_of_week(d), datetime(2026, 11, 2, tzinfo=timezone.utc))

    def test_agent_pr_attribution_not_plain_mentions(self):
        self.assertEqual(codex_stats.identified_pr_agents({
            "title": "Compare Claude and Cursor docs", "head": {"ref": "feature/claude-helper"}
        }), set())
        self.assertEqual(codex_stats.identified_pr_agents({
            "title": "Fix bug", "head": {"ref": "cursor/fix-bug"}
        }), {"cursor"})
        self.assertEqual(codex_stats.identified_pr_agents({
            "title": "Fix bug", "labels": [{"name": "claude-code"}]
        }), {"claude"})
        self.assertEqual(codex_stats.identified_pr_agents({
            "user": {"login": "copilot-swe-agent[bot]"}
        }), {"copilot"})
        self.assertEqual(codex_stats.identified_pr_agents({
            "body": "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
        }), {"claude"})
        self.assertEqual(codex_stats.identified_pr_agents({
            "head": {"ref": "gemini/add-tests"}
        }), {"gemini"})

    def test_commit_attribution_from_author_and_trailers(self):
        self.assertEqual(codex_stats.identified_commit_agents({
            "commit": {"author": {"name": "sunmeat"}, "message":
                "feat: lesson\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"}
        }), {"claude"})
        self.assertEqual(codex_stats.identified_commit_agents({
            "commit": {"author": {"name": "GitHub Copilot"}, "message": "fix"}
        }), {"copilot"})
        self.assertEqual(codex_stats.identified_commit_agents({
            "commit": {"author": {"name": "sunmeat"}, "message": "feat: parser\n\nAI-Tool: Gemini CLI"}
        }), {"gemini"})
        self.assertEqual(codex_stats.identified_commit_agents({
            "commit": {"author": {"name": "sunmeat"}, "message":
                "Improve Claude Code and GitHub Copilot docs"}
        }), set())
        self.assertEqual(codex_stats.identified_commit_agents({
            "commit": {"author": {"name": "Claude Smith", "email": "claude@personal.example"}, "message": "fix"}
        }), set())

    def test_prs_commits_and_ai_counts(self):
        pr_codex = {"number": 4, "head": {"ref": "codex/feature"}}
        pr_claude = {"number": 5, "head": {"ref": "feat/change"}}
        counts = {
            "/repos/sunmeat/ai/pulls/4": {"commits": 3, "additions": 100, "deletions": 20},
            "/repos/sunmeat/ai/pulls/5": {"commits": 2, "additions": 25, "deletions": 5},
        }
        claude_commit = {"commit": {"author": {"name": "sunmeat"}, "message":
            "feat: new slides\n\nCo-Authored-By: Claude Code <noreply@anthropic.com>"}}
        def fake_api(path, params=None):
            if path in counts:
                return counts[path]
            if path == "/repos/sunmeat/ai/pulls/5/commits":
                return [claude_commit]
            if path == "/repos/sunmeat/ai/commits":
                return [claude_commit]
            return []
        with (patch.object(codex_stats, "repos", return_value=iter(["ai"])),
              patch.object(codex_stats, "prs", return_value=iter([pr_codex, pr_claude])),
              patch.object(codex_stats, "api", side_effect=fake_api)):
            total, agents, inspected, active, identified, branch_repos = codex_stats.collect(
                datetime(2026, 11, 2, tzinfo=timezone.utc))
        self.assertEqual(total, {"prs": 2, "commits": 5, "added": 125, "deleted": 25})
        self.assertEqual(agents["codex"]["prs"], 1)
        self.assertEqual(agents["codex"]["commits"], 3)
        self.assertEqual(agents["claude"]["prs"], 1)
        self.assertEqual(agents["claude"]["commits"], 2)
        self.assertEqual(agents["claude"]["default_commits"], 1)
        self.assertEqual((inspected, active, identified, branch_repos), (1, 1, 1, 1))

    def test_profile_repo_default_branch_excluded(self):
        def fake_api(path, params=None):
            if "/commits" in path:
                raise AssertionError("Profile commits must not be scanned")
            return []
        with (patch.object(codex_stats, "repos", return_value=iter(["sunmeat"])),
              patch.object(codex_stats, "prs", return_value=iter([])),
              patch.object(codex_stats, "api", side_effect=fake_api)):
            total, agents, inspected, active, identified, branch_repos = codex_stats.collect(
                datetime(2026, 11, 2, tzinfo=timezone.utc))
        self.assertEqual(branch_repos, 0)
        self.assertEqual(agents["claude"]["default_commits"], 0)

    def test_last_successful_refresh_timestamp_in_utc_and_kyiv(self):
        counters = {"prs": 0, "commits": 0, "added": 0, "deleted": 0}
        agents = codex_stats.empty_agents()
        winter = datetime(2026, 11, 4, 8, 43, 12, tzinfo=timezone.utc)
        summer = datetime(2026, 7, 1, 8, 3, 0, tzinfo=timezone.utc)
        winter_section = codex_stats.render(
            codex_stats.beginning_of_week(winter), winter, counters, agents, 7, 1, 0, 6
        )
        summer_section = codex_stats.render(
            codex_stats.beginning_of_week(summer), summer, counters, agents, 7, 1, 0, 6
        )
        self.assertIn(
            "**Last successful data refresh:** 04 Nov 2026, 08:43:12 UTC · 04 Nov 2026, 10:43:12 EET (Kyiv)",
            winter_section,
        )
        self.assertIn(
            "**Last successful data refresh:** 01 Jul 2026, 08:03:00 UTC · 01 Jul 2026, 11:03:00 EEST (Kyiv)",
            summer_section,
        )

    def test_preserves_wakatime_section(self):
        original = ("<!--START_SECTION:waka-->\nwakatime\n<!--END_SECTION:waka-->\n"
                    "<!--START_SECTION:codex-github-->\nold\n<!--END_SECTION:codex-github-->\n")
        with tempfile.TemporaryDirectory() as directory:
            readme = Path(directory) / "README.md"
            readme.write_text(original, encoding="utf-8")
            with patch.object(codex_stats, "README", readme):
                self.assertTrue(codex_stats.update("new stats"))
                self.assertFalse(codex_stats.update("new stats"))
            new = readme.read_text(encoding="utf-8")
        self.assertIn("<!--START_SECTION:waka-->\nwakatime\n<!--END_SECTION:waka-->", new)
        self.assertIn("<!--START_SECTION:codex-github-->\nnew stats\n<!--END_SECTION:codex-github-->", new)


if __name__ == "__main__":
    unittest.main()
