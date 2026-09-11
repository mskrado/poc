"""Local static server for the fixture sites.

Mock mode never needs a browser, but the fixtures are real pages: serve them to poke at
the failure modes by hand, or to point a live adapter at something safe.
"""

from __future__ import annotations

import contextlib
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator

from browser_benchmark.config import sites_root


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


def list_sites(root: Path | None = None) -> list[str]:
    base = sites_root(root)
    return sorted(p.name for p in base.iterdir() if p.is_dir() and (p / "index.html").exists())


def site_url(base_url: str, fixture: str) -> str:
    return f"{base_url.rstrip('/')}/{fixture}/"


def make_server(port: int = 0, root: Path | None = None) -> ThreadingHTTPServer:
    handler = partial(_QuietHandler, directory=str(sites_root(root)))
    return ThreadingHTTPServer(("127.0.0.1", port), handler)


@contextlib.contextmanager
def serve(port: int = 0, root: Path | None = None) -> Iterator[str]:
    """Serve the fixture sites for the duration of the context, yielding the base URL."""
    server = make_server(port, root)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def serve_forever(port: int = 8000, root: Path | None = None) -> None:
    server = make_server(port, root)
    print(f"Serving fixture sites on http://127.0.0.1:{server.server_address[1]}/ (ctrl-c to stop)")
    for name in list_sites(root):
        print(f"  /{name}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        server.server_close()
