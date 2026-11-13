import unittest
from types import SimpleNamespace
from request_control import RequestController
from compare_live import compare, Judgment
from unittest.mock import Mock


class Clock:
    def __init__(self):
        self.now = 0
        self.delays = []
    def time(self):
        return self.now
    def sleep(self, delay):
        self.delays.append(delay)
        self.now += delay


class ProviderError(Exception):
    def __init__(self, code, headers=None, kind=None):
        self.status_code = 429
        self.code = code
        self.body = {'code': code, 'type': kind, 'message': 'DO NOT LOG SECRET'}
        self.response = SimpleNamespace(headers=headers or {})


class RequestControlTests(unittest.TestCase):
    def setup_controller(self, **kwargs):
        self.clock = Clock()
        return RequestController(clock=self.clock.time, sleep=self.clock.sleep,
                                 wall_clock=lambda: 0, jitter=lambda: .5, **kwargs)

    def test_start_spacing_across_arms(self):
        c = self.setup_controller(interval=3)
        starts = []
        def operation(attempt):
            starts.append(self.clock.now)
            self.clock.now += 1
            return 'ok'
        c.call(operation)
        _, metrics = c.call(operation)
        self.assertEqual(starts, [0, 3])
        self.assertEqual(metrics['attempts'][0]['delay_seconds'], 2)

    def test_backoff_jitter_and_retry_after(self):
        c = self.setup_controller(interval=0)
        op = Mock(side_effect=[ProviderError('rate_limit_exceeded'),
                              ProviderError('rate_limit_exceeded', {'retry-after': '7'}), 'ok'])
        answer, metrics = c.call(op)
        self.assertEqual(answer, 'ok')
        self.assertEqual(self.clock.delays, [1.5, 7])
        self.assertEqual(len(metrics['attempts']), 3)

    def test_http_date_and_milliseconds(self):
        for headers, expected in [({'retry-after': 'Thu, 01 Jan 1970 00:00:10 GMT'}, 10),
                                  ({'retry-after-ms': '3500'}, 3.5)]:
            c = self.setup_controller(interval=0)
            c.call(Mock(side_effect=[ProviderError('slow_down', headers), 'ok']))
            self.assertEqual(self.clock.delays, [expected])

    def test_quota_stops_remaining_arm_without_leaking_body(self):
        c = self.setup_controller()
        runner = Mock()
        runner.invoke.side_effect = ProviderError('insufficient_quota')
        report = compare(runner, 'offline', controller=c)
        self.assertEqual(runner.invoke.call_count, 1)
        self.assertEqual(report['results']['veil']['status'], 'skipped')
        self.assertEqual(report['request_metrics']['control']['http_status'], 429)
        self.assertNotIn('SECRET', str(report))
        self.assertEqual(self.clock.delays, [])

    def test_quota_type_takes_precedence_over_transient_code(self):
        c = self.setup_controller()
        op = Mock(side_effect=ProviderError('rate_limit_exceeded', kind='insufficient_quota'))
        _, metrics = c.call(op)
        self.assertEqual(op.call_count, 1)
        self.assertEqual(metrics['category'], 'quota_or_billing')

    def test_exhausted_budget_stops_more_calls(self):
        c = self.setup_controller(interval=0, retries=1)
        op = Mock(side_effect=ProviderError('rate_limit_exceeded'))
        c.call(op)
        _, metrics = c.call(op)
        self.assertEqual(op.call_count, 2)
        self.assertEqual(metrics['stop_reason'], 'retry_budget_exhausted')

    def test_long_provider_delay_never_retried_early(self):
        c = self.setup_controller(max_wait=5)
        op = Mock(side_effect=ProviderError('rate_limit_exceeded', {'retry-after': '60'}))
        _, metrics = c.call(op)
        self.assertEqual(op.call_count, 1)
        self.assertEqual(self.clock.delays, [])
        self.assertEqual(metrics['stop_reason'], 'retry_delay_exceeds_budget')

    def test_unknown_429_and_timeout_not_retried(self):
        for exc in [ProviderError('unknown'), TimeoutError()]:
            c = self.setup_controller()
            op = Mock(side_effect=exc)
            c.call(op)
            self.assertEqual(op.call_count, 1)

    def test_invalid_output_not_retried(self):
        c = self.setup_controller(interval=0)
        runner = Mock()
        runner.invoke.return_value = Judgment(decision='ask', reason='Need evidence', question=None)
        report = compare(runner, 'offline', controller=c)
        self.assertEqual(runner.invoke.call_count, 2)
        self.assertTrue(all(r['status'] == 'error' for r in report['results'].values()))

    def test_invalid_settings(self):
        for kwargs in [{'interval': float('nan')}, {'interval': -1}, {'interval': 61},
                       {'retries': -1}, {'retries': 6}, {'max_wait': float('inf')}]:
            with self.assertRaises(ValueError):
                self.setup_controller(**kwargs)
