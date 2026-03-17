const DEFAULT_CONFIG = window.__BACKTEST_CONFIG__ || {};

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
