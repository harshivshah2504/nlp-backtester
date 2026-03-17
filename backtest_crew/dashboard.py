"""Build a Netlify-hostable dashboard for the backtest crew.

This module replaces the old Streamlit UI with two pieces:

1. A serializer that converts the existing Python backtest result into a
   browser-friendly JSON payload.
2. A small static-site builder that writes a Netlify-ready frontend.

Usage:
    python backtest_crew/dashboard.py

Optional environment variables:
    NETLIFY_BACKTEST_API_BASE_URL
    NETLIFY_BACKTEST_API_PATH
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover - dashboard build should still work
    pd = None


THIS_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = THIS_DIR / "netlify_dashboard"
DEFAULT_API_PATH = "/api/backtest"


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Backtest Crew</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap"
      rel="stylesheet"
    />
    <link rel="stylesheet" href="./assets/styles.css" />
  </head>
  <body>
    <main class="app-shell">
      <section class="input-panel">
        <textarea
          id="query"
          rows="8"
          placeholder="Enter your trading strategy idea..."
        ></textarea>
        <button id="runButton" type="button">Run</button>
        <div id="statusBanner" class="status-banner">Ready.</div>
      </section>

      <section class="output-grid">
        <div class="output-box">
          <div class="output-title">Summary</div>
          <div id="resultMeta" class="meta-text">No run yet.</div>
          <div id="summaryCards" class="summary-grid empty-state">No result.</div>
        </div>

        <div class="output-box">
          <div class="output-title">Trades</div>
          <div id="tradesTable" class="table-shell empty-state">No trades.</div>
        </div>

        <div class="output-box">
          <div class="output-title">Chart</div>
          <div id="figureContainer" class="figure-shell empty-state">No chart.</div>
        </div>

        <div class="output-box">
          <div class="output-title">Code</div>
          <pre id="codeBlock" class="code-shell empty-state"><code>No code.</code></pre>
        </div>

        <div class="output-box">
          <div class="output-title">Output</div>
          <pre id="outputBlock" class="code-shell empty-state"><code>No output.</code></pre>
        </div>
      </section>
    </main>

    <script src="./config.js"></script>
    <script src="./assets/app.js"></script>
  </body>
</html>
"""


STYLES_CSS = """:root {
  --bg: #f7f7f4;
  --panel: #ffffff;
  --border: #d7d9d2;
  --ink: #171717;
  --muted: #676b63;
  --accent: #111111;
  --success: #1f7a4d;
  --error: #a33d2b;
  --shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  background: var(--bg);
  color: var(--ink);
  font-family: "Space Grotesk", sans-serif;
}

textarea,
pre,
code,
button {
  font-family: "IBM Plex Mono", monospace;
}

.app-shell {
  width: min(1100px, calc(100vw - 24px));
  margin: 24px auto;
}

.input-panel,
.output-box {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: var(--shadow);
}

.input-panel {
  padding: 16px;
}

textarea {
  width: 100%;
  min-height: 180px;
  resize: vertical;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px;
  background: #fcfcfa;
  color: var(--ink);
  font-size: 0.95rem;
}

textarea:focus {
  outline: none;
  border-color: #999d93;
}

button {
  margin-top: 12px;
  border: none;
  border-radius: 10px;
  padding: 12px 16px;
  background: var(--accent);
  color: #ffffff;
  font-size: 0.95rem;
  cursor: pointer;
}

button:disabled {
  opacity: 0.7;
  cursor: wait;
}

.status-banner {
  margin-top: 12px;
  color: var(--muted);
  font-size: 0.92rem;
}

.status-banner.success {
  color: var(--success);
}

.status-banner.error {
  color: var(--error);
}

.output-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
  margin-top: 14px;
}

.output-box {
  padding: 14px;
}

.output-title {
  margin-bottom: 10px;
  font-size: 0.92rem;
  font-weight: 700;
}

.meta-text {
  margin-bottom: 10px;
  color: var(--muted);
  font-size: 0.9rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}

.summary-card {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px;
  background: #fcfcfa;
}

.summary-card-label {
  display: block;
  margin-bottom: 6px;
  color: var(--muted);
  font-size: 0.78rem;
  text-transform: uppercase;
}

.summary-card-value {
  display: block;
  font-size: 1.05rem;
  font-weight: 700;
}

.table-shell,
.figure-shell,
.code-shell {
  min-height: 96px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: #fcfcfa;
  overflow: auto;
}

.table-shell {
  padding: 10px;
}

.table-shell table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.table-shell th,
.table-shell td {
  padding: 8px 10px;
  text-align: left;
  border-bottom: 1px solid #eceee8;
  white-space: nowrap;
}

.table-shell th {
  background: #f2f4ee;
  position: sticky;
  top: 0;
}

.figure-shell iframe {
  width: 100%;
  min-height: 520px;
  border: none;
}

.code-shell {
  margin: 0;
  padding: 12px;
  line-height: 1.5;
}

.empty-state {
  display: grid;
  place-items: center;
  color: var(--muted);
}
"""


