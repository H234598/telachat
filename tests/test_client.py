from __future__ import annotations

import json
import threading
import unittest
from unittest import mock
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar

from telachat.client import (
    ChatResult,
    OpenAICompatClient,
    TokenUsage,
    format_token_usage,
    token_usage_record,
)
from telachat.config import Profile


class FakeOpenAIHandler(BaseHTTPRequestHandler):
    requests: ClassVar[list[dict[str, object]]] = []

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/v1/models":
            self._json({"object": "list", "data": [{"id": "demo-model"}]})
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        self.requests.append(body)
        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for payload in [
                {"choices": [{"delta": {"role": "assistant"}, "finish_reason": None}]},
                {"choices": [{"delta": {"content": "Hel"}, "finish_reason": None}]},
                {"choices": [{"delta": {"content": "lo"}, "finish_reason": None}]},
                {"choices": [{"delta": {}, "finish_reason": "stop"}]},
            ]:
                self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode("utf-8"))
            self.wfile.write(b"data: [DONE]\n\n")
            return
        self._json(
            {
                "choices": [
                    {"message": {"role": "assistant", "content": "Hello"}, "index": 0}
                ],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 2,
                    "total_tokens": 5,
                    "prompt_tokens_details": {"cached_tokens": 1},
                    "completion_tokens_details": {"reasoning_tokens": 1},
                },
            }
        )

    def _json(self, payload: dict[str, object]) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class ClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenAIHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}/v1"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.thread.join(timeout=5)
        cls.server.server_close()

    def setUp(self) -> None:
        FakeOpenAIHandler.requests.clear()

    def profile(self, *, stream: bool = False) -> Profile:
        return Profile(
            name="test",
            label="Test",
            base_url=self.base_url,
            api_key="test-key",
            model="demo-model",
            timeout_seconds=5,
            stream=stream,
        )

    def test_list_models(self) -> None:
        client = OpenAICompatClient(self.profile())
        self.assertEqual(client.list_models(), ["demo-model"])

    def test_non_stream_chat(self) -> None:
        client = OpenAICompatClient(self.profile(stream=False))
        result = client.chat([{"role": "user", "content": "Hi"}])
        self.assertIsInstance(result, ChatResult)
        assert isinstance(result, ChatResult)
        self.assertEqual(result.content, "Hello")
        self.assertEqual(
            result.usage,
            TokenUsage(
                input_tokens=3,
                output_tokens=2,
                total_tokens=5,
                cached_input_tokens=1,
                reasoning_tokens=1,
            ),
        )

    def test_chat_completions_request_uses_profile_generation_parameters(self) -> None:
        profile = Profile(
            **{
                **self.profile(stream=False).__dict__,
                "temperature": 0.42,
                "top_p": 0.66,
                "max_tokens": 123,
                "reasoning_effort": "low",
            }
        )
        result = OpenAICompatClient(profile).chat([{"role": "user", "content": "Hi"}])

        self.assertIsInstance(result, ChatResult)
        self.assertEqual(FakeOpenAIHandler.requests[-1]["temperature"], 0.42)
        self.assertEqual(FakeOpenAIHandler.requests[-1]["top_p"], 0.66)
        self.assertEqual(FakeOpenAIHandler.requests[-1]["max_tokens"], 123)
        self.assertEqual(FakeOpenAIHandler.requests[-1]["reasoning_effort"], "low")
        self.assertEqual(FakeOpenAIHandler.requests[-1]["stream"], False)

    def test_stream_chat(self) -> None:
        client = OpenAICompatClient(self.profile(stream=True))
        result = client.chat([{"role": "user", "content": "Hi"}])
        self.assertNotIsInstance(result, ChatResult)
        self.assertEqual("".join(result), "Hello")

    def test_codex_profile_uses_cli(self) -> None:
        profile = Profile(
            name="codex",
            label="Codex",
            base_url="codex://local",
            api_key="",
            model="codex-cli",
            api_mode="codex",
            timeout_seconds=5,
            stream=True,
        )
        completed = mock.Mock(returncode=0, stdout="Codex OK\n", stderr="")
        with mock.patch("telachat.client.subprocess.run", return_value=completed) as run:
            result = OpenAICompatClient(profile).chat(
                [{"role": "user", "content": "Hi"}], stream=True
            )
        self.assertIsInstance(result, ChatResult)
        assert isinstance(result, ChatResult)
        self.assertEqual(result.content, "Codex OK")
        self.assertIn("codex", run.call_args.args[0][0])

    def test_responses_profile_extracts_output_text(self) -> None:
        profile = self.profile(stream=False).with_overrides(
            max_tokens=77,
            stream=False,
            temperature=0.35,
        )
        profile = Profile(
            **{
                **profile.__dict__,
                "api_mode": "responses",
                "reasoning_effort": "high",
                "top_p": 0.55,
            }
        )
        client = OpenAICompatClient(profile)
        with mock.patch.object(
            client,
            "_request_json",
            return_value={
                "output_text": "Response OK",
                "usage": {
                    "input_tokens": 11,
                    "output_tokens": 4,
                    "total_tokens": 15,
                    "input_tokens_details": {"cached_tokens": 6},
                    "output_tokens_details": {"reasoning_tokens": 2},
                },
            },
        ) as request:
            result = client.chat([{"role": "user", "content": "Hi"}])
        self.assertIsInstance(result, ChatResult)
        assert isinstance(result, ChatResult)
        self.assertEqual(result.content, "Response OK")
        self.assertEqual(
            result.usage,
            TokenUsage(
                input_tokens=11,
                output_tokens=4,
                total_tokens=15,
                cached_input_tokens=6,
                reasoning_tokens=2,
            ),
        )
        self.assertEqual(request.call_args.args[1], "/responses")
        body = request.call_args.args[2]
        self.assertEqual(body["max_output_tokens"], 77)
        self.assertEqual(body["temperature"], 0.35)
        self.assertEqual(body["top_p"], 0.55)
        self.assertEqual(body["reasoning"], {"effort": "high"})

    def test_usage_summary_formatting(self) -> None:
        usage = TokenUsage(
            input_tokens=13,
            output_tokens=18,
            total_tokens=31,
            cached_input_tokens=5,
            reasoning_tokens=4,
        )

        self.assertEqual(
            format_token_usage(usage),
            "Tokens: 13 in/18 out, 31 total, 5 cached, 4 reasoning",
        )
        self.assertEqual(
            token_usage_record(usage),
            {
                "cached_input_tokens": 5,
                "input_tokens": 13,
                "output_tokens": 18,
                "reasoning_tokens": 4,
                "total_tokens": 31,
            },
        )
        self.assertEqual(format_token_usage(None), "")
        self.assertEqual(token_usage_record(None), {})
        malformed = TokenUsage(
            input_tokens=-1,
            output_tokens=0,
            total_tokens=-5,
            cached_input_tokens=-2,
            reasoning_tokens=0,
        )
        self.assertEqual(format_token_usage(malformed), "Tokens: 0 out")
        self.assertEqual(
            token_usage_record(malformed),
            {"output_tokens": 0, "reasoning_tokens": 0},
        )


if __name__ == "__main__":
    unittest.main()
