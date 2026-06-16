"""
Unit tests for the SecureDispatcher tool-execution gate (Layer 1).

Runnable on any OS. Verifies:
  - risk classification,
  - argument validation blocks injection payloads at the gate,
  - SAFE tools run without approval,
  - DANGEROUS tools are denied when no ask-callback is present,
  - an ask-callback that says "no" blocks; "yes" allows.
"""

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# secure_dispatch lives one level up from the alice_security package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

# Import the module under test from Alice_code.
_ALICE_CODE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ALICE_CODE)

from secure_dispatch import SecureDispatcher, RiskLevel  # noqa: E402


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestClassification(unittest.TestCase):
    def setUp(self):
        self.d = SecureDispatcher(ask_callback=None)

    def test_known_levels(self):
        self.assertEqual(self.d.classify("get_weather"), RiskLevel.SAFE)
        self.assertEqual(self.d.classify("open_application"), RiskLevel.SENSITIVE)
        self.assertEqual(self.d.classify("advanced_system_operations"), RiskLevel.DANGEROUS)

    def test_unknown_defaults_sensitive(self):
        self.assertEqual(self.d.classify("some_new_tool"), RiskLevel.SENSITIVE)


class TestArgValidation(unittest.TestCase):
    def setUp(self):
        self.d = SecureDispatcher(ask_callback=None)

    def test_injection_in_app_name_blocked(self):
        allowed, reason = run(self.d.authorize("open_application", {"app_name": "notepad & calc"}))
        self.assertFalse(allowed)
        self.assertIn("rejected", reason.lower())

    def test_bad_url_blocked(self):
        allowed, _ = run(self.d.authorize("open_browser",
                                          {"browser": "chrome", "url": "javascript:alert(1)"}))
        self.assertFalse(allowed)

    def test_clean_sensitive_allowed_by_policy(self):
        # No ask callback, sensitive auto-allow policy (validated input).
        allowed, _ = run(self.d.authorize("open_application", {"app_name": "notepad"}))
        self.assertTrue(allowed)


class TestApprovalFlow(unittest.TestCase):
    def test_safe_runs_without_ask(self):
        d = SecureDispatcher(ask_callback=None)
        allowed, _ = run(d.authorize("get_weather", {"city": "Delhi"}))
        self.assertTrue(allowed)

    def test_dangerous_denied_without_ask(self):
        d = SecureDispatcher(ask_callback=None, allow_dangerous_without_ask=False)
        allowed, reason = run(d.authorize("advanced_system_operations", {"operation": "development setup"}))
        self.assertFalse(allowed)

    def test_dangerous_allowed_when_user_says_yes(self):
        async def yes(_q):
            return True
        d = SecureDispatcher(ask_callback=yes)
        allowed, _ = run(d.authorize("advanced_system_operations", {"operation": "development setup"}))
        self.assertTrue(allowed)

    def test_dangerous_blocked_when_user_says_no(self):
        async def no(_q):
            return False
        d = SecureDispatcher(ask_callback=no)
        allowed, _ = run(d.authorize("advanced_system_operations", {"operation": "browser testing"}))
        self.assertFalse(allowed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
