"""Transport tests: exercise each provider dialect against a local stub server.

These run fully offline. A tiny HTTP server answers the endpoints each provider
calls, which pins down request URLs, auth headers and response parsing without
needing any real API key.
"""
from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cosmoforge.providers import ChatMessage, resolve
from cosmoforge.providers.anthropic import AnthropicProvider
from cosmoforge.providers.google import GoogleProvider
from cosmoforge.providers.ollama import OllamaProvider
from cosmoforge.providers.openai import OpenAICompatProvider

MESSAGES = [ChatMessage("system", "be terse"), ChatMessage("user", "hello")]


class _Stub(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        path = self.path
        if path.endswith("/chat/completions"):
            reply = {
                "model": "stub",
                "choices": [{"message": {"role": "assistant", "content": "openai-ok"}}],
                "usage": {"total_tokens": 3},
            }
        elif path.endswith("/v1/messages"):
            reply = {
                "model": "stub",
                "content": [{"type": "text", "text": "anthropic-ok"}],
                "usage": {"input_tokens": 1},
            }
        elif ":generateContent" in path:
            reply = {
                "candidates": [{"content": {"parts": [{"text": "google-ok"}]}}],
                "usageMetadata": {"totalTokenCount": 4},
            }
        elif path.endswith("/api/chat"):
            reply = {"model": "stub", "message": {"content": "ollama-ok"}}
        else:
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(reply).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence the stub
        return


class ProviderTransportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Stub)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_openai_compatible(self):
        provider = OpenAICompatProvider(
            model="stub", api_key="k", base_url=self.base, retries=0
        )
        response = provider.complete(MESSAGES, temperature=0.2)
        self.assertEqual(response.text, "openai-ok")
        self.assertEqual(response.provider, "openai")

    def test_anthropic(self):
        provider = AnthropicProvider(model="stub", api_key="k", base_url=self.base, retries=0)
        response = provider.complete(MESSAGES)
        self.assertEqual(response.text, "anthropic-ok")
        self.assertEqual(response.provider, "anthropic")

    def test_google(self):
        provider = GoogleProvider(model="stub", api_key="k", base_url=f"{self.base}/v1beta", retries=0)
        response = provider.complete(MESSAGES)
        self.assertEqual(response.text, "google-ok")

    def test_ollama(self):
        provider = OllamaProvider(model="stub", base_url=self.base, retries=0)
        response = provider.complete(MESSAGES)
        self.assertEqual(response.text, "ollama-ok")

    def test_missing_key_is_reported(self):
        provider = resolve({"provider": "anthropic", "api_key": "", "base_url": self.base})
        provider.api_key = ""
        with self.assertRaises(Exception) as ctx:
            provider.complete(MESSAGES)
        self.assertIn("not configured", str(ctx.exception))

    def test_fallback_when_first_provider_is_unreachable(self):
        from cosmoforge.providers import FallbackProvider, MockProvider

        dead = OpenAICompatProvider(
            model="x", api_key="k", base_url="http://127.0.0.1:9", timeout=0.5, retries=0
        )
        chain = FallbackProvider([dead, MockProvider()])
        response = chain.complete(MESSAGES)
        self.assertEqual(response.provider, "mock")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
