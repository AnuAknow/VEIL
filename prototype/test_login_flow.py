import unittest
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from login_flow import Approval, LoginRequest, OfflineLoginGate


class LoginFlowTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.request = LoginRequest('synthetic-qa', 'mock://staging/login')
        self.approval = Approval('granted', self.request, self.now, self.now + timedelta(minutes=5), 'v1')
        self.gate = OfflineLoginGate(lambda _: self.approval, lambda: self.now)

    def test_approved_single_use(self):
        a = self.gate.evaluate(self.request)
        self.assertEqual(a['decision'], 'proceed')
        self.assertEqual(len(self.gate.mock_calls), 0)
        result = self.gate.execute_mock(a['assessment_id'], self.request)
        self.assertTrue(result['mock_execution_performed'])
        self.assertFalse(result['execution_performed'])
        replay = self.gate.execute_mock(a['assessment_id'], self.request)
        self.assertEqual(replay['decision'], 'hold')
        self.assertEqual(len(self.gate.mock_calls), 1)

    def test_unknown_recovered_with_verified_record(self):
        approval = self.approval
        self.approval = None
        unknown = self.gate.evaluate(self.request)
        self.assertEqual(unknown['decision'], 'ask')
        self.gate.execute_mock(unknown['assessment_id'], self.request)
        self.assertEqual(len(self.gate.mock_calls), 0)
        self.approval = approval
        fresh = self.gate.evaluate(self.request, predecessor=unknown['assessment_id'])
        self.assertEqual(fresh['decision'], 'proceed')
        self.assertEqual(fresh['predecessor_id'], unknown['assessment_id'])
        self.assertEqual(self.gate.history[0]['decision'], 'ask')
        self.gate.execute_mock(fresh['assessment_id'], self.request)
        self.assertEqual(len(self.gate.mock_calls), 1)

    def test_multiple_grants_cannot_bypass_approval_budget(self):
        first = self.gate.evaluate(self.request)
        second = self.gate.evaluate(self.request)
        self.gate.execute_mock(first['assessment_id'], self.request)
        rejected = self.gate.execute_mock(second['assessment_id'], self.request)
        self.assertEqual(rejected['reason_code'], 'APPROVAL_BUDGET_EXHAUSTED')
        fresh = self.gate.evaluate(self.request)
        self.assertEqual(fresh['decision'], 'hold')
        self.assertEqual(len(self.gate.mock_calls), 1)

    def test_denial_precedes_missing_time(self):
        self.approval = replace(self.approval, authorization='denied', expires_at=None)
        result = self.gate.evaluate(self.request)
        self.assertEqual(result['reason_code'], 'AUTHORIZATION_DENIED')
        self.gate.execute_mock(result['assessment_id'], self.request)
        self.assertEqual(len(self.gate.mock_calls), 0)

    def test_exact_expiry_prevents_execution(self):
        a = self.gate.evaluate(self.request)
        self.now = self.approval.expires_at
        result = self.gate.execute_mock(a['assessment_id'], self.request)
        self.assertEqual(result['reason_code'], 'OUTSIDE_APPROVED_WINDOW')
        self.assertEqual(len(self.gate.mock_calls), 0)

    def test_changed_request_prevents_execution(self):
        for change in [dict(principal='other'), dict(target='production'), dict(attempts=2), dict(method='password_cycling')]:
            a = self.gate.evaluate(self.request)
            result = self.gate.execute_mock(a['assessment_id'], replace(self.request, **change))
            self.assertEqual(result['reason_code'], 'REQUEST_CHANGED')
        self.assertEqual(len(self.gate.mock_calls), 0)

    def test_revoked_approval_prevents_execution(self):
        a = self.gate.evaluate(self.request)
        self.approval = replace(self.approval, authorization='denied')
        result = self.gate.execute_mock(a['assessment_id'], self.request)
        self.assertEqual(result['decision'], 'hold')
        self.assertEqual(len(self.gate.mock_calls), 0)

    def test_changed_revision_requires_new_evaluation(self):
        a = self.gate.evaluate(self.request)
        self.approval = replace(self.approval, revision='v2')
        result = self.gate.execute_mock(a['assessment_id'], self.request)
        self.assertEqual(result['reason_code'], 'APPROVAL_OR_POLICY_CHANGED')
        self.assertEqual(len(self.gate.mock_calls), 0)

    def test_unavailable_source_prevents_execution(self):
        a = self.gate.evaluate(self.request)
        def unavailable(_):
            raise OSError('private connector details')
        self.gate.approval_source = unavailable
        result = self.gate.execute_mock(a['assessment_id'], self.request)
        self.assertEqual(result['reason_code'], 'REVALIDATION_UNAVAILABLE')
        self.assertNotIn('private', str(result))
        self.assertEqual(len(self.gate.mock_calls), 0)

    def test_policy_change_prevents_execution(self):
        a = self.gate.evaluate(self.request)
        with patch('login_flow.load_policy', return_value={'version': 'changed', 'rules': []}):
            result = self.gate.execute_mock(a['assessment_id'], self.request)
        self.assertEqual(result['decision'], 'hold')
        self.assertEqual(len(self.gate.mock_calls), 0)

    def test_untrusted_returned_decision_cannot_grant_permission(self):
        self.approval = None
        a = self.gate.evaluate(self.request)
        a['decision'] = 'proceed'
        result = self.gate.execute_mock(a['assessment_id'], self.request)
        self.assertEqual(result['decision'], 'hold')
        self.assertEqual(self.gate.history[0]['decision'], 'ask')
        self.assertEqual(len(self.gate.mock_calls), 0)

    def test_invalid_scope_budget_and_clock(self):
        for request in [replace(self.request, attempts=True), replace(self.request, attempts=2),
                        replace(self.request, target='production')]:
            self.assertEqual(self.gate.evaluate(request)['decision'], 'hold')
        self.approval = replace(self.approval, starts_at=datetime(2026, 1, 1))
        self.assertEqual(self.gate.evaluate(self.request)['decision'], 'ask')
        self.assertEqual(len(self.gate.mock_calls), 0)
