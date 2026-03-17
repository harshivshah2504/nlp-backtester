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
    <div class="page-shell">
      <header class="hero">
        <p class="eyebrow">Netlify-ready frontend</p>
        <div class="hero-copy">
          <h1>Backtest Crew Console</h1>
          <p>
            Static UI for generating trading strategies from natural language.
            Host this on Netlify and point it at a separate HTTP API that runs
            the Python crew.
          </p>
        </div>
        <div class="hero-card">
          <span class="hero-card-label">Runtime model</span>
          <strong>Static app + remote API</strong>
          <p>
            The deployed site is browser-only. The backtest engine stays on a
            Python host and returns JSON.
          </p>
        </div>
      </header>

      <main class="layout">
        <section class="panel panel-form">
          <div class="panel-header">
            <h2>Run Strategy Generator</h2>
            <p>Submit a trading idea and render the backtest response.</p>
          </div>

          <label class="field">
            <span>Backtest API base URL</span>
            <input
              id="apiBaseUrl"
              type="url"
              placeholder="https://your-backend.example.com"
              spellcheck="false"
            />
          </label>

          <label class="field">
            <span>Endpoint path</span>
            <input
              id="apiPath"
              type="text"
              placeholder="/api/backtest"
              value="/api/backtest"
              spellcheck="false"
            />
          </label>

          <label class="field">
            <span>Trading strategy idea</span>
            <textarea
              id="query"
              rows="10"
              placeholder="Build a long-short technical strategy for MSFT from 2024-01-01 with ATR-based stops and adaptive risk sizing."
            ></textarea>
          </label>

          <div class="actions">
            <button id="runButton" class="primary-button">Run Backtest</button>
            <button id="saveConfigButton" class="secondary-button" type="button">
              Save Endpoint
            </button>
          </div>

          <div id="statusBanner" class="status-banner info">
            Configure the API endpoint, then run a strategy.
          </div>
        </section>

        <aside class="panel panel-side">
          <div class="panel-header">
            <h2>Expected API</h2>
            <p>POST JSON payload with a single <code>query</code> field.</p>
          </div>
          <pre class="api-contract"><code>{
  "query": "Build a momentum strategy for NVDA..."
}</code></pre>
          <p class="panel-note">
            The response can either be the raw result object or
            <code>{ "result": ... }</code>. If you use the serializer in
            <code>backtest_crew/dashboard.py</code>, the frontend already knows
            how to render it.
          </p>
        </aside>

        <section class="panel panel-results">
          <div class="panel-header">
            <h2>Result</h2>
            <p id="resultMeta">No run yet.</p>
          </div>

          <div id="summaryCards" class="summary-grid empty-state">
            Backtest summary metrics will appear here.
          </div>

          <div class="result-block">
            <h3>Trades</h3>
            <div id="tradesTable" class="table-shell empty-state">
              No trades to show.
            </div>
          </div>

          <div class="result-block">
            <h3>Equity Curve</h3>
            <div id="figureContainer" class="figure-shell empty-state">
              No visualization returned.
            </div>
          </div>

          <div class="result-block">
            <h3>Generated Strategy Code</h3>
            <pre id="codeBlock" class="code-shell empty-state"><code>No code generated yet.</code></pre>
          </div>

          <div class="result-block">
            <h3>Raw Output</h3>
            <pre id="outputBlock" class="code-shell empty-state"><code>No output yet.</code></pre>
          </div>
        </section>
      </main>
    </div>

    <script src="./config.js"></script>
    <script src="./assets/app.js"></script>
  </body>
