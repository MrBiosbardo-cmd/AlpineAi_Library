import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx


HOST = "127.0.0.1"
PORT = 8169
UPSTREAM_URL = "https://api.169pi.com/v1/chat/completions"
ALLOWED_FIELDS = {
    "model",
    "messages",
    "max_tokens",
    "temperature",
    "stream",
    "top_p",
    "frequency_penalty",
    "presence_penalty",
}


def normalize_content(content: object) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content) if content is not None else ""

    text_parts = []
    for block in content:
        if isinstance(block, str):
            text_parts.append(block)
        elif isinstance(block, dict) and isinstance(block.get("text"), str):
            text_parts.append(block["text"])
    return "\n".join(text_parts)


def normalize_messages(messages: object) -> list[dict[str, str]]:
    if not isinstance(messages, list):
        raise ValueError("messages must be an array")

    normalized = []
    for message in messages:
        if not isinstance(message, dict):
            raise ValueError("each message must be an object")
        role = message.get("role")
        if role == "developer":
            role = "system"
        elif role == "tool":
            role = "user"
        if role not in {"system", "user", "assistant"}:
            raise ValueError(f"unsupported message role: {role}")
        normalized.append(
            {"role": role, "content": normalize_content(message.get("content"))}
        )
    return normalized


class Pi169ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/health":
            self._send_json(200, {"status": "ok"})
            return

        if self.path.rstrip("/") == "/v1/models":
            self._send_json(
                200,
                {
                    "object": "list",
                    "data": [{"id": "alpie-32b", "object": "model"}],
                },
            )
            return

        self._send_json(404, {"error": {"message": "Not found"}})

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._send_json(404, {"error": {"message": "Not found"}})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            request_body = json.loads(self.rfile.read(content_length))
        except (ValueError, json.JSONDecodeError):
            self._send_json(400, {"error": {"message": "Invalid JSON body"}})
            return

        authorization = self.headers.get("Authorization")
        if not authorization:
            self._send_json(401, {"error": {"message": "Missing API key"}})
            return

        payload = {
            key: value for key, value in request_body.items() if key in ALLOWED_FIELDS
        }
        try:
            payload["messages"] = normalize_messages(payload.get("messages"))
            payload["max_tokens"] = min(int(payload.get("max_tokens") or 1000), 1000)
        except (TypeError, ValueError) as error:
            self._send_json(400, {"error": {"message": str(error)}})
            return
        payload["model"] = "alpie-32b"

        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if payload.get("stream") else "application/json",
        }

        try:
            with httpx.Client(timeout=None) as client:
                with client.stream(
                    "POST", UPSTREAM_URL, headers=headers, json=payload
                ) as response:
                    self.send_response(response.status_code)
                    self.send_header(
                        "Content-Type",
                        response.headers.get("Content-Type", "application/json"),
                    )
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "close")
                    self.end_headers()
                    for chunk in response.iter_bytes():
                        self.wfile.write(chunk)
                        self.wfile.flush()
        except (httpx.HTTPError, OSError) as error:
            self._send_json(502, {"error": {"message": str(error)}})

    def log_message(self, format: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Pi169ProxyHandler)
    print(f"Pi169 Cline proxy listening at http://{HOST}:{PORT}/v1")
    server.serve_forever()