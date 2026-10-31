import os
import unittest
from unittest.mock import patch
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