</html>
"""


STYLES_CSS = """:root {
  --bg: #f4efe4;
  --bg-accent: radial-gradient(circle at top left, rgba(194, 120, 64, 0.18), transparent 34%),
    radial-gradient(circle at top right, rgba(9, 71, 86, 0.18), transparent 30%),
    linear-gradient(180deg, #f7f2e8 0%, #efe5d4 100%);
  --panel: rgba(255, 250, 240, 0.78);
  --panel-border: rgba(15, 45, 52, 0.14);
  --ink: #172628;
  --muted: #55686d;
  --accent: #0d596a;
  --accent-strong: #093f4a;
  --accent-warm: #ba6a33;
  --success: #1f7a4d;
  --error: #a33d2b;
  --info: #325c84;
  --shadow: 0 18px 48px rgba(30, 41, 59, 0.12);
  --radius-lg: 26px;
  --radius-md: 18px;
  --radius-sm: 12px;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  font-family: "Space Grotesk", sans-serif;
  color: var(--ink);
  background: var(--bg-accent);
}

code,
pre,
input,
textarea {
  font-family: "IBM Plex Mono", monospace;
}

.page-shell {
  width: min(1240px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 32px 0 48px;
}

.hero {
  display: grid;
  grid-template-columns: 1.7fr 0.9fr;
  gap: 20px;
  align-items: stretch;
  margin-bottom: 22px;
}

.hero-copy,
.hero-card,
.panel {
  backdrop-filter: blur(16px);
  background: var(--panel);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
}

.hero-copy {
  padding: 30px;
  position: relative;
  overflow: hidden;
}

.hero-copy::after {
  content: "";
  position: absolute;
  right: -40px;
  bottom: -60px;
  width: 180px;
  height: 180px;
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(13, 89, 106, 0.14), rgba(186, 106, 51, 0.22));
}

.eyebrow {
  margin: 0 0 10px;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 0.78rem;
  color: var(--accent);
}

.hero h1,
.panel h2,
.result-block h3 {
  margin: 0;
}

.hero h1 {
  font-size: clamp(2.2rem, 4vw, 4.5rem);
  line-height: 0.95;
  max-width: 12ch;
}

.hero-copy p,
.hero-card p,
.panel-header p,
.panel-note,
.status-banner {
  color: var(--muted);
}

.hero-copy p {
  max-width: 62ch;
  margin: 16px 0 0;
  line-height: 1.6;
}

.hero-card {
  padding: 24px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10px;
}

.hero-card-label {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--accent-warm);
}

.layout {
  display: grid;
  grid-template-columns: 1.05fr 0.7fr;
  gap: 20px;
}

.panel {
  padding: 24px;
}

.panel-results {
  grid-column: 1 / -1;
}

.panel-header {
  margin-bottom: 18px;
}

.panel-header p {
  margin: 8px 0 0;
  line-height: 1.5;
}

.field {
  display: grid;
  gap: 8px;
  margin-bottom: 16px;
}

.field span {
  font-size: 0.92rem;
  font-weight: 700;
}

input,
textarea {
  width: 100%;
  border: 1px solid rgba(9, 63, 74, 0.18);
  background: rgba(255, 255, 255, 0.72);
  color: var(--ink);
  border-radius: var(--radius-sm);
  padding: 14px 16px;
  font-size: 0.95rem;
  transition: border-color 120ms ease, transform 120ms ease, background 120ms ease;
}

input:focus,
textarea:focus {
  outline: none;
  border-color: rgba(13, 89, 106, 0.52);
  background: rgba(255, 255, 255, 0.94);
  transform: translateY(-1px);
}

textarea {
  resize: vertical;
  min-height: 220px;
}

.actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

button {
  border: none;
  border-radius: 999px;
  padding: 13px 18px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
  transition: transform 120ms ease, opacity 120ms ease, box-shadow 120ms ease;
}

button:hover {
  transform: translateY(-1px);
}

button:disabled {
  cursor: wait;
  opacity: 0.72;
}

.primary-button {
  background: linear-gradient(135deg, var(--accent), var(--accent-strong));
  color: #fff8ef;
  box-shadow: 0 12px 24px rgba(9, 63, 74, 0.18);
}

.secondary-button {
  background: rgba(255, 255, 255, 0.72);
  color: var(--accent-strong);
  border: 1px solid rgba(9, 63, 74, 0.14);
}

