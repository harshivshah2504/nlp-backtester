const DEFAULT_CONFIG = window.__BACKTEST_CONFIG__ || {};

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
  return `${baseUrl.replace(/\/$/, "")}${apiPath.startsWith("/") ? apiPath : `/${apiPath}`}`;
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
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return '"' + str.replace(/"/g, '""') + '"';
  }
  return str;
}

function arrayToCsv(headers, rows) {
  const lines = [headers.map(escapeCsvCell).join(",")];
  rows.forEach(row => {
    lines.push(headers.map(h => escapeCsvCell(row[h])).join(","));
  });
  return lines.join("\n");
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

  downloadCsv(parts.join("\n"), "backtest_report.csv");
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
