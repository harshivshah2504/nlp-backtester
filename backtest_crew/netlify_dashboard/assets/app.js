const CONFIG_STORAGE_KEY = "backtest-crew-config";
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

  const baseUrl = config.apiBaseUrl.replace(/\/$/, "");
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
