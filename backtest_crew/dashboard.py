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
    <meta name="description" content="AI-powered backtesting strategy generator. Describe a trading strategy in plain English and get executable backtest code with results." />
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
        <div class="input-actions">
          <button id="runButton" type="button">Run</button>
          <button id="exportCsvButton" type="button" class="btn-secondary" disabled>&#x2913; Export CSV</button>
        </div>
        <div id="statusBanner" class="status-banner">Ready.</div>
      </section>

      <section class="output-grid">
        <div class="output-box">
          <div class="output-title">Summary</div>
          <div id="resultMeta" class="meta-text">No run yet.</div>
          <div id="summaryCards" class="summary-grid empty-state">No result.</div>
        </div>

        <div class="output-box">
          <div class="output-title-row">
            <div class="output-title">Strategy Interpretation</div>
            <span class="panel-badge">AI Explainability</span>
          </div>
          <div id="strategyInterpretation" class="interpretation-panel empty-state">No interpretation yet.</div>
        </div>

        <div class="output-box">
          <div class="output-title-row">
            <div class="output-title">Trades</div>
            <button id="exportTradesCsvButton" type="button" class="btn-small" disabled>&#x2913; CSV</button>
          </div>
          <div id="tradesTable" class="table-shell empty-state">No trades.</div>
        </div>

        <div class="output-box">
          <div class="output-title">Chart</div>
          <div id="figureContainer" class="figure-shell empty-state">No chart.</div>
        </div>

        <div class="output-box">
          <details id="codeDetails" class="code-details">
            <summary class="code-summary">View Code</summary>
            <pre id="codeBlock" class="code-shell empty-state"><code>No code.</code></pre>
          </details>
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
  --interpret-bg: #f0f4ff;
  --interpret-border: #c7d2fe;
  --interpret-label: #4338ca;
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

.input-actions {
  display: flex;
  gap: 10px;
  align-items: center;
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
  transition: opacity 0.15s ease, transform 0.1s ease;
}

button:hover:not(:disabled) {
  opacity: 0.88;
  transform: translateY(-1px);
}

button:active:not(:disabled) {
  transform: translateY(0);
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: transparent;
  color: var(--accent);
  border: 1.5px solid var(--border);
}

.btn-secondary:hover:not(:disabled) {
  border-color: var(--accent);
  background: rgba(17, 17, 17, 0.04);
}

.btn-small {
  margin-top: 0;
  padding: 5px 12px;
  font-size: 0.78rem;
  background: transparent;
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 8px;
}

.btn-small:hover:not(:disabled) {
  color: var(--accent);
  border-color: var(--accent);
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

.output-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.output-title-row .output-title {
  margin-bottom: 0;
}

.panel-badge {
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--interpret-bg);
  color: var(--interpret-label);
  border: 1px solid var(--interpret-border);
}

.meta-text {
  margin-bottom: 10px;
  color: var(--muted);
  font-size: 0.9rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 8px;
}

.summary-row {
  display: grid;
  grid-template-columns: minmax(120px, 180px) minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px;
  background: #fcfcfa;
}

.summary-label {
  color: var(--muted);
  font-size: 0.8rem;
  text-transform: uppercase;
  line-height: 1.35;
}

.summary-value {
  min-width: 0;
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.92rem;
  font-weight: 600;
  line-height: 1.45;
  overflow-wrap: anywhere;
  word-break: break-word;
}

/* --- Strategy Interpretation Panel --- */
.interpretation-panel {
  border: 1px solid var(--interpret-border);
  border-radius: 12px;
  background: var(--interpret-bg);
  padding: 16px;
  min-height: 72px;
}

.interpretation-panel.empty-state {
  display: grid;
  place-items: center;
  color: var(--muted);
  background: #fcfcfa;
  border-color: var(--border);
}

.interp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 10px;
}

.interp-card {
  background: rgba(255,255,255,0.7);
  border: 1px solid rgba(199,210,254,0.6);
  border-radius: 10px;
  padding: 12px;
}

