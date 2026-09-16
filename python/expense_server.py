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
from house_store import HouseStore  # noqa: E402
from expense_git import GitError, push_expenses  # noqa: E402
from import_pipeline import (  # noqa: E402
    build_price_discovery_prompt,
    commit_rows,
    preview_pack,
)

DEFAULT_PORT = 8768
ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "web"
DATA_DIR = ROOT_DIR / "data"
_STORE: ExpenseStore | None = None
_HOUSE: HouseStore | None = None


def get_store(data_dir: Path) -> ExpenseStore:
    global _STORE
    resolved = data_dir.resolve()
    if _STORE is None or _STORE.data_dir.resolve() != resolved:
        _STORE = ExpenseStore(resolved)
    return _STORE


def get_house(data_dir: Path) -> HouseStore:
    global _HOUSE
    resolved = data_dir.resolve()
    if _HOUSE is None or _HOUSE.data_dir.resolve() != resolved:
        _HOUSE = HouseStore(resolved)
    return _HOUSE


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
        self.send_header("Cache-Control", "no-store, max-age=0")
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
                    "features": ["state", "crud", "push", "prompts", "import", "house", "house_3d"],
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

        if path == "/house-3d.js":
            self._serve_static("house-3d.js", "application/javascript; charset=utf-8")
            return

        if path.startswith("/vendor/three/"):
            filename = path.rsplit("/", 1)[-1]
            allowed = {
                "three.module.js",
                "three.core.js",
                "OrbitControls.js",
                "LICENSE.txt",
                "VERSION.txt",
            }
            if filename not in allowed:
                self._json(404, {"ok": False, "error": "vendor asset not found"})
                return
            content_type = "application/javascript; charset=utf-8" if filename.endswith(".js") else "text/plain; charset=utf-8"
            self._serve_static(f"vendor/three/{filename}", content_type)
            return

        if path == "/api/state":
            store = get_store(self.data_dir)
            self._json(200, store.state())
            return

        if path == "/api/house":
            house = get_house(self.data_dir)
            self._json(200, house.load())
            return

        if path in ("/api/house/blueprint.jpg", "/data/blueprint.jpg"):
            bp = (self.data_dir / "blueprint.jpg").resolve()
            try:
                bp.relative_to(self.data_dir.resolve())
            except ValueError:
                self._json(403, {"ok": False, "error": "forbidden"})
                return
            if not bp.is_file():
                self._json(404, {"ok": False, "error": "blueprint missing"})
                return
            self._bytes(200, bp.read_bytes(), "image/jpeg")
            return

        if path.startswith("/api/project/people/"):
            filename = path.rsplit("/", 1)[-1]
            allowed = {
                "eduardo.jpg": "image/jpeg",
                "gelson.jpg": "image/jpeg",
                "jane.png": "image/png",
                "leo.jpg": "image/jpeg",
            }
            mime_type = allowed.get(filename)
            if not mime_type:
                self._json(404, {"ok": False, "error": "person image not found"})
                return
            image = (self.data_dir / "people" / filename).resolve()
            try:
                image.relative_to((self.data_dir / "people").resolve())
            except ValueError:
                self._json(403, {"ok": False, "error": "forbidden"})
                return
            if not image.is_file():
                self._json(404, {"ok": False, "error": "person image missing"})
                return
            self._bytes(200, image.read_bytes(), mime_type)
            return

        if path == "/api/project/documents/purchase-contract.pdf":
            document = (
                self.data_dir
                / "documents"
                / "purchase-contract-2026-09-08.pdf"
            ).resolve()
            try:
                document.relative_to(self.data_dir.resolve())
            except ValueError:
                self._json(403, {"ok": False, "error": "forbidden"})
                return
            if not document.is_file():
                self._json(404, {"ok": False, "error": "contract missing"})
                return
            self._bytes(200, document.read_bytes(), "application/pdf")
            return

        if path.startswith("/assets/"):
            rel = path[len("/assets/") :]
            self._serve_static(f"assets/{rel}", "image/jpeg" if rel.lower().endswith((".jpg", ".jpeg")) else "application/octet-stream")
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
            if path == "/api/push":
                result = push_expenses(ROOT_DIR)
                self._json(200, result)
                return
            if path == "/api/house":
                house_payload = payload.get("house") if isinstance(payload.get("house"), dict) else payload
                self._json(200, get_house(self.data_dir).save(house_payload))
                return
            if path == "/api/prompts/price-discovery":
                ids = payload.get("ids") if isinstance(payload.get("ids"), list) else None
                self._json(200, build_price_discovery_prompt(store, ids))
                return
            if path == "/api/import/preview":
                pack_text = str(payload.get("pack_text") or "")
                pack_id = str(payload.get("pack_id") or "price")
                self._json(200, preview_pack(pack_text, pack_id=pack_id))
                return
            if path == "/api/import/commit":
                rows = payload.get("rows")
                if not isinstance(rows, list) or not rows:
                    self._json(400, {"ok": False, "error": "rows required"})
                    return
                pack_text = str(payload.get("pack_text") or "")
                pack_id = str(payload.get("pack_id") or "price")
                self._json(200, commit_rows(store, rows, pack_text=pack_text, pack_id=pack_id))
                return
            self._json(404, {"ok": False, "error": "not found"})
        except ValueError as exc:
            self._json(400, {"ok": False, "error": str(exc)})
        except GitError as exc:
            self._json(500, {"ok": False, "error": str(exc)})
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
