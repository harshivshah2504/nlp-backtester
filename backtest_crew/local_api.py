"""Local server for running the Backtest Crew frontend and API together.

Usage:
    python backtest_crew/local_api.py

This serves:
    GET  /                 -> static frontend
    GET  /assets/*         -> frontend assets
    GET  /config.js        -> frontend config
    POST /api/backtest     -> runs the Python crew and returns JSON
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from dashboard import build_netlify_dashboard, serialize_backtest_result


STATIC_DIR = THIS_DIR / "netlify_dashboard"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
_RUN_CREW_IMPL = None


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=True).encode("utf-8")


def _get_run_crew():
    global _RUN_CREW_IMPL
    if _RUN_CREW_IMPL is None:
        main_module = importlib.import_module("main")
        _RUN_CREW_IMPL = main_module.run_crew
    return _RUN_CREW_IMPL


class BacktestRequestHandler(BaseHTTPRequestHandler):
    server_version = "BacktestCrewLocal/1.0"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        request_path = parsed.path or "/"

        if request_path == "/health":
            self._write_json({"status": "ok"})
            return

        self._serve_static(request_path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/backtest":
            self._write_json(
                {"status": "failed", "error": f"Unknown endpoint: {parsed.path}"},
                status=HTTPStatus.NOT_FOUND,
            )
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self._write_json(
                {"status": "failed", "error": "Missing JSON body."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._write_json(
                {"status": "failed", "error": "Request body must be valid JSON."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        query = str(payload.get("query", "")).strip()
        if not query:
            self._write_json(
                {"status": "failed", "error": "Field 'query' is required."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            result = _get_run_crew()(query)
            response_payload = {"result": serialize_backtest_result(result)}
            self._write_json(response_payload)
        except Exception as exc:  # pragma: no cover - runtime behavior
            self._write_json(
                {
                    "result": {
                        "status": "failed",
                        "error": str(exc),
                    }
                },
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[local_api] {self.address_string()} - {format % args}")

    def _serve_static(self, request_path: str) -> None:
        normalized_path = request_path
        if normalized_path in {"/", ""}:
            normalized_path = "/index.html"

        if normalized_path.startswith("/backtest_crew/netlify_dashboard/"):
            normalized_path = normalized_path.removeprefix("/backtest_crew/netlify_dashboard")

        candidate = (STATIC_DIR / normalized_path.lstrip("/")).resolve()
        static_root = STATIC_DIR.resolve()

        if static_root not in candidate.parents and candidate != static_root:
            self._write_json(
                {"status": "failed", "error": "Invalid path."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        if candidate.is_dir():
            candidate = candidate / "index.html"

        if not candidate.exists() or not candidate.is_file():
            candidate = STATIC_DIR / "index.html"

        content_type = self._guess_content_type(candidate)
        body = candidate.read_bytes()

        self.send_response(HTTPStatus.OK)
        self._set_cors_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _guess_content_type(self, path: Path) -> str:
        suffix = path.suffix.lower()
        return {
            ".html": "text/html; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".ico": "image/x-icon",
        }.get(suffix, "application/octet-stream")

    def _write_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _set_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Backtest Crew local web server.")
    parser.add_argument("--host", default=os.getenv("BACKTEST_CREW_HOST", DEFAULT_HOST))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", os.getenv("BACKTEST_CREW_PORT", str(DEFAULT_PORT)))),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    build_netlify_dashboard(output_dir=STATIC_DIR, api_base_url="", api_path="/api/backtest")

    server = ThreadingHTTPServer((args.host, args.port), BacktestRequestHandler)
    print(f"Backtest Crew local server running at http://{args.host}:{args.port}")
    print(f"Frontend: http://{args.host}:{args.port}/")
    print(f"API:      http://{args.host}:{args.port}/api/backtest")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