.interp-card-label {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--interpret-label);
  margin-bottom: 6px;
}

.interp-card-value {
  font-size: 0.88rem;
  line-height: 1.5;
  color: var(--ink);
  white-space: pre-wrap;
  word-break: break-word;
}

/* --- Collapsible Code Block --- */
.code-details {
  border-radius: 12px;
}

.code-summary {
  cursor: pointer;
  font-size: 0.92rem;
  font-weight: 700;
  padding: 10px 0;
  list-style: none;
  display: flex;
  align-items: center;
  gap: 8px;
  user-select: none;
  color: var(--ink);
}

.code-summary::-webkit-details-marker {
  display: none;
}

.code-summary::before {
  content: "\25B6";
  font-size: 0.7rem;
  transition: transform 0.2s ease;
  display: inline-block;
}

.code-details[open] > .code-summary::before {
  transform: rotate(90deg);
}

.code-details .code-shell {
  margin-top: 8px;
  animation: fadeSlideIn 0.25s ease;
}

@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
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

@media (max-width: 700px) {
  .summary-row {
    grid-template-columns: 1fr;
    gap: 6px;
  }
  .input-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
"""


APP_JS = """const DEFAULT_CONFIG = window.__BACKTEST_CONFIG__ || {};

/* ---- Cached last result for CSV export ---- */
let _lastResult = null;

const elements = {
  query: document.getElementById("query"),
  runButton: document.getElementById("runButton"),
  exportCsvButton: document.getElementById("exportCsvButton"),
  exportTradesCsvButton: document.getElementById("exportTradesCsvButton"),
  statusBanner: document.getElementById("statusBanner"),
  resultMeta: document.getElementById("resultMeta"),
  summaryCards: document.getElementById("summaryCards"),
  strategyInterpretation: document.getElementById("strategyInterpretation"),
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

/* ---- Strategy Interpretation (AI Explainability) ---- */

const INTERP_LABELS = {
  ticker: "Ticker",
  start_date: "Start Date",
  end_date: "End Date",
  strategy_task: "Strategy Logic",
  risk_task: "Risk Management",
  trade_task: "Trade Management",
};

function renderStrategyInterpretation(result) {
  const spec = result?.decomposition_spec || null;
  const el = elements.strategyInterpretation;

  if (!spec || typeof spec !== "object" || !Object.keys(spec).length) {
    el.className = "interpretation-panel empty-state";
    el.textContent = "No interpretation yet.";
    return;
  }

  el.className = "interpretation-panel";
  const grid = document.createElement("div");
  grid.className = "interp-grid";

  const orderedKeys = ["ticker", "start_date", "end_date", "strategy_task", "risk_task", "trade_task"];
  const allKeys = [...orderedKeys.filter(k => k in spec), ...Object.keys(spec).filter(k => !orderedKeys.includes(k))];

  allKeys.forEach(key => {
    const card = document.createElement("div");
    card.className = "interp-card";

    const label = document.createElement("div");
    label.className = "interp-card-label";
    label.textContent = INTERP_LABELS[key] || key.replaceAll("_", " ");

    const value = document.createElement("div");
    value.className = "interp-card-value";
    const raw = spec[key];
    value.textContent = typeof raw === "object" ? JSON.stringify(raw, null, 2) : String(raw ?? "");

    card.append(label, value);
    grid.appendChild(card);
  });

  el.replaceChildren(grid);
}

/* ---- Summary Cards ---- */

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
      const row = document.createElement("article");
      row.className = "summary-row";

      const label = document.createElement("span");
      label.className = "summary-label";
      label.textContent = key.replaceAll("_", " ");

      const metric = document.createElement("span");
      metric.className = "summary-value";
      metric.textContent = String(value);

      row.append(label, metric);
      return row;
    })
  );
}

/* ---- Trades Table ---- */