APP_JS = """const DEFAULT_CONFIG = window.__BACKTEST_CONFIG__ || {};

const elements = {
  query: document.getElementById("query"),
  runButton: document.getElementById("runButton"),
  statusBanner: document.getElementById("statusBanner"),
  resultMeta: document.getElementById("resultMeta"),
  summaryCards: document.getElementById("summaryCards"),
  tradesTable: document.getElementById("tradesTable"),
  figureContainer: document.getElementById("figureContainer"),
  codeBlock: document.getElementById("codeBlock"),
  outputBlock: document.getElementById("outputBlock"),
};

function getRequestUrl() {
  const baseUrl =
    DEFAULT_CONFIG.apiBaseUrl ||
    (window.location.protocol.startsWith("http") ? window.location.origin : "");
  const apiPath = DEFAULT_CONFIG.apiPath || "/api/backtest";
  return `${baseUrl.replace(/\\/$/, "")}${apiPath.startsWith("/") ? apiPath : `/${apiPath}`}`;
}

function setStatus(message, tone = "") {
  elements.statusBanner.className = tone ? `status-banner ${tone}` : "status-banner";
  elements.statusBanner.textContent = message;
}

function setTextCodeBlock(element, text, emptyFallback) {
  const code = element.querySelector("code") || document.createElement("code");
  code.textContent = text || emptyFallback;
  element.classList.toggle("empty-state", !text);
  element.replaceChildren(code);
}

function normalizeResult(payload) {
  if (payload && typeof payload === "object" && payload.result && typeof payload.result === "object") {
    return payload.result;
  }
  return payload;
}

function renderSummaryCards(result) {
  const summary = result?.stats_summary || result?.stats || {};
  const entries = Object.entries(summary || {}).filter(([key, value]) => key !== "_trades" && (typeof value !== "object" || value === null));

  if (!entries.length) {
    elements.summaryCards.className = "summary-grid empty-state";
    elements.summaryCards.textContent = "No result.";
    return;
  }

  elements.summaryCards.className = "summary-grid";
  elements.summaryCards.replaceChildren(
    ...entries.map(([key, value]) => {
      const card = document.createElement("article");
      card.className = "summary-card";

      const label = document.createElement("span");
      label.className = "summary-card-label";
      label.textContent = key.replaceAll("_", " ");

      const metric = document.createElement("strong");
      metric.className = "summary-card-value";
      metric.textContent = String(value);

      card.append(label, metric);
      return card;
    })
  );
}

function renderTradesTable(result) {
  const trades = result?.trades || result?.stats?._trades || [];
  if (!Array.isArray(trades) || !trades.length) {
    elements.tradesTable.className = "table-shell empty-state";
    elements.tradesTable.textContent = "No trades.";
    return;
  }

  const columns = Array.from(
    trades.reduce((set, row) => {
      Object.keys(row || {}).forEach((key) => set.add(key));
      return set;
    }, new Set())
  );

  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const tbody = document.createElement("tbody");
  const headerRow = document.createElement("tr");

  columns.forEach((column) => {
    const th = document.createElement("th");
    th.textContent = column;
    headerRow.appendChild(th);
  });

  thead.appendChild(headerRow);

  trades.forEach((row) => {
    const tr = document.createElement("tr");
    columns.forEach((column) => {
      const td = document.createElement("td");
      td.textContent = row?.[column] == null ? "" : String(row[column]);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  table.append(thead, tbody);
  elements.tradesTable.className = "table-shell";
  elements.tradesTable.replaceChildren(table);
}

function renderFigure(result) {
  const figureHtml = result?.figure_html || result?.fig_html || "";
  const figureUrl = result?.figure_url || result?.fig_url || "";

  if (figureHtml || figureUrl) {
    const iframe = document.createElement("iframe");
    iframe.loading = "lazy";
    iframe.referrerPolicy = "no-referrer";
    if (figureHtml) {
      iframe.srcdoc = figureHtml;
    } else {
      iframe.src = figureUrl;
    }
    elements.figureContainer.className = "figure-shell";
    elements.figureContainer.replaceChildren(iframe);
    return;
  }

  elements.figureContainer.className = "figure-shell empty-state";
  elements.figureContainer.textContent = "No chart.";
}

function renderResult(result) {
  renderSummaryCards(result || {});
  renderTradesTable(result || {});
  renderFigure(result || {});
  setTextCodeBlock(elements.codeBlock, result?.final_code || "", "No code.");
  setTextCodeBlock(elements.outputBlock, result?.output || result?.error || "", "No output.");

  const status = result?.status || "unknown";
  const attempts = result?.attempts_taken ? `attempts ${result.attempts_taken}` : "attempts n/a";
  elements.resultMeta.textContent = `${status} | ${attempts}`;
}

async function runBacktest() {
  const query = elements.query.value.trim();
  if (!query) {
    setStatus("Enter a query.", "error");
    return;
  }

  elements.runButton.disabled = true;
  elements.resultMeta.textContent = "running...";
  setStatus("Running...");

  try {
    const response = await fetch(getRequestUrl(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    const payload = await response.json();
    const result = normalizeResult(payload);

    if (!response.ok) {
      const message = result?.error || `Request failed with HTTP ${response.status}`;
      renderResult(result || { status: "failed", error: message });
      setStatus(message, "error");
      return;
    }

    renderResult(result || {});
    setStatus("Done.", result?.status === "failed" ? "error" : "success");
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    renderResult({ status: "failed", error: message });
    setStatus(message, "error");
  } finally {
    elements.runButton.disabled = false;
  }
}

function bootstrap() {
  elements.query.value = DEFAULT_CONFIG.exampleQuery || "";
  elements.runButton.addEventListener("click", runBacktest);
}

bootstrap();
"""


