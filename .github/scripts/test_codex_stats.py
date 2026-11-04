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

    def test_prs_total_and_codex_counted_separately(self):
        pr_codex = {"number": 4, "head": {"ref": "codex/feature"}}
        pr_other = {"number": 5, "head": {"ref": "feat/change"}}
        data = {
            "/repos/sunmeat/ai/pulls/4": {"commits": 3, "additions": 100, "deletions": 20},
            "/repos/sunmeat/ai/pulls/5": {"commits": 2, "additions": 25, "deletions": 5},
        }
        with (patch.object(codex_stats, "repos", return_value=iter(["ai"])),
              patch.object(codex_stats, "prs", return_value=iter([pr_codex, pr_other])),
              patch.object(codex_stats, "api", side_effect=lambda path: data[path])):
            total, ai, inspected, active, identified = codex_stats.collect(datetime.now(timezone.utc))
        self.assertEqual(total, {"prs": 2, "commits": 5, "added": 125, "deleted": 25})
        self.assertEqual(ai, {"prs": 1, "commits": 3, "added": 100, "deleted": 20})
        self.assertEqual((inspected, active, identified), (1, 1, 1))

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
