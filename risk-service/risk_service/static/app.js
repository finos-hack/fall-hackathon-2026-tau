// Risk page for feature 001. No external assets. All figures use SYNTHETIC price history.
"use strict";

const $ = (id) => document.getElementById(id);
const usd = (x) => (x < 0 ? "−$" : "$") + Math.abs(x).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const num = (x, d) => Number(x).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const OUTCOME_TITLES = {
  ACCOUNT_NOT_FOUND: "Account not found",
  NO_OPEN_POSITIONS: "No open positions",
  MISSING_PRICE_HISTORY: "Missing price history",
  ZERO_VOLATILITY: "Zero volatility",
  POSITIONS_UNAVAILABLE: "TraderX unavailable",
  INVALID_REQUEST: "Invalid request",
};

async function getJSON(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  return response.json();
}

async function loadAccounts() {
  const select = $("account");
  try {
    const data = await getJSON("/api/v1/accounts");
    if (!data.accounts) {
      select.innerHTML = '<option value="">Accounts unavailable</option>';
      showOutcome(data);
      return;
    }
    select.innerHTML = '<option value="">Choose an account…</option>' + data.accounts
      .map((a) => `<option value="${esc(a.id)}">${esc(a.id)} — ${esc(a.displayName || "")}</option>`).join("");
    const wanted = new URLSearchParams(location.search).get("account");
    if (wanted) { select.value = wanted; loadRisk(wanted); }
  } catch (err) {
    select.innerHTML = '<option value="">Accounts unavailable</option>';
    $("status").textContent = "Could not reach the risk service: " + err;
  }
}

async function loadRisk(id) {
  if (!id) return;
  history.replaceState(null, "", "?account=" + encodeURIComponent(id));
  $("status").hidden = false;
  $("status").className = "panel muted";
  $("status").textContent = "Computing…";
  try {
    const data = await getJSON("/api/v1/risk/accounts/" + encodeURIComponent(id));
    if (data.outcome === "OK") showOK(data); else showOutcome(data);
  } catch (err) {
    $("result").hidden = true;
    $("status").textContent = "Could not reach the risk service: " + err;
  }
}

function showOutcome(data) {
  $("result").hidden = true;
  const title = OUTCOME_TITLES[data.outcome] || data.outcome;
  let extra = "";
  if (data.missing_securities) extra = "<div>Securities without history: " + data.missing_securities.map(esc).join(", ") + "</div>";
  $("status").hidden = false;
  $("status").className = "";
  $("status").innerHTML = `<div class="outcome"><b>${esc(title)}</b>${esc(data.message || "")}${extra}</div>`;
  showBasis(data.provenance);
}

function showOK(data) {
  $("status").hidden = true;
  $("result").hidden = false;
  const c = data.current;
  $("var").textContent = usd(c.var_usd);
  $("asof").textContent = "data as of " + c.data_as_of + " close";
  $("fcast").textContent = "forecast for " + c.forecast_for;
  $("positions").innerHTML = c.positions.map((p) =>
    `<tr><td>${esc(p.security)}</td><td>${num(p.quantity, 0)}</td><td>${usd(p.price)}</td><td>${usd(p.market_value)}</td></tr>`).join("");
  $("net").textContent = usd(c.net_market_value);
  showVerdict(data.verdict);
  showTrack(data.track_record);
  showBasis(data.provenance);
}

function showVerdict(v) {
  const k = v.kupiec;
  const decision = k.reject_5pct ? `reject at 5% (${k.direction === "too_many" ? "too many" : "too few"} breaches)` : "do not reject at 5%";
  $("verdict").innerHTML = `
    <div class="grid">
      <dl>
        <dt>Breaches</dt><dd><b>${v.breaches}</b> of ${v.observations} days (${num(v.breach_rate * 100, 2)}%)</dd>
        <dt>Nominal expectation</dt><dd>${num(v.expected_breaches_nominal, 1)} (1.00%)</dd>
        <dt>Finite-sample expectation</dt><dd>${num(v.expected_breaches_finite_sample, 1)} (${num(v.finite_sample_rate * 100, 2)}%)</dd>
      </dl>
      <dl>
        <dt>Kupiec LR</dt><dd>${num(k.lr, 4)} (critical ${num(k.critical_value, 4)})</dd>
        <dt>p-value</dt><dd>${num(k.p_value, 4)}</dd>
        <dt>Decision</dt><dd>${esc(decision)}</dd>
        <dt>Basel zone</dt><dd><span class="zone ${esc(v.basel_zone)}">${esc(v.basel_zone)}</span></dd>
      </dl>
    </div>
    <div class="note">${esc(v.note)}</div>`;
}