def _default_config_js(api_base_url: str, api_path: str) -> str:
    payload = {
        "apiBaseUrl": api_base_url,
        "apiPath": api_path,
        "exampleQuery": (
            "Design a technical long-short strategy for MSFT from 2024-01-01 "
            "with ATR-based stop loss, take profit, and adaptive risk sizing."
        ),
    }
    return f"window.__BACKTEST_CONFIG__ = {json.dumps(payload, indent=2)};\n"


def _netlify_toml(output_dir: Path) -> str:
    relative_publish_dir = Path(os.path.relpath(output_dir, Path.cwd()))
    return (
        "[build]\n"
        f'  publish = "{relative_publish_dir.as_posix()}"\n\n'
        "[[redirects]]\n"
        '  from = "/*"\n'
        '  to = "/index.html"\n'
        "  status = 200\n"
    )


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except Exception:
            pass

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, timedelta):
        return str(value)

    if pd is not None:
        if isinstance(value, pd.DataFrame):
            records = value.to_dict(orient="records")
            return [_json_safe(record) for record in records]
        if isinstance(value, pd.Series):
            return {str(key): _json_safe(item) for key, item in value.to_dict().items()}
        if pd.api.types.is_timedelta64_dtype(getattr(value, "dtype", None)):
            return value.astype(str).tolist()

    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]

    return str(value)


def serialize_backtest_result(result: Any) -> dict[str, Any]:
    """Convert the Python backtest output into JSON-friendly data for the web UI."""
    if not isinstance(result, dict):
        return {"status": "success", "output": str(result)}

    payload = {
        key: _json_safe(value)
        for key, value in result.items()
        if key not in {"stats_file", "fig_file"}
    }

    stats_file = result.get("stats_file")
    if stats_file:
        stats_path = Path(stats_file)
        if stats_path.exists():
            with stats_path.open("rb") as handle:
                raw_stats = pickle.load(handle)

            stats_mapping = _json_safe(raw_stats)
            payload["stats"] = (
                {
                    str(key): value
                    for key, value in dict(stats_mapping).items()
                    if key != "_trades"
                }
                if isinstance(stats_mapping, Mapping)
                else stats_mapping
            )

            if isinstance(raw_stats, Mapping):
                trades = raw_stats.get("_trades")
            elif pd is not None and isinstance(raw_stats, pd.Series):
                trades = raw_stats.get("_trades")
            else:
                trades = None

            payload["stats_summary"] = payload.get("stats", {})
            payload["trades"] = _json_safe(trades) if trades is not None else []

    fig_file = result.get("fig_file")
    if fig_file:
        fig_path = Path(fig_file)
        if fig_path.exists():
            payload["figure_html"] = fig_path.read_text(encoding="utf-8")

    return payload


def build_netlify_dashboard(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    api_base_url: str | None = None,
    api_path: str = DEFAULT_API_PATH,
) -> Path:
    """Write a static dashboard that Netlify can publish directly."""
    resolved_output_dir = Path(output_dir)
    assets_dir = resolved_output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    api_base_url = api_base_url or os.getenv("NETLIFY_BACKTEST_API_BASE_URL", "").strip()
    api_path = (api_path or os.getenv("NETLIFY_BACKTEST_API_PATH", DEFAULT_API_PATH)).strip() or DEFAULT_API_PATH

    (resolved_output_dir / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (resolved_output_dir / "config.js").write_text(
        _default_config_js(api_base_url=api_base_url, api_path=api_path),
        encoding="utf-8",
    )
    (assets_dir / "styles.css").write_text(STYLES_CSS, encoding="utf-8")
    (assets_dir / "app.js").write_text(APP_JS, encoding="utf-8")
    (Path.cwd() / "netlify.toml").write_text(_netlify_toml(resolved_output_dir), encoding="utf-8")

    return resolved_output_dir


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Netlify dashboard assets.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where the static frontend should be written.",
    )
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("NETLIFY_BACKTEST_API_BASE_URL", ""),
        help="Default API base URL to prefill in config.js.",
    )
    parser.add_argument(
        "--api-path",
        default=os.getenv("NETLIFY_BACKTEST_API_PATH", DEFAULT_API_PATH),
        help="Endpoint path appended to the API base URL.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    output_dir = build_netlify_dashboard(
        output_dir=Path(args.output_dir),
        api_base_url=args.api_base_url,
        api_path=args.api_path,
    )
    print(f"Netlify dashboard written to {output_dir}")


if __name__ == "__main__":
    main()
