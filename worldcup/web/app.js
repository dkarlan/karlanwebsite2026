// World Cup Happiness Index 2026 - results-first guide.
// Reads rankings.json (written by the pipeline). A flipped bar chart, one bar per
// country, sorted by the active view. Each bar shows the country, its Best Prior
// World Cup result and where it is Expected to Reach; hover for the full detail.
// Tick countries and hit the compare button for a side-by-side table.
// Two views: Performance relative to expectations (default) and absolute. Win
// probability never weights the score; under the relative view it only sets the bar.

const HOME_ADV = 60;  // Elo bump for host nations, matches the model

const VIEWS = {
  surprise: {
    key: "surprise_index",
    label: "Performance, relative to expectations",
    note: "Joy from overperforming: a deep run weighted by how unlikely it was, " +
      "with later rounds counting more. The bar is each team's pre-tournament odds; " +
      "those odds set the bar, they never shrink the score.",
  },
  rooting: {
    key: "rooting_index",
    label: "Performance, absolute",
    note: "The happiness a title itself would add, full stop: fans reached, weighted " +
      "up where people have less, valued by the lingering memory of a win.",
  },
};

let DATA = null;
let byName = {};
let view = "surprise";
let timeframe = "live";           // "live" or "pre"
let shownName = null;             // country whose detail card is open (click to toggle)
const selected = new Set();        // countries ticked for comparison

function activeKey() {
  if (view === "rooting") return "rooting_index";
  return timeframe === "pre" ? "surprise_index_pre" : "surprise_index";
}

