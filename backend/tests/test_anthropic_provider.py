"""Exercises the real Anthropic SDK against a local stub server to verify the request we send."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from app.ai.providers import AnthropicProvider, ProviderConfig


def test_anthropic_provider_request_shape(monkeypatch):
    seen = {}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            seen["path"] = self.path
            seen["headers"] = dict(self.headers)
            seen["body"] = json.loads(self.rfile.read(int(self.headers["content-length"])))
            body = json.dumps({
                "id": "msg_1", "type": "message", "role": "assistant", "model": seen["body"]["model"],
                "content": [{"type": "text", "text": "Hello Sachin"}], "stop_reason": "end_turn", "stop_sequence": None,
                "usage": {"input_tokens": 10, "output_tokens": 3},
            }).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("ANTHROPIC_BASE_URL", f"http://127.0.0.1:{srv.server_port}")
    p = AnthropicProvider(ProviderConfig("anthropic", "claude-opus-5-5", "sk-ant-test"))
    out = p.complete("system prompt", [{"role": "user", "content": "hi"}], max_tokens=500)
    srv.shutdown()
    assert out == "Hello Sachin"
    assert seen["path"].startswith("/v1/messages")
    hdrs = {k.lower(): v for k, v in seen["headers"].items()}
    assert hdrs.get("x-api-key") == "sk-ant-test" or hdrs.get("authorization") == "Bearer sk-ant-test"
    assert seen["body"]["system"] == "system prompt" and seen["body"]["model"] == "claude-opus-5-5"
    assert seen["body"]["fallbacks"] == "default" and "server-side-fallback-2026-07-01" in hdrs["anthropic-beta"]
