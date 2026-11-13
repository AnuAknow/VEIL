import unittest
import io
import json
from contextlib import redirect_stderr, redirect_stdout
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

    def test_streaming_transport_and_final_validation(self):
        import httpx
        from langchain_openai import ChatOpenAI

        requests = []

        def respond(request):
            body = json.loads(request.content)
            requests.append(body)
            self.assertTrue(body["stream"])
            self.assertEqual(body["response_format"]["type"], "json_schema")
            # The second response is complete JSON but violates the ask contract.
            decision = "proceed" if len(requests) == 1 else "ask"
            parts = ['{"decision":"' + decision + '",', '"reason":"Supported",', '"question":null}']
            chunks = []
            for part in parts:
                chunks.append("data: " + json.dumps({
                    "id": "test", "object": "chat.completion.chunk", "created": 0,
                    "model": "test-model", "choices": [{"index": 0,
                    "delta": {"role": "assistant", "content": part}, "finish_reason": None}]
                }) + "\n\n")
            chunks.append("data: " + json.dumps({
                "id": "test", "object": "chat.completion.chunk", "created": 0,
                "model": "test-model", "choices": [{"index": 0,
                "delta": {}, "finish_reason": "stop"}]
            }) + "\n\ndata: [DONE]\n\n")
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, text="".join(chunks))

        stderr, stdout = io.StringIO(), io.StringIO()
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            runner = ChatOpenAI(model="test-model", api_key="offline-test-only", http_client=client,
                                streaming=True, max_retries=0).with_structured_output(Judgment, method="json_schema")
            with redirect_stderr(stderr), redirect_stdout(stdout):
                report = compare(runner, "test-model", stream=True)
        self.assertEqual(len(requests), 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn('"reason":"Supported"', stderr.getvalue())
        self.assertIn("not yet validated", stderr.getvalue())
        self.assertEqual(report["results"]["control"]["status"], "evaluated", report)
        self.assertEqual(report["results"]["veil"]["status"], "error")

    def test_interrupted_stream_is_not_a_decision(self):
        def interrupted(messages, config):
            config["callbacks"][0].on_llm_new_token('{"decision":"proceed"')
            raise TimeoutError()
        runner = Mock()
        runner.invoke.side_effect = interrupted
        with redirect_stderr(io.StringIO()):
            report = compare(runner, "test-model", stream=True)
        for result in report["results"].values():
            self.assertEqual(result, {"status": "error", "error_type": "TimeoutError"})