function fmtInt(n) { return n.toLocaleString("en-US"); }
function fmtM(n) { return (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + "M"; }
function pWin(a, b) {
  const ea = a.elo + (a.host ? HOME_ADV : 0);
  const eb = b.elo + (b.host ? HOME_ADV : 0);
  return 1 / (1 + Math.pow(10, -(ea - eb) / 400));
}

// Best prior World Cup result and expected finish, in one shared round vocabulary.
function bestPrior(code) {
  return {
    won: "Won it", final: "Final", semi: "Semifinals", quarter: "Quarterfinals",
    round16: "Round of 16", group: "Group stage", first: "First time",
  }[code] || "unknown";
}
function expStage(d) {
  if (d < 0.5) return "Group stage";
  if (d < 1.5) return "Round of 32";
  if (d < 2.5) return "Round of 16";
  if (d < 3.5) return "Quarterfinals";
  if (d < 4.5) return "Semifinals";
  return "Final";
}
function stageAbbr(full) {
  return {
    "Won it": "Won", "Final": "Fin", "Semifinals": "SF", "Quarterfinals": "QF",
    "Round of 16": "R16", "Round of 32": "R32", "Group stage": "Grp", "First time": "1st",
  }[full] || full;
}
function shortName(n) {
  return {
    "Bosnia and Herzegovina": "Bosnia", "United States": "USA", "South Africa": "S. Africa",
    "South Korea": "S. Korea", "Saudi Arabia": "Saudi", "New Zealand": "N. Zealand",
    "Cote d'Ivoire": "Ivory Coast",
  }[n] || n;
}
function statusText(t) {
  return t.eliminated ? "Out"
    : (t.reached_depth > 0 ? "Still in (knockouts)" : "Still in (group stage)");
}

// One source of truth for every data value, used by the hover card and the
// comparison table.
function detailRows(t) {
  return [
    ["Performance, relative (live)", t.surprise_index.toFixed(1)],
    ["Performance, relative (pre)", t.surprise_index_pre.toFixed(1)],
    ["Performance, absolute", t.rooting_index.toFixed(1)],
    ["Expected to Reach", expStage(t.expected_depth)],
    ["Best Prior World Cup", bestPrior(t.best_finish)],
    ["Status", statusText(t)],
    ["World Cup titles", String(t.wc_titles)],
    ["Last major trophy", t.last_major_year === null ? "none" : String(t.last_major_year)],
    ["Memory half-life", t.memory_half_life + " yrs"],
    ["Fans reached", fmtM(t.fan_population)],
    ["&nbsp;&nbsp;home", fmtM(t.home_fans)],
    ["&nbsp;&nbsp;diaspora", fmtM(t.diaspora_fans)],
    ["&nbsp;&nbsp;continental solidarity", fmtM(t.solidarity_fans)],
    ["Consumption (GNI pc, PPP)", "$" + fmtInt(t.consumption)],
    ["Marginal-utility weight", t.mu_weight.toFixed(2) + "x"],
    ["Elo rating", String(t.elo)],
  ];
}

async function load() {
  const res = await fetch("rankings.json");
  DATA = await res.json();
  byName = Object.fromEntries(DATA.teams.map((t) => [t.name, t]));
  bindToggle();
  document.getElementById("compare-btn").addEventListener("click", renderCompareTable);

  const chart = document.getElementById("chart");
  chart.addEventListener("click", (e) => {
    if (e.target.classList.contains("col-check")) return;   // checkbox: handled below
    const el = e.target.closest("[data-name]");
    if (!el) { hideCard(); shownName = null; return; }       // empty chart space
    const n = el.dataset.name;
    if (shownName === n) { hideCard(); shownName = null; }
    else { showCard(byName[n], el); shownName = n; }
  });
  // Click anywhere else on the page closes the open detail card.
  document.addEventListener("click", (e) => {
    if (shownName !== null && !e.target.closest("#chart")) { hideCard(); shownName = null; }
  });
  chart.addEventListener("change", (e) => {
    if (!e.target.classList.contains("col-check")) return;
    const n = e.target.dataset.name;
    if (e.target.checked) selected.add(n); else selected.delete(n);
    updateCompareCount();
    if (!document.getElementById("compare-table").classList.contains("hidden")) renderCompareTable();
  });

  refresh();
  renderMeta();
}

function teamsByView() {
  const key = activeKey();
  return [...DATA.teams].sort((a, b) => b[key] - a[key]);
}

function refresh() {
  document.getElementById("time-toggle").classList.toggle("muted", view === "rooting");
  renderHeadline();
  renderChart();
  renderMatches();
  if (!document.getElementById("compare-table").classList.contains("hidden")) renderCompareTable();
}

function bindToggle() {
  document.querySelectorAll("#view-toggle button").forEach((btn) => {
    btn.addEventListener("click", () => {
      view = btn.dataset.view;
      document.querySelectorAll("#view-toggle button").forEach((b) => b.classList.toggle("active", b === btn));
      refresh();
    });
  });
  document.querySelectorAll("#time-toggle button").forEach((btn) => {
    btn.addEventListener("click", () => {
      timeframe = btn.dataset.time;
      document.querySelectorAll("#time-toggle button").forEach((b) => b.classList.toggle("active", b === btn));
      refresh();
    });
  });
}

function renderHeadline() {
  const top = teamsByView()[0];
  document.getElementById("headline").innerHTML = view === "rooting"
    ? `For the biggest prize if they win, root for <b>${top.name}</b>.`
    : `Right now, root for <b>${top.name}</b>: odds are low for them, the following is large and incomes low, so every round they survive lands where it counts.`;
}

function renderChart() {
  hideCard(); shownName = null;
  let note = VIEWS[view].note;
  if (view !== "rooting") {
    note += timeframe === "pre"
      ? " Showing the frozen pre-tournament ranking."
      : " Showing the live ranking, updated for results so far.";
  }
  document.getElementById("view-note").textContent = note;

  const key = activeKey();
  const teams = teamsByView();
  const max = Math.max(...teams.map((t) => t[key])) || 1;
  const chart = document.getElementById("chart");
  chart.style.gridTemplateColumns = `96px repeat(${teams.length}, minmax(0, 1fr))`;

  const bars = teams.map((t, i) => {
    const h = Math.max(2, (t[key] / max) * 100);
    const cls = "barcell" + (i === 0 ? " top" : "") + (t.eliminated ? " out" : "");
    return `<div class="${cls}" data-name="${t.name}"><div class="bval">${t[key].toFixed(0)}</div><div class="bar" style="height:${h}%"></div></div>`;
  }).join("");
  const names = teams.map((t) => `<div class="namecell" data-name="${t.name}"><span>${shortName(t.name)}</span></div>`).join("");
  const priors = teams.map((t) => `<div class="abbr prior" data-name="${t.name}">${stageAbbr(bestPrior(t.best_finish))}</div>`).join("");
  const exps = teams.map((t) => `<div class="abbr exp" data-name="${t.name}">${stageAbbr(expStage(t.expected_depth))}</div>`).join("");
  const checks = teams.map((t) => `<div class="checkcell"><input type="checkbox" class="col-check" ${selected.has(t.name) ? "checked" : ""} data-name="${t.name}" aria-label="compare ${t.name}"></div>`).join("");

  chart.innerHTML =
    `<div class="g-blank"></div>${bars}` +
    `<div class="g-blank"></div>${names}` +
    `<div class="g-label">Best Prior</div>${priors}` +
    `<div class="g-label">2026 Expectation</div>${exps}` +
    `<div class="g-blank"></div>${checks}`;
  updateCompareCount();
}

function updateCompareCount() {
  document.getElementById("compare-count").textContent =
    selected.size ? `${selected.size} selected` : "none selected";
}

function showCard(t, el) {
  const tip = document.getElementById("tooltip");
  tip.innerHTML =
    `<div class="tip-title">${t.name}</div>` +
    `<div class="tip-sub">${t.confederation} &middot; Group ${t.group}${t.host ? " &middot; Host" : ""}</div>` +
    detailRows(t).map(([k, v]) => `<div class="kv"><span class="k">${k}</span><span class="v">${v}</span></div>`).join("");
  tip.classList.remove("hidden");
  // Anchor to the top of the bars, near the hovered one, so it never covers the
  // checkbox row at the bottom.
  const wrap = document.querySelector(".chart-wrap").getBoundingClientRect();
  const chartBox = document.getElementById("chart").getBoundingClientRect();
  const r = el.getBoundingClientRect();
  const w = 226;
  let left = r.left - wrap.left + r.width / 2 - w / 2;
  left = Math.max(6, Math.min(left, wrap.width - w - 6));
  tip.style.left = left + "px";
  tip.style.top = (chartBox.top - wrap.top + 6) + "px";
}
function hideCard() { document.getElementById("tooltip").classList.add("hidden"); }

function renderCompareTable() {
  const el = document.getElementById("compare-table");
  el.classList.remove("hidden");
  const cols = teamsByView().filter((t) => selected.has(t.name));
  if (!cols.length) {
    el.innerHTML = '<p class="empty">Tick the box under any countries in the chart, then this table compares them side by side.</p>';
    return;
  }
  const labels = detailRows(cols[0]).map(([k]) => k);
  const bodies = cols.map((t) => detailRows(t).map(([, v]) => v));
  const rows = labels.map((lab, ri) =>
    `<tr><th>${lab}</th>${bodies.map((b) => `<td>${b[ri]}</td>`).join("")}</tr>`).join("");
  el.innerHTML =
    `<div class="ct-head"><h3>Comparing ${cols.length} ${cols.length === 1 ? "country" : "countries"}</h3>` +
    `<button id="ct-close" aria-label="close comparison">Close &times;</button></div>` +
    `<div class="ct-scroll"><table><thead><tr><th></th>${cols.map((t) => `<th>${t.name}</th>`).join("")}</tr></thead>` +
    `<tbody>${rows}</tbody></table></div>`;
  document.getElementById("ct-close").addEventListener("click", () => el.classList.add("hidden"));
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

const TODAY = "2026-06-19";
function fmtDate(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  const wd = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][dt.getUTCDay()];
  const mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m - 1];
  return `${wd} ${d} ${mon}`;
}

