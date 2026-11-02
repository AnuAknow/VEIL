import unittest
from unittest.mock import Mock

from compare_live import Judgment, compare


class PilotTests(unittest.TestCase):
    def test_only_policy_changes_and_errors_remain_visible(self):
        runner = Mock()
        runner.invoke.side_effect = [TimeoutError(), Judgment(decision="ask", reason="Missing evidence", question="Which receipt?")]
        report = compare(runner, "test-model")
        control, veil = [call.args[0] for call in runner.invoke.call_args_list]
        self.assertEqual(control[1], veil[1])
        self.assertTrue(veil[0][1].startswith(control[0][1] + "\nPolicy: "))
        self.assertNotIn("VEIL-005", control[0][1])
        self.assertIn("VEIL-005", veil[0][1])
        self.assertEqual(report["results"]["control"], {"status": "error", "error_type": "TimeoutError"})
        self.assertEqual(report["results"]["veil"]["question"], "Which receipt?")
