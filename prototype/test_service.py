import os
import unittest
from unittest.mock import patch, Mock
from service import review, demo
class ServiceTests(unittest.TestCase):
    def test_live_contract(self):
        for decision in ("proceed","ask","hold"):
            factory=lambda: lambda *_: {"decision":decision,"reason":"Test","rule_ids":["VEIL-005"],"question":"Which evidence?" if decision=="ask" else None}
            r=review("Review a report","Supplied context",factory)
            self.assertEqual(r["status"],"evaluated")
            self.assertEqual(r["decision"],decision)
            self.assertFalse(r["eligible_to_execute"])
            self.assertFalse(r["authorization_verified"])
    def test_missing_configuration(self):
        with patch.dict(os.environ,{},clear=True):
            r=review("Test","Context")
        self.assertEqual(r["status"],"error")
        self.assertEqual(r["decision"],"hold")
    def test_invalid_live_response(self):
        r=review("Test","Context",lambda:lambda *_: {"decision":"proceed","eligible_to_execute":True})
        self.assertEqual(r["status"],"error")
        self.assertFalse(r["eligible_to_execute"])
    def test_demo_labeled_and_nonexecuting(self):
        for id,d in (("P01","proceed"),("A01","ask"),("H01","hold")):
            r=demo(id)
            self.assertEqual(r["decision"],d)
            self.assertEqual(r["mode"],"fixture_demo")
            self.assertFalse(r["eligible_to_execute"])
    def test_invalid_input_never_calls_provider(self):
        def fail(): self.fail("Provider invoked")
        for action in ("","x"*20001,None):
            self.assertEqual(review(action,"context",fail)["status"],"error")

    def test_null_policy_returns_type_error_hold(self):
        factory = Mock()
        with patch("service.load_policy", return_value=None):
            r = review("Test", "Context", factory)
        self.assertEqual(r["status"], "error")
        self.assertEqual(r["decision"], "hold")
        self.assertIn("invalid type", r["reason"])
        self.assertIsNone(r["policy_sha256"])
        self.assertIsNone(r["policy_id"])
        self.assertIsNone(r["policy_version"])
        self.assertFalse(r["eligible_to_execute"])
        factory.assert_not_called()

    def test_policy_file_failures_hold_without_provider(self):
        for contents in ("null", "{", '{"rules": []}'):
            with self.subTest(contents=contents):
                factory = Mock()
                with patch("core.Path.read_text", return_value=contents):
                    r = review("Test", "Context", factory)
                self.assertEqual((r["status"], r["decision"]), ("error", "hold"))
                self.assertIsNone(r["policy_sha256"])
                factory.assert_not_called()
        factory = Mock()
        with patch("core.Path.read_text", side_effect=FileNotFoundError("private path")):
            r = review("Test", "Context", factory)
        self.assertEqual((r["status"], r["decision"]), ("error", "hold"))
        self.assertNotIn("private path", r["reason"])
        factory.assert_not_called()
