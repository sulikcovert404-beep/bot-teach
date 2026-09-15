from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/health/ready":
            body = json.dumps({"status": "ready", "environment": "disposable"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        elif self.path == "/health" or self.path.endswith("/"):
            body = b"<!doctype html><html lang='fa' dir='rtl'><body>disposable fixture</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        else:
            body = b"not found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