function renderMatches() {
  const host = document.getElementById("matches");
  const upcoming = DATA.fixtures
    .filter((f) => f.date >= TODAY)
    .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : a.group < b.group ? -1 : 1));
  host.innerHTML = "";
  if (!upcoming.length) {
    host.innerHTML = '<p class="empty">No upcoming fixtures with both teams set.</p>';
    return;
  }
  const key = activeKey();
  upcoming.forEach((f) => {
    const h = byName[f.home], a = byName[f.away];
    const homePick = h[key] >= a[key];   // root for the higher score from the table
    const el = document.createElement("div");
    el.className = "match";
    el.innerHTML =
      `<span class="m-date">${fmtDate(f.date)}</span>` +
      `<span class="m-grp">Grp ${f.group}</span>` +
      `<span class="m-pair">` +
        `<span class="m-team ${homePick ? "pick" : ""}">${h.name} <i>${h[key].toFixed(0)}</i></span>` +
        `<span class="m-v">v</span>` +
        `<span class="m-team right ${homePick ? "" : "pick"}">${a.name} <i>${a[key].toFixed(0)}</i></span>` +
      `</span>`;
    host.appendChild(el);
  });
}

function renderMeta() {
  const p = DATA.meta.params;
  document.getElementById("meta").innerHTML =
    `Updated ${DATA.meta.generated.slice(0, 10)} &middot; basis: ${DATA.meta.basis} &middot; ` +
    `<code>eta=${p.eta}</code> ` +
    `<code>memory half-life ${(Math.log(2) / p.r_lo).toFixed(0)}y to ${(Math.log(2) / p.r_hi).toFixed(1)}y</code> ` +
    `<code>later-round weight exp=${p.stage_weight_exp}</code> ` +
    `<code>${fmtInt(p.mc_iterations)} sims for the bar</code>. Methods in the appendix above.`;
}

load();