.status-banner,
.api-contract,
.summary-card,
.table-shell,
.figure-shell,
.code-shell {
  border-radius: var(--radius-md);
}

.status-banner {
  margin-top: 18px;
  padding: 14px 16px;
  border: 1px solid transparent;
  background: rgba(50, 92, 132, 0.08);
}

.status-banner.info {
  color: var(--info);
  border-color: rgba(50, 92, 132, 0.16);
}

.status-banner.success {
  color: var(--success);
  border-color: rgba(31, 122, 77, 0.18);
  background: rgba(31, 122, 77, 0.08);
}

.status-banner.error {
  color: var(--error);
  border-color: rgba(163, 61, 43, 0.18);
  background: rgba(163, 61, 43, 0.08);
}

.api-contract,
.code-shell {
  margin: 0;
  padding: 16px;
  overflow: auto;
  background: #112126;
  color: #eff8f0;
}

.panel-note {
  margin-bottom: 0;
  line-height: 1.6;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 14px;
  margin-bottom: 22px;
}

.summary-card {
  min-height: 118px;
  padding: 16px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(244, 239, 228, 0.88));
  border: 1px solid rgba(9, 63, 74, 0.1);
}

.summary-card-label {
  display: block;
  margin-bottom: 10px;
  font-size: 0.8rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}

.summary-card-value {
  display: block;
  font-size: 1.35rem;
  font-weight: 700;
  line-height: 1.2;
}

.result-block + .result-block {
  margin-top: 18px;
}

.result-block h3 {
  margin-bottom: 10px;
}

.table-shell,
.figure-shell {
  min-height: 160px;
  overflow: auto;
  background: rgba(255, 255, 255, 0.66);
  border: 1px solid rgba(9, 63, 74, 0.1);
  padding: 12px;
}

.table-shell table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.92rem;
}

.table-shell th,
.table-shell td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid rgba(9, 63, 74, 0.08);
  white-space: nowrap;
}

.table-shell th {
  position: sticky;
  top: 0;
  background: #f2e8d9;
}

.figure-shell iframe {
  width: 100%;
  min-height: 620px;
  border: none;
  border-radius: 10px;
  background: white;
}

.code-shell {
  min-height: 160px;
  line-height: 1.6;
}

.empty-state {
  display: grid;
  place-items: center;
  color: var(--muted);
}

@media (max-width: 1024px) {
  .hero,
  .layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .page-shell {
    width: min(100vw - 20px, 1240px);
    padding-top: 18px;
  }

  .hero-copy,
  .hero-card,
  .panel {
    border-radius: 20px;
  }

  .panel {
    padding: 18px;
  }

  .actions {
    flex-direction: column;
  }

  button {
    width: 100%;
  }
}
"""


APP_JS = """const CONFIG_STORAGE_KEY = "backtest-crew-config";
const DEFAULT_CONFIG = window.__BACKTEST_CONFIG__ || {};

const elements = {
  apiBaseUrl: document.getElementById("apiBaseUrl"),
  apiPath: document.getElementById("apiPath"),
  query: document.getElementById("query"),
  runButton: document.getElementById("runButton"),
  saveConfigButton: document.getElementById("saveConfigButton"),
  statusBanner: document.getElementById("statusBanner"),
  resultMeta: document.getElementById("resultMeta"),
  summaryCards: document.getElementById("summaryCards"),
  tradesTable: document.getElementById("tradesTable"),
  figureContainer: document.getElementById("figureContainer"),
  codeBlock: document.getElementById("codeBlock"),
  outputBlock: document.getElementById("outputBlock"),
};

function readSavedConfig() {
  try {
    return JSON.parse(localStorage.getItem(CONFIG_STORAGE_KEY) || "{}");
  } catch (_) {
    return {};
  }
}

