"""Local HTTP server for the home expenses web app (port 8768)."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from expense_store import ExpenseStore  # noqa: E402

DEFAULT_PORT = 8768
ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "web"
DATA_DIR = ROOT_DIR / "data"
_STORE: ExpenseStore | None = None


def get_store(data_dir: Path) -> ExpenseStore:
    global _STORE
    resolved = data_dir.resolve()
    if _STORE is None or _STORE.data_dir.resolve() != resolved:
        _STORE = ExpenseStore(resolved)
    return _STORE


class ExpenseHandler(BaseHTTPRequestHandler):
    data_dir: Path

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("[expense_server] " + (format % args) + "\n")

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _bytes(self, code: int, data: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self._cors()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _serve_static(self, relative: str, content_type: str) -> None:
        path = (WEB_DIR / relative).resolve()
        try:
            path.relative_to(WEB_DIR.resolve())
        except ValueError:
            self._json(403, {"ok": False, "error": "forbidden"})
            return
        if not path.is_file():
            self._json(404, {"ok": False, "error": "not found"})
            return
        self._bytes(200, path.read_bytes(), content_type)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path.rstrip("/") == "/health":
            self._json(
                200,
                {
                    "ok": True,
                    "service": "expense_server",
                    "port": DEFAULT_PORT,
                    "features": ["state", "crud"],
                },
            )
            return

        if path in ("/", "/index.html"):
            self._serve_static("index.html", "text/html; charset=utf-8")
            return

        if path == "/styles.css":
            self._serve_static("styles.css", "text/css; charset=utf-8")
            return

        if path == "/app.js":
            self._serve_static("app.js", "application/javascript; charset=utf-8")
            return

        if path == "/api/state":
            store = get_store(self.data_dir)
            self._json(200, store.state())
            return

        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        store = get_store(self.data_dir)
        try:
            payload = self._read_json()
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "invalid JSON"})
            return
        try:
            if path == "/api/expenses":
                self._json(200, store.upsert_expense(payload))
                return
            self._json(404, {"ok": False, "error": "not found"})
        except ValueError as exc:
            self._json(400, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._json(
                500,
                {"ok": False, "error": str(exc), "trace": traceback.format_exc()},
            )

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        store = get_store(self.data_dir)
        try:
            if path.startswith("/api/expenses/"):
                expense_id = path[len("/api/expenses/") :]
                self._json(200, store.delete_expense(expense_id))
                return
            self._json(404, {"ok": False, "error": "not found"})
        except ValueError as exc:
            self._json(400, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._json(
                500,
                {"ok": False, "error": str(exc), "trace": traceback.format_exc()},
            )


def make_handler(data_dir: Path):
    class BoundHandler(ExpenseHandler):
        pass

    BoundHandler.data_dir = data_dir
    return BoundHandler


def main() -> int:
    parser = argparse.ArgumentParser(description="Home expenses local server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help="Directory for expenses.csv",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the app in the default browser",
    )
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    get_store(data_dir)

    handler = make_handler(data_dir)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"Home expenses server listening on {url}", flush=True)
    print(f"Data: {data_dir / 'expenses.csv'}", flush=True)

    if args.open:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down…", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
