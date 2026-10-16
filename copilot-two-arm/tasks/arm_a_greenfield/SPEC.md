# Arm A: greenfield task: a tiny HTTP item store

Write `server.py` from an empty folder, using only the Python standard library.

Run as `python server.py --port <PORT>`. It serves JSON on 127.0.0.1 and keeps items in memory.

| Request | Response |
|---|---|
| `GET /health` | `200` `{"status": "ok"}` |
| `POST /items` with `{"name": "<non-empty string>"}` | `201` `{"id": <int>, "name": "..."}`; ids start at 1 and go up by 1 |
| `POST /items` with a body that isn't JSON | `400` `{"error": "..."}` |
| `POST /items` without a non-empty string `name` | `400` `{"error": "..."}` |
| `GET /items` | `200` list of items, ordered by id |
| `GET /items/<id>` | `200` the item, or `404` `{"error": "..."}` |
| `DELETE /items/<id>` | `204` with an empty body, or `404` |
| any other path | `404` `{"error": "..."}` |

Every JSON response sets `Content-Type: application/json`.

Done = all 12 hidden acceptance checks pass (`twoarm finish` runs them). You may not see the hidden tests during a timed run.
This mirrors the shape of Peng et al. 2023 (an HTTP server, 12 checks), in Python instead of JavaScript.
