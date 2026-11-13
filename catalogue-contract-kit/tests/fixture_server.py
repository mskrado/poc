"""Local fixture stores: 'pass', 'fail' and 'blocked' (403 to this kit's UA), each on its own port."""
import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


class Handler(SimpleHTTPRequestHandler):
    blocked = False

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.blocked and self.path.startswith("/products/"):
            self.send_response(403)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>Access Denied</body></html>")
            return
        return super().do_GET()


def serve(variant):
    folder = "pass" if variant == "blocked" else variant
    handler = type(f"H_{variant}", (Handler,), {"blocked": variant == "blocked"})
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(handler, directory=str(FIXTURES / folder)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/"
