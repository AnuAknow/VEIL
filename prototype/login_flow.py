"""Offline login gate. Synthetic authority and mock execution only; no network I/O."""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import hashlib
import json
import uuid

from core import load_policy


@dataclass(frozen=True)
class LoginRequest:
    principal: str
    target: str
    method: str = 'negative_login'
    attempts: int = 1


@dataclass(frozen=True)
class Approval:
    authorization: str  # granted / denied / unknown; supplied by a trusted adapter
    request: LoginRequest
    starts_at: datetime
    expires_at: datetime
    revision: str


def aware(value):
    return isinstance(value, datetime) and value.utcoffset() is not None


class OfflineLoginGate:
    """Single-process simulator; approval_source is trusted fixture code, never model output.

    A grant is single-use and bound to request, approval revision and policy digest.
    These in-memory grants are NOT production credentials or durable audit records.
    """
    def __init__(self, approval_source, clock=None):
        self.approval_source = approval_source
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.history = []
        self.mock_calls = []
        self._grants = {}
        self._used_approvals = set()

    def _check(self, request):
        policy = load_policy()
        digest = hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()
        evidence = {'policy_version': policy['version'], 'policy_sha256': digest}
        if not isinstance(request, LoginRequest) or any(
            not isinstance(value, str) or not value.strip()
            for value in (request.principal, request.target, request.method)
        ):
            return 'hold', 'INVALID_REQUEST', None, evidence
        if request.method != 'negative_login' or type(request.attempts) is not int or request.attempts != 1:
            return 'hold', 'METHOD_OR_BUDGET_VIOLATION', None, evidence
        # This slice only permits one synthetic negative-login attempt against this mock target.
        if request.target != 'mock://staging/login':
            return 'hold', 'TARGET_OUT_OF_SCOPE', None, evidence
        approval = self.approval_source(request.principal)
        if approval is None:
            return 'ask', 'AUTHORIZATION_UNKNOWN', None, evidence
        if not isinstance(approval, Approval):
            return 'hold', 'INVALID_AUTHORITY_RECORD', None, evidence
        evidence['approval_revision'] = approval.revision
        if approval.authorization == 'denied':
            return 'hold', 'AUTHORIZATION_DENIED', approval, evidence
        if approval.authorization == 'unknown':
            return 'ask', 'AUTHORIZATION_UNKNOWN', approval, evidence
        if approval.authorization != 'granted':
            return 'hold', 'INVALID_AUTHORITY_RECORD', approval, evidence
        if request != approval.request:
            return 'hold', 'APPROVED_SCOPE_MISMATCH', approval, evidence
        now = self.clock()
        if not all(aware(v) for v in (now, approval.starts_at, approval.expires_at)) or not approval.revision:
            return 'ask', 'AUTHORITY_TIME_OR_REVISION_MISSING', approval, evidence
        if approval.starts_at >= approval.expires_at:
            return 'hold', 'INVALID_APPROVAL_WINDOW', approval, evidence
        if not approval.starts_at <= now < approval.expires_at:
            return 'hold', 'OUTSIDE_APPROVED_WINDOW', approval, evidence
        if (request.principal, approval.revision) in self._used_approvals:
            return 'hold', 'APPROVAL_BUDGET_EXHAUSTED', approval, evidence
        return 'proceed', 'APPROVED_SYNTHETIC_ATTEMPT', approval, evidence

    def _record(self, decision, reason, evidence=None, predecessor=None, performed=False):
        record = {'assessment_id': uuid.uuid4().hex, 'predecessor_id': predecessor,
                  'mode': 'offline_mock', 'decision': decision, 'reason_code': reason,
                  'question': 'Can the trusted approval source verify current permission and its scope?' if decision == 'ask' else None,
                  'mock_execution_performed': performed, 'execution_performed': False,
                  **(evidence or {})}
        self.history.append(record.copy())
        return record

    def evaluate(self, request, predecessor=None):
        try:
            decision, reason, approval, evidence = self._check(request)
        except Exception:
            return self._record('hold', 'EVALUATION_UNAVAILABLE', predecessor=predecessor)
        record = self._record(decision, reason, evidence, predecessor)
        if decision == 'proceed':
            self._grants[record['assessment_id']] = (request, approval, evidence['policy_sha256'])
        return record

    def execute_mock(self, assessment_id, request):
        # Consume even rejected grants: retries require deliberate fresh evaluation.
        grant = self._grants.pop(assessment_id, None)
        if grant is None:
            return self._record('hold', 'NO_UNUSED_GRANT', predecessor=assessment_id)
        original, original_approval, digest = grant
        if request != original:
            return self._record('hold', 'REQUEST_CHANGED', predecessor=assessment_id)
        try:
            decision, reason, approval, evidence = self._check(request)
        except Exception:
            return self._record('hold', 'REVALIDATION_UNAVAILABLE', predecessor=assessment_id)
        if decision != 'proceed':
            return self._record(decision, reason, evidence, assessment_id)
        if approval != original_approval or evidence['policy_sha256'] != digest:
            return self._record('hold', 'APPROVAL_OR_POLICY_CHANGED', evidence, assessment_id)
        self._used_approvals.add((request.principal, approval.revision))
        self.mock_calls.append(request)
        return self._record('proceed', 'MOCK_ATTEMPT_RECORDED', evidence, assessment_id, performed=True)


def demo():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    request = LoginRequest('synthetic-qa', 'mock://staging/login')
    state = {'approval': None, 'now': now}
    gate = OfflineLoginGate(lambda _: state['approval'], lambda: state['now'])
    missing = gate.evaluate(request)
    state['approval'] = Approval('granted', request, now, now + timedelta(minutes=5), 'approval-1')
    approved = gate.evaluate(request, predecessor=missing['assessment_id'])
    gate.execute_mock(approved['assessment_id'], request)
    state['approval'] = Approval('granted', request, now, now + timedelta(minutes=5), 'approval-expiry-test')
    expiring = gate.evaluate(request)
    state['now'] = now + timedelta(minutes=5)
    gate.execute_mock(expiring['assessment_id'], request)
    state['approval'] = Approval('denied', request, now, now + timedelta(minutes=5), 'approval-2')
    gate.evaluate(request)
    print(json.dumps({'description': 'Synthetic fixtures only. No real login or AI call.',
                      'mock_call_count': len(gate.mock_calls), 'history': gate.history}, indent=2))


if __name__ == '__main__':
    demo()
