"""Hidden acceptance checks for Arm A. 12 tests, like Peng et al.'s 12 checks."""
import json, os, socket, subprocess, sys, time, urllib.request, urllib.error
import pytest

WS = os.environ["TWOARM_WORKSPACE"]


def _port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


@pytest.fixture(scope="module")
def base():
    port = _port()
    proc = subprocess.Popen([sys.executable, os.path.join(WS, "server.py"), "--port", str(port)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(url + "/health", timeout=0.5); break
        except Exception:
            time.sleep(0.1)
    yield url
    proc.terminate(); proc.wait(5)


def req(base, method, path, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    r = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=3) as resp:
            txt = resp.read().decode(); return resp.status, resp.headers, (json.loads(txt) if txt else None)
    except urllib.error.HTTPError as e:
        txt = e.read().decode(); return e.code, e.headers, (json.loads(txt) if txt else None)


def test_01_health(base):
    s, h, b = req(base, "GET", "/health"); assert s == 200 and b == {"status": "ok"}

def test_02_content_type(base):
    s, h, b = req(base, "GET", "/health"); assert h["Content-Type"].startswith("application/json")

def test_03_create_first(base):
    s, h, b = req(base, "POST", "/items", {"name": "a"}); assert s == 201 and b == {"id": 1, "name": "a"}

def test_04_create_second(base):
    s, h, b = req(base, "POST", "/items", {"name": "b"}); assert s == 201 and b["id"] == 2

def test_05_list_ordered(base):
    s, h, b = req(base, "GET", "/items"); assert s == 200 and [i["id"] for i in b] == [1, 2]

def test_06_get_one(base):
    s, h, b = req(base, "GET", "/items/2"); assert s == 200 and b == {"id": 2, "name": "b"}

def test_07_get_missing(base):
    s, h, b = req(base, "GET", "/items/999"); assert s == 404 and "error" in b

def test_08_bad_json(base):
    s, h, b = req(base, "POST", "/items", raw=b"{not json"); assert s == 400 and "error" in b

def test_09_missing_name(base):
    s, h, b = req(base, "POST", "/items", {"title": "x"}); assert s == 400 and "error" in b

def test_10_empty_name(base):
    s, h, b = req(base, "POST", "/items", {"name": ""}); assert s == 400

def test_11_delete(base):
    s, h, b = req(base, "DELETE", "/items/1"); assert s == 204 and b is None
    s, h, b = req(base, "GET", "/items/1"); assert s == 404

def test_12_unknown_route(base):
    s, h, b = req(base, "GET", "/nope"); assert s == 404 and "error" in b