function getConfig() {
  const fallbackBaseUrl =
    DEFAULT_CONFIG.apiBaseUrl ||
    (window.location.protocol.startsWith("http") ? window.location.origin : "");

  return {
    apiBaseUrl: elements.apiBaseUrl.value.trim() || fallbackBaseUrl,
    apiPath: elements.apiPath.value.trim() || "/api/backtest",
  };
}

function saveConfig() {
  localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(getConfig()));
  setStatus("Endpoint saved in this browser.", "success");
}

function setStatus(message, tone = "info") {
  elements.statusBanner.className = `status-banner ${tone}`;
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
  const entries = Object.entries(summary || {}).filter(([key, value]) => {
    if (key === "_trades") {
      return false;
    }

    const valueType = typeof value;
    return valueType !== "object" || value === null;
  });

  if (!entries.length) {
    elements.summaryCards.className = "summary-grid empty-state";
    elements.summaryCards.textContent = "Backtest summary metrics will appear here.";
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
    elements.tradesTable.textContent = "No trades to show.";
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
      const value = row?.[column];
      td.textContent = value == null ? "" : String(value);
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

  if (figureHtml) {
    const iframe = document.createElement("iframe");
    iframe.loading = "lazy";
    iframe.referrerPolicy = "no-referrer";
    iframe.srcdoc = figureHtml;
    elements.figureContainer.className = "figure-shell";
    elements.figureContainer.replaceChildren(iframe);
    return;
  }

  if (figureUrl) {
    const iframe = document.createElement("iframe");
    iframe.loading = "lazy";
    iframe.referrerPolicy = "no-referrer";
    iframe.src = figureUrl;
    elements.figureContainer.className = "figure-shell";
    elements.figureContainer.replaceChildren(iframe);
    return;
  }

  elements.figureContainer.className = "figure-shell empty-state";
  elements.figureContainer.textContent = "No visualization returned.";
}

function renderResult(result) {
  renderSummaryCards(result || {});
  renderTradesTable(result || {});
  renderFigure(result || {});
  setTextCodeBlock(elements.codeBlock, result?.final_code || "", "No code generated yet.");
  setTextCodeBlock(
    elements.outputBlock,
    result?.output || result?.error || "",
    "No output yet."
  );

  const attempts = result?.attempts_taken ? `Attempts: ${result.attempts_taken}` : "Attempts: n/a";
  const status = result?.status || "unknown";
  elements.resultMeta.textContent = `Status: ${status} | ${attempts}`;
}

async function runBacktest() {
  const query = elements.query.value.trim();
  const config = getConfig();

  if (!config.apiBaseUrl) {
    setStatus("Enter the API base URL first.", "error");
    return;
  }

  if (!query) {
    setStatus("Enter a strategy idea before running the backtest.", "error");
    return;
  }

  const baseUrl = config.apiBaseUrl.replace(/\\/$/, "");
  const path = config.apiPath.startsWith("/") ? config.apiPath : `/${config.apiPath}`;
  const requestUrl = `${baseUrl}${path}`;

  elements.runButton.disabled = true;
  setStatus(`Running backtest via ${requestUrl}`, "info");
  elements.resultMeta.textContent = "Request in progress...";

  try {
    const response = await fetch(requestUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
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
    setStatus("Backtest completed.", result?.status === "failed" ? "error" : "success");
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    renderResult({ status: "failed", error: message });
    setStatus(`Request failed: ${message}`, "error");
  } finally {
    elements.runButton.disabled = false;
  }
}

function bootstrap() {
  const saved = readSavedConfig();
  elements.apiBaseUrl.value = saved.apiBaseUrl || DEFAULT_CONFIG.apiBaseUrl || "";
  elements.apiPath.value = saved.apiPath || DEFAULT_CONFIG.apiPath || "/api/backtest";
  elements.query.value = DEFAULT_CONFIG.exampleQuery || "";

  elements.runButton.addEventListener("click", runBacktest);
  elements.saveConfigButton.addEventListener("click", saveConfig);
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