function showTrack(rows) {
  $("track").innerHTML = rows.map((r) =>
    `<tr class="${r.breach ? "breach" : ""}"><td>${esc(r.date)}</td><td>${r.day}</td><td>${usd(r.forecast_var_usd)}</td><td>${usd(r.realised_pnl_usd)}</td><td>${r.breach ? "BREACH" : ""}</td></tr>`).join("");
  drawChart(rows);
}

function drawChart(rows) {
  const W = 1000, H = 300, padL = 86, padR = 10, padT = 10, padB = 28;
  const lo = Math.min(...rows.map((r) => Math.min(r.realised_pnl_usd, -r.forecast_var_usd)));
  const hi = Math.max(...rows.map((r) => Math.max(r.realised_pnl_usd, 0)));
  const span = (hi - lo) || 1;
  const y = (v) => padT + (hi - v) / span * (H - padT - padB);
  const step = (W - padL - padR) / rows.length;
  const x = (i) => padL + i * step;
  const style = getComputedStyle(document.documentElement);
  const col = (n) => style.getPropertyValue(n).trim();
  let bars = "", marks = "";
  rows.forEach((r, i) => {
    const top = Math.min(y(r.realised_pnl_usd), y(0)), h = Math.abs(y(r.realised_pnl_usd) - y(0));
    bars += `<rect x="${x(i).toFixed(1)}" y="${top.toFixed(1)}" width="${Math.max(step - 1, 1).toFixed(1)}" height="${Math.max(h, 0.5).toFixed(1)}" fill="${r.breach ? col("--breach") : col("--muted")}" opacity="${r.breach ? 1 : 0.55}"><title>${r.date}: P&L ${usd(r.realised_pnl_usd)}, VaR ${usd(r.forecast_var_usd)}${r.breach ? " — BREACH" : ""}</title></rect>`;
    if (r.breach) marks += `<circle cx="${(x(i) + step / 2).toFixed(1)}" cy="${(y(r.realised_pnl_usd) + 6).toFixed(1)}" r="3.5" fill="${col("--breach")}"/>`;
  });
  const line = rows.map((r, i) => `${i ? "L" : "M"}${(x(i) + step / 2).toFixed(1)},${y(-r.forecast_var_usd).toFixed(1)}`).join("");
  const ticks = [lo, lo / 2, 0, hi].map((v) =>
    `<text x="${padL - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end" font-size="11" fill="${col("--muted")}">${usd(v).replace(".00", "")}</text>`).join("");
  const first = rows[0].date, last = rows[rows.length - 1].date;
  $("chart").innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Realised P&L against the −VaR forecast, ${rows.length} days">
    <line x1="${padL}" x2="${W - padR}" y1="${y(0)}" y2="${y(0)}" stroke="${col("--line")}"/>
    ${bars}<path d="${line}" fill="none" stroke="${col("--accent")}" stroke-width="2"/>${marks}${ticks}
    <text x="${padL}" y="${H - 8}" font-size="11" fill="${col("--muted")}">${first}</text>
    <text x="${W - padR}" y="${H - 8}" font-size="11" text-anchor="end" fill="${col("--muted")}">${last}</text></svg>`;
}

function showBasis(p) {
  if (!p) return;
  $("basis-panel").hidden = false;
  const rows = [
    ["Data", p.data], ["Seed", p.seed], ["Method", p.method], ["λ", p.lambda],
    ["Pool size", p.pool_size], ["Warm-up", p.warmup], ["Confidence", p.confidence],
    ["Horizon (days)", p.horizon_days], ["Quantile rule", p.quantile_rule], ["As-of date", p.as_of_date],
    ["Position source", p.position_source], ["Positions read at", p.positions_read_at || "—"],
    ["Data file", p.data_file], ["Data SHA-256", p.data_sha256],
  ];
  $("basis").innerHTML = rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("");
}

$("account").addEventListener("change", (e) => loadRisk(e.target.value));
loadAccounts();
