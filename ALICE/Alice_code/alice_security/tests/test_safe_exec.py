"""
Regression tests for safe_exec helpers that DON'T require Windows.

Focus: `search_files` is the pure-Python replacement for the old
`dir "<loc>" /s /b | findstr "<query>"` shell pipeline. These tests prove it
finds files correctly AND that injection payloads cannot escape (there is no
shell to escape into — we assert behavior, not just absence).
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from alice_security import search_files, SecurityValidationError  # noqa: E402
from alice_security.safe_exec import _IS_WINDOWS  # noqa: E402


class TestSearchFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="alice_sec_test_")
        # Create a small tree
        open(os.path.join(self.tmp, "report.pdf"), "w").close()
        open(os.path.join(self.tmp, "notes.txt"), "w").close()
        sub = os.path.join(self.tmp, "sub")
        os.makedirs(sub)
        open(os.path.join(sub, "budget_report.xlsx"), "w").close()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_finds_by_substring(self):
        results = search_files("report", self.tmp)
        names = sorted(os.path.basename(r) for r in results)
        self.assertEqual(names, ["budget_report.xlsx", "report.pdf"])

    def test_finds_by_extension_fragment(self):
        results = search_files(".txt", self.tmp)
        self.assertEqual([os.path.basename(r) for r in results], ["notes.txt"])

    def test_no_match_returns_empty(self):
        self.assertEqual(search_files("zzz_nomatch", self.tmp), [])

    def test_injection_payload_is_inert(self):
        # The classic payload: with a shell this would delete files. Here it is
        # simply a (non-matching) search string. Nothing is executed, the tree
        # is intact afterwards.
        payload = '*.txt" & del /s . &'
        results = search_files(payload, self.tmp)  # treated as literal text
        self.assertEqual(results, [])
        # Files must still exist — proof nothing was executed.
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "notes.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "report.pdf")))

    def test_rejects_newline_query(self):
        with self.assertRaises(SecurityValidationError):
            search_files("a\nb", self.tmp)

    def test_rejects_nonexistent_location(self):
        with self.assertRaises(SecurityValidationError):
            search_files("x", "/no/such/dir/xyz123")

    def test_respects_max_results(self):
        for i in range(10):
            open(os.path.join(self.tmp, f"bulk_{i}.dat"), "w").close()
        results = search_files("bulk", self.tmp, max_results=3)
        self.assertEqual(len(results), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
