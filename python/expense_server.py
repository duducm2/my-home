"""Local HTTP server for the my-home application."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contract_store import ContractStore, MAX_PDF_BYTES  # noqa: E402
from expense_git import GitError, push_expenses  # noqa: E402
from expense_store import ExpenseStore  # noqa: E402
from house_store import HouseStore  # noqa: E402
from import_pipeline import (  # noqa: E402
    build_price_discovery_prompt,
    build_quotation_ingestion_prompt,
    commit_rows,
    preview_pack,
)
from media_export import (  # noqa: E402
    FFmpegUnavailable,
    MAX_VIDEO_BYTES,
    MediaExportError,
    capabilities as media_capabilities,
    convert_webm_to_mp4,
)
from note_store import NoteStore  # noqa: E402
from provider_store import ProviderStore  # noqa: E402
from quick_task_store import QuickTaskStore  # noqa: E402
from task_store import TaskStore  # noqa: E402


DEFAULT_PORT = 8768
ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "web"
DATA_DIR = ROOT_DIR / "data"
_STORE: ExpenseStore | None = None
_TASKS: TaskStore | None = None
_HOUSE: HouseStore | None = None
_NOTES: NoteStore | None = None
_PROVIDERS: ProviderStore | None = None
_CONTRACTS: ContractStore | None = None
_QUICK_TASKS: QuickTaskStore | None = None


def get_store(data_dir: Path) -> ExpenseStore:
    global _STORE
    if _STORE is None or _STORE.data_dir != data_dir.resolve():
        _STORE = ExpenseStore(data_dir)
    return _STORE


def get_tasks(data_dir: Path) -> TaskStore:
    global _TASKS
    if _TASKS is None or _TASKS.data_dir != data_dir.resolve():
        _TASKS = TaskStore(data_dir)
    return _TASKS


def get_providers(data_dir: Path) -> ProviderStore:
    global _PROVIDERS
    if _PROVIDERS is None or _PROVIDERS.data_dir != data_dir.resolve():
        _PROVIDERS = ProviderStore(data_dir)
    return _PROVIDERS


def get_contracts(data_dir: Path) -> ContractStore:
    global _CONTRACTS
    if _CONTRACTS is None or _CONTRACTS.data_dir != data_dir.resolve():
        _CONTRACTS = ContractStore(data_dir)
    return _CONTRACTS


def get_notes(data_dir: Path) -> NoteStore:
    global _NOTES
    if _NOTES is None or _NOTES.data_dir != data_dir.resolve():
        _NOTES = NoteStore(data_dir)
    return _NOTES


def get_quick_tasks(data_dir: Path) -> QuickTaskStore:
    global _QUICK_TASKS
    if _QUICK_TASKS is None or _QUICK_TASKS.data_dir != data_dir.resolve():
        _QUICK_TASKS = QuickTaskStore(data_dir)
    return _QUICK_TASKS


def get_house(data_dir: Path) -> HouseStore:
    global _HOUSE
    if _HOUSE is None or _HOUSE.data_dir != data_dir.resolve():
        _HOUSE = HouseStore(data_dir)
    return _HOUSE


class ExpenseHandler(BaseHTTPRequestHandler):
    data_dir = DATA_DIR

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("[my-home] " + format % args + "\n")

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Filename")

    def _json(self, code: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _bytes(self, code: int, data: bytes, content_type: str) -> None:
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _download(self, data: bytes, content_type: str, filename: str) -> None:
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("request body must be an object")
        return payload

    def _serve_file(self, path: Path, content_type: str | None = None) -> None:
        try:
            path.resolve().relative_to(ROOT_DIR.resolve())
        except ValueError:
            self._json(403, {"ok": False, "error": "forbidden"})
            return
        if not path.is_file():
            self._json(404, {"ok": False, "error": "not found"})
            return
        guessed = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if guessed.startswith(("text/", "application/javascript", "application/json")):
            guessed += "; charset=utf-8"
        self._bytes(200, path.read_bytes(), guessed)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        path = unquote(urlparse(self.path).path)
        if path.rstrip("/") == "/health":
            self._json(200, {"ok": True, "service": "my-home", "port": DEFAULT_PORT})
            return
        if path in {"/", "/index.html"}:
            self._serve_file(WEB_DIR / "index.html", "text/html")
            return
        static = {
            "/styles.css": WEB_DIR / "styles.css",
            "/tasks.css": WEB_DIR / "tasks.css",
            "/app.js": WEB_DIR / "app.js",
            "/house-3d.js": WEB_DIR / "house-3d.js",
        }
        if path in static:
            self._serve_file(static[path])
            return
        if path.startswith("/vendor/three/"):
            filename = path.rsplit("/", 1)[-1]
            allowed = {
                "three.module.js",
                "three.core.js",
                "OrbitControls.js",
                "TransformControls.js",
                "GLTFLoader.js",
                "LICENSE.txt",
                "VERSION.txt",
            }
            if filename not in allowed:
                self._json(404, {"ok": False, "error": "vendor asset not found"})
                return
            self._serve_file(WEB_DIR / "vendor" / "three" / filename)
            return
        if path.startswith("/vendor/utils/"):
            filename = path.rsplit("/", 1)[-1]
            if filename not in {"BufferGeometryUtils.js", "SkeletonUtils.js"}:
                self._json(404, {"ok": False, "error": "vendor utility not found"})
                return
            self._serve_file(WEB_DIR / "vendor" / "utils" / filename)
            return
        pdfjs_files = {
            "/vendor/pdfjs/node_modules/pdfjs-dist/build/pdf.mjs": (
                WEB_DIR
                / "vendor"
                / "pdfjs"
                / "node_modules"
                / "pdfjs-dist"
                / "build"
                / "pdf.mjs"
            ),
            "/vendor/pdfjs/node_modules/pdfjs-dist/build/pdf.worker.mjs": (
                WEB_DIR
                / "vendor"
                / "pdfjs"
                / "node_modules"
                / "pdfjs-dist"
                / "build"
                / "pdf.worker.mjs"
            ),
        }
        if path in pdfjs_files:
            self._serve_file(pdfjs_files[path], "application/javascript")
            return
        if path.startswith("/api/expenses/") and path.endswith("/quotations"):
            parts = [part for part in path.split("/") if part]
            if len(parts) == 4:
                self._json(200, get_store(self.data_dir).quotation_state(parts[2]))
                return
        if path == "/api/state":
            self._json(200, get_store(self.data_dir).state())
            return
        if path == "/api/tasks":
            self._json(200, get_tasks(self.data_dir).state())
            return
        if path == "/api/quick-tasks":
            self._json(200, get_quick_tasks(self.data_dir).state())
            return
        if path == "/api/notes":
            self._json(200, get_notes(self.data_dir).load())
            return
        if path == "/api/providers":
            self._json(200, get_providers(self.data_dir).state())
            return
        if path == "/api/contracts":
            self._json(200, get_contracts(self.data_dir).state())
            return
        if path == "/api/cashflow":
            payload = json.loads((self.data_dir / "cashflow-projection.json").read_text(encoding="utf-8-sig"))
            self._json(200, payload)
            return
        if path == "/api/media/capabilities":
            self._json(200, media_capabilities())
            return
        if path == "/api/house":
            self._json(200, get_house(self.data_dir).load())
            return
        if path == "/api/house/blueprint.jpg":
            self._serve_file(self.data_dir / "blueprint.jpg", "image/jpeg")
            return
        people = {
            "/api/project/people/eduardo.jpg": "eduardo.jpg",
            "/api/project/people/gelson.jpg": "gelson.jpg",
            "/api/project/people/jane.png": "jane.png",
            "/api/project/people/leo.jpg": "leo.jpg",
            "/api/project/people/cats.jpg": "cats.jpg",
        }
        if path in people:
            self._serve_file(self.data_dir / "people" / people[path])
            return
        documents = {
            "/api/project/documents/purchase-contract.pdf": "purchase-contract-2026-09-08.pdf",
            "/api/project/documents/gelson-contract-01.pdf": "gelson-contract-01-draft.pdf",
            "/api/project/documents/gelson-contract-02.pdf": "gelson-contract-02-draft.pdf",
        }
        if path in documents:
            self._serve_file(self.data_dir / "documents" / documents[path], "application/pdf")
            return
        if path.startswith("/api/contracts/") and "/documents/" in path:
            parts = [part for part in path.split("/") if part]
            if len(parts) == 5 and parts[:2] == ["api", "contracts"] and parts[3] == "documents":
                document_id = "" if parts[4] == "current" else parts[4]
                try:
                    target = get_contracts(self.data_dir).document_path(parts[2], document_id)
                except ValueError as exc:
                    self._json(404, {"ok": False, "error": str(exc)})
                    return
                self._serve_file(target, "application/pdf")
                return
        if path.startswith("/assets/item-icons/"):
            filename = path.rsplit("/", 1)[-1]
            manifest = get_store(self.data_dir)._icon_manifest()
            allowed = {
                str(item.get("filename") or "")
                for item in (manifest.get("icons") or {}).values()
                if isinstance(item, dict)
            }
            if filename not in allowed:
                self._json(404, {"ok": False, "error": "item icon not found"})
                return
            self._serve_file(WEB_DIR / "assets" / "item-icons" / filename, "image/png")
            return
        if path.startswith("/assets/"):
            self._serve_file(WEB_DIR / "assets" / path[len("/assets/") :])
            return
        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        path = unquote(urlparse(self.path).path)
        try:
            if path == "/api/media/convert-video":
                length = int(self.headers.get("Content-Length", "0") or "0")
                if length <= 0 or length > MAX_VIDEO_BYTES:
                    raise ValueError("video must contain data and be at most 80 MB")
                data = self.rfile.read(length)
                converted = convert_webm_to_mp4(
                    data,
                    self.headers.get("Content-Type", "video/webm"),
                )
                self._download(converted, "video/mp4", "my-home-modelo-3d.mp4")
                return
            if path.startswith("/api/contracts/") and path.endswith("/documents"):
                parts = [part for part in path.split("/") if part]
                if len(parts) != 4:
                    raise ValueError("invalid document upload route")
                length = int(self.headers.get("Content-Length", "0") or "0")
                if length <= 0 or length > MAX_PDF_BYTES:
                    raise ValueError("PDF must contain data and be at most 25 MB")
                data = self.rfile.read(length)
                filename = unquote(self.headers.get("X-Filename", "contract.pdf"))
                self._json(200, get_contracts(self.data_dir).add_document(parts[2], data, filename))
                return
            payload = self._read_json()
            store = get_store(self.data_dir)
            if path.startswith("/api/expenses/") and "/quotations" in path:
                parts = [part for part in path.split("/") if part]
                if len(parts) == 4 and parts[3] == "quotations":
                    self._json(200, store.upsert_quotation(parts[2], payload))
                elif (
                    len(parts) == 6
                    and parts[3] == "quotations"
                    and parts[5] == "select"
                ):
                    self._json(200, store.select_quotation(parts[2], parts[4]))
                else:
                    self._json(404, {"ok": False, "error": "not found"})
            elif path == "/api/expenses":
                result = store.upsert_expense(payload)
                get_contracts(self.data_dir).sync_expense_link(result["expense_id"], str(payload.get("contract_id") or ""))
                self._json(200, result)
            elif path == "/api/tasks":
                result = get_tasks(self.data_dir).upsert(payload)
                result["expense_state"] = get_store(self.data_dir).state()
                self._json(200, result)
            elif path == "/api/quick-tasks":
                self._json(200, get_quick_tasks(self.data_dir).upsert(payload))
            elif path == "/api/notes":
                self._json(200, get_notes(self.data_dir).save(payload))
            elif path == "/api/providers":
                self._json(200, get_providers(self.data_dir).upsert(payload))
            elif path == "/api/contracts":
                self._json(200, get_contracts(self.data_dir).upsert(payload))
            elif path == "/api/push":
                self._json(200, push_expenses(ROOT_DIR))
            elif path == "/api/house":
                house_payload = payload.get("house") if isinstance(payload.get("house"), dict) else payload
                self._json(200, get_house(self.data_dir).save(house_payload))
            elif path == "/api/house/name":
                self._json(200, get_house(self.data_dir).save_name(payload.get("name")))
            elif path == "/api/house/model3d-layout":
                self._json(200, get_house(self.data_dir).save_model3d_layout(payload))
            elif path == "/api/prompts/quotation-ingestion":
                ids = payload.get("ids") if isinstance(payload.get("ids"), list) else None
                self._json(
                    200,
                    build_quotation_ingestion_prompt(
                        store,
                        ids,
                        str(payload.get("source_text") or ""),
                    ),
                )
            elif path == "/api/prompts/price-discovery":
                ids = payload.get("ids") if isinstance(payload.get("ids"), list) else None
                self._json(
                    200,
                    build_price_discovery_prompt(
                        store,
                        ids,
                        str(payload.get("source_text") or ""),
                    ),
                )
            elif path == "/api/import/preview":
                self._json(
                    200,
                    preview_pack(
                        str(payload.get("pack_text") or ""),
                        pack_id=str(payload.get("pack_id") or "price"),
                        correction_instructions=str(
                            payload.get("correction_instructions") or ""
                        ),
                        expense_context=str(payload.get("expense_context") or ""),
                    ),
                )
            elif path == "/api/import/commit":
                rows = payload.get("rows")
                if not isinstance(rows, list):
                    raise ValueError("rows is required")
                self._json(
                    200,
                    commit_rows(
                        store,
                        rows,
                        pack_text=str(payload.get("pack_text") or ""),
                        pack_id=str(payload.get("pack_id") or "price"),
                        expense_context=str(
                            payload.get("expense_context") or ""
                        ),
                    ),
                )
            else:
                self._json(404, {"ok": False, "error": "not found"})
        except (json.JSONDecodeError, ValueError) as exc:
            self._json(400, {"ok": False, "error": str(exc)})
        except FFmpegUnavailable as exc:
            self._json(503, {"ok": False, "error": str(exc), "fallback": "video/webm"})
        except MediaExportError as exc:
            self._json(500, {"ok": False, "error": str(exc), "fallback": "video/webm"})
        except GitError as exc:
            self._json(500, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._json(500, {"ok": False, "error": str(exc), "trace": traceback.format_exc()})

    def do_DELETE(self) -> None:
        path = unquote(urlparse(self.path).path)
        try:
            if path.startswith("/api/expenses/") and "/quotations/" in path:
                parts = [part for part in path.split("/") if part]
                if len(parts) != 5 or parts[3] != "quotations":
                    raise ValueError("invalid quotation route")
                self._json(
                    200,
                    get_store(self.data_dir).delete_quotation(parts[2], parts[4]),
                )
            elif path.startswith("/api/expenses/"):
                expense_id = path[len("/api/expenses/") :]
                result = get_store(self.data_dir).delete_expense(expense_id)
                get_contracts(self.data_dir).sync_expense_link(expense_id)
                self._json(200, result)
            elif path.startswith("/api/tasks/"):
                result = get_tasks(self.data_dir).delete(path[len("/api/tasks/") :])
                result["expense_state"] = get_store(self.data_dir).state()
                self._json(200, result)
            elif path.startswith("/api/quick-tasks/"):
                self._json(
                    200,
                    get_quick_tasks(self.data_dir).delete(
                        path[len("/api/quick-tasks/") :]
                    ),
                )
            elif path.startswith("/api/contracts/"):
                self._json(200, get_contracts(self.data_dir).archive(path[len("/api/contracts/") :]))
            elif path.startswith("/api/providers/"):
                self._json(200, get_providers(self.data_dir).archive(path[len("/api/providers/") :]))
            else:
                self._json(404, {"ok": False, "error": "not found"})
        except ValueError as exc:
            self._json(400, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._json(500, {"ok": False, "error": str(exc), "trace": traceback.format_exc()})


def make_handler(data_dir: Path):
    class BoundHandler(ExpenseHandler):
        pass

    BoundHandler.data_dir = data_dir.resolve()
    return BoundHandler


def main() -> int:
    parser = argparse.ArgumentParser(description="my-home local server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    get_store(args.data_dir)
    get_tasks(args.data_dir)
    get_providers(args.data_dir)
    get_contracts(args.data_dir)
    get_quick_tasks(args.data_dir)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(args.data_dir))
    url = f"http://{args.host}:{args.port}/"
    print(f"my-home server listening on {url}", flush=True)
    print(f"Data: {args.data_dir.resolve()}", flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
