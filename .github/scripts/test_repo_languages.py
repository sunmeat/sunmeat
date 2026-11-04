"""Regression tests for complete GitHub language inventory and README rendering."""
import tempfile
import unittest
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import repo_languages as lang


class RepoLanguageTests(unittest.TestCase):
    def test_top_ten_and_percentages_use_all_languages(self):
        totals = Counter({f"L{n:02d}": 1000*n for n in range(1, 13)})
        counts = Counter({name: 1 for name in totals})
        block = lang.render(totals, counts, 12, 12, 2, 1,
                            datetime(2026, 11, 4, 9, 15, 20, tzinfo=timezone.utc))
        self.assertLess(block.index("| L12 |"), block.index("| L11 |"))
        self.assertNotIn("| L01 |", block)
        self.assertNotIn("| L02 |", block)
        self.assertIn("**15.38%**", block)
        self.assertIn("**Other 2 languages:** 3.85%", block)
        self.assertIn("**Languages found:** 12", block)
        self.assertIn("04 Nov 2026, 11:15:20 EET (Kyiv)", block)

    def test_summer_timezone_and_single_language(self):
        block = lang.render(Counter({"C#": 500}), Counter({"C#": 1}), 1, 1, 0, 0,
                            datetime(2026, 7, 1, 12, tzinfo=timezone.utc))
        self.assertIn("**100.00%**", block)
        self.assertIn("01 Jul 2026, 15:00:00 EEST (Kyiv)", block)

    def test_aggregates_all_languages_and_counts_repositories_per_language(self):
        repos = [
            {"name": "a", "private": False, "fork": False},
            {"name": "b", "private": True, "fork": True},
            {"name": "empty", "private": False, "fork": False}
        ]
        data = {"/repos/sunmeat/a/languages": {"C#": 300, "JS": 10},
                "/repos/sunmeat/b/languages": {"C#": 100, "Python": 400},
                "/repos/sunmeat/empty/languages": {}}
        with patch.object(lang, "owned_repositories", return_value=repos), \
             patch.object(lang, "api", side_effect=lambda path: data[path]):
            total, counts, scanned, nonempty, private, forks = lang.collect()
        self.assertEqual(total, Counter({"C#": 400, "JS": 10, "Python": 400}))
        self.assertEqual(counts, Counter({"C#": 2, "JS": 1, "Python": 1}))
        self.assertEqual((scanned, nonempty, private, forks), (3, 2, 1, 1))

    def test_public_and_private_are_merged_and_other_users_excluded(self):
        a = {"name": "public", "owner": {"login": "sunmeat"}}
        b = {"name": "private", "owner": {"login": "sunmeat"}}
        c = {"name": "elsewhere", "owner": {"login": "elsewhere"}}
        def paged_mock(path, params):
            if path.startswith("/users/"):
                return iter([a, c])
            return iter([a, b])
        with patch.object(lang, "TOKEN", "dummy"), patch.object(lang, "paged", side_effect=paged_mock):
            names = [repo["name"] for repo in lang.owned_repositories()]
        self.assertEqual(names, ["private", "public"])

    def test_pagination(self):
        first = [{"name": str(n)} for n in range(100)]
        with patch.object(lang, "api", side_effect=lambda path, params: first if params["page"] == 1 else [{"name": "final"}]):
            self.assertEqual(len(list(lang.paged("/test", {}))), 101)

    def test_readme_edit_preserves_wakatime_and_ai(self):
        example = ("<!--START_SECTION:waka-->\nwaka\n<!--END_SECTION:waka-->\n"
                   "<!--START_SECTION:repo-languages-->\nold\n<!--END_SECTION:repo-languages-->\n"
                   "<!--START_SECTION:codex-github-->\nai\n<!--END_SECTION:codex-github-->\n")
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "README.md"
            file.write_text(example, encoding="utf-8")
            with patch.object(lang, "README", file):
                self.assertTrue(lang.update("new report"))
                self.assertFalse(lang.update("new report"))
            actual = file.read_text(encoding="utf-8")
        self.assertIn("waka", actual)
        self.assertIn("new report", actual)
        self.assertIn("ai", actual)


if __name__ == "__main__":
    unittest.main()
