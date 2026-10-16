import argparse, json, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ITEMS = {}
NEXT = [1]


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body=None):
        data = b"" if body is None else json.dumps(body).encode()
        self.send_response(code)
        if body is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def item_id(self):
        m = re.fullmatch(r"/items/(\d+)", self.path)
        return int(m.group(1)) if m else None

    def do_GET(self):
        if self.path == "/health":
            return self.send(200, {"status": "ok"})
        if self.path == "/items":
            return self.send(200, [ITEMS[k] for k in sorted(ITEMS)])
        i = self.item_id()
        if i is not None and i in ITEMS:
            return self.send(200, ITEMS[i])
        self.send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/items":
            return self.send(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"")
        except ValueError:
            return self.send(400, {"error": "invalid json"})
        name = body.get("name") if isinstance(body, dict) else None
        if not isinstance(name, str) or not name:
            return self.send(400, {"error": "name must be a non-empty string"})
        item = {"id": NEXT[0], "name": name}
        ITEMS[NEXT[0]] = item
        NEXT[0] += 1
        self.send(201, item)

    def do_DELETE(self):
        i = self.item_id()
        if i is not None and i in ITEMS:
            del ITEMS[i]
            return self.send(204)
        self.send(404, {"error": "not found"})


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--port", type=int, default=8000)
    ThreadingHTTPServer(("127.0.0.1", p.parse_args().port), H).serve_forever()