function renderTradesTable(result) {
  const trades = result?.trades || result?.stats?._trades || [];
  if (!Array.isArray(trades) || !trades.length) {
    elements.tradesTable.className = "table-shell empty-state";
    elements.tradesTable.textContent = "No trades.";
    elements.exportTradesCsvButton.disabled = true;
    return;
  }

  elements.exportTradesCsvButton.disabled = false;

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

/* ---- Chart ---- */

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

/* ---- CSV Export / Download ---- */

function escapeCsvCell(value) {
  const str = value == null ? "" : String(value);
  if (str.includes(",") || str.includes('"') || str.includes("\\n")) {
    return '"' + str.replace(/"/g, '""') + '"';
  }
  return str;
}

function arrayToCsv(headers, rows) {
  const lines = [headers.map(escapeCsvCell).join(",")];
  rows.forEach(row => {
    lines.push(headers.map(h => escapeCsvCell(row[h])).join(","));
  });
  return lines.join("\\n");
}

function downloadCsv(csvContent, filename) {
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function exportTradesCsv() {
  if (!_lastResult) return;
  const trades = _lastResult.trades || _lastResult.stats?._trades || [];
  if (!Array.isArray(trades) || !trades.length) return;

  const columns = Array.from(
    trades.reduce((set, row) => { Object.keys(row || {}).forEach(k => set.add(k)); return set; }, new Set())
  );
  const csv = arrayToCsv(columns, trades);
  downloadCsv(csv, "backtest_trades.csv");
}

function exportFullCsv() {
  if (!_lastResult) return;
  const parts = [];

  // Section 1: Summary stats
  const summary = _lastResult.stats_summary || _lastResult.stats || {};
  const summaryEntries = Object.entries(summary).filter(([k, v]) => k !== "_trades" && (typeof v !== "object" || v === null));
  if (summaryEntries.length) {
    parts.push("--- Summary ---");
    parts.push("Metric,Value");
    summaryEntries.forEach(([k, v]) => parts.push(`${escapeCsvCell(k)},${escapeCsvCell(v)}`));
    parts.push("");
  }

  // Section 2: Decomposition spec
  const spec = _lastResult.decomposition_spec;
  if (spec && typeof spec === "object") {
    parts.push("--- Strategy Interpretation ---");
    parts.push("Field,Value");
    Object.entries(spec).forEach(([k, v]) => {
      const valStr = typeof v === "object" ? JSON.stringify(v) : String(v ?? "");
      parts.push(`${escapeCsvCell(k)},${escapeCsvCell(valStr)}`);
    });
    parts.push("");
  }

  // Section 3: Trades
  const trades = _lastResult.trades || _lastResult.stats?._trades || [];
  if (Array.isArray(trades) && trades.length) {
    const columns = Array.from(
      trades.reduce((set, row) => { Object.keys(row || {}).forEach(k => set.add(k)); return set; }, new Set())
    );
    parts.push("--- Trades ---");
    parts.push(arrayToCsv(columns, trades));
  }

  downloadCsv(parts.join("\\n"), "backtest_report.csv");
}

/* ---- Render orchestrator ---- */

function renderResult(result) {
  _lastResult = result || null;

  renderSummaryCards(result || {});
  renderStrategyInterpretation(result || {});
  renderTradesTable(result || {});
  renderFigure(result || {});
  setTextCodeBlock(elements.codeBlock, result?.final_code || "", "No code.");
  setTextCodeBlock(elements.outputBlock, result?.output || result?.error || "", "No output.");

  const status = result?.status || "unknown";
  const attempts = result?.attempts_taken ? `attempts ${result.attempts_taken}` : "attempts n/a";
  elements.resultMeta.textContent = `${status} | ${attempts}`;

  // Enable / disable the main Export CSV button
  elements.exportCsvButton.disabled = !result;
}

/* ---- Run ---- */

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

/* ---- Bootstrap ---- */

function bootstrap() {
  elements.query.value = DEFAULT_CONFIG.exampleQuery || "";
  elements.runButton.addEventListener("click", runBacktest);
  elements.exportCsvButton.addEventListener("click", exportFullCsv);
  elements.exportTradesCsvButton.addEventListener("click", exportTradesCsv);
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
