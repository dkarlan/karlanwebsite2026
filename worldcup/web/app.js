// World Cup Happiness Index 2026 - live "who to root for" tool.
// Reads rankings.json (written by the pipeline). Two ways to value the joy:
//   Performance, relative to expectations (default): a deep run weighted by how
//     unlikely it was, with later rounds counting more. Underdogs rise.
//   Performance, absolute: the happiness a title itself would add, full stop.
// Both use fans reached x marginal-utility weight (always tilted toward the poor)
// x the present value of the lingering memory of a win. Win probability never
// weights the score; under the relative view it only sets the bar.

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
let view = "surprise";
let timeframe = "live";   // "live" (results so far) or "pre" (frozen pre-tournament)

// The index field for the active method and timeframe. The absolute view is a
// fixed prize and ignores the timeframe; the relative view switches on it.
function activeKey() {
  if (view === "rooting") return "rooting_index";
  return timeframe === "pre" ? "surprise_index_pre" : "surprise_index";
}

// A team's best prior World Cup result, as a round name (same vocabulary as the
// expected-finish below, so the two read as a direct comparison).
function bestPrior(code) {
  return {
    won: "Won it", final: "Final", semi: "Semifinals",
    quarter: "Quarterfinals", round16: "Round of 16",
    group: "Group stage", first: "First time",
  }[code] || "unknown";
}

// Expected finish, from expected depth (0 to 6) to a round name.
function expStage(d) {
  if (d < 0.5) return "Group stage";
  if (d < 1.5) return "Round of 32";
  if (d < 2.5) return "Round of 16";
  if (d < 3.5) return "Quarterfinals";
  if (d < 4.5) return "Semifinals";
  return "Final";
}

function fmtInt(n) { return n.toLocaleString("en-US"); }
function fmtM(n) { return (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + "M"; }
function pWin(a, b) {
  const ea = a.elo + (a.host ? HOME_ADV : 0);
  const eb = b.elo + (b.host ? HOME_ADV : 0);
  return 1 / (1 + Math.pow(10, -(ea - eb) / 400));
}

async function load() {
  const res = await fetch("rankings.json");
  DATA = await res.json();
  bindToggle();
  renderHeadline();
  renderRanking();
  setupDates();
  renderMeta();
}

function teamsByView() {
  const key = activeKey();
  return [...DATA.teams].sort((a, b) => b[key] - a[key]);
}

function renderHeadline() {
  const top = teamsByView()[0];
  if (view === "rooting") {
    const why = top.wc_titles === 0
      ? "a huge, devoted following, low incomes, and no title to take for granted"
      : "a huge following weighted up by low incomes";
    document.getElementById("headline").innerHTML =
      `If you only care about the win itself, root for <b>${top.name}</b>: ${why}. ` +
      `The glow would linger for years rather than fade in a season.`;
    return;
  }
  document.getElementById("headline").innerHTML =
    `Root for <b>${top.name}</b>: few expect much of them, their following is large ` +
    `and their incomes low, so every round they survive is a jolt of joy that lands ` +
    `where it counts and lingers for years.`;
}

function refresh() {
  // The timeframe toggle only bites on the surprise views; dim it otherwise.
  document.getElementById("time-toggle").classList.toggle("muted", view === "rooting");
  renderHeadline();
  renderRanking();
  renderMatches(document.getElementById("match-date").value);
}

function bindToggle() {
  document.querySelectorAll("#view-toggle button").forEach((btn) => {
    btn.addEventListener("click", () => {
      view = btn.dataset.view;
      document.querySelectorAll("#view-toggle button")
        .forEach((b) => b.classList.toggle("active", b === btn));
      refresh();
    });
  });
  document.querySelectorAll("#time-toggle button").forEach((btn) => {
    btn.addEventListener("click", () => {
      timeframe = btn.dataset.time;
      document.querySelectorAll("#time-toggle button")
        .forEach((b) => b.classList.toggle("active", b === btn));
      refresh();
    });
  });
}

function renderRanking() {
  let note = VIEWS[view].note;
  if (view !== "rooting") {
    note += timeframe === "pre"
      ? " Showing the frozen pre-tournament ranking, before any results."
      : " Showing the live ranking, updated for results so far.";
  }
  document.getElementById("view-note").textContent = note;
  const key = activeKey();
  const teams = teamsByView();
  const max = Math.max(...teams.map((t) => t[key])) || 1;
  const host = document.getElementById("ranking");
  host.innerHTML = "";

  teams.forEach((t, i) => {
    const pct = Math.max(1.5, (t[key] / max) * 100);
    const el = document.createElement("div");
    el.className = "row" + (i === 0 ? " top" : "");
    const tags = [];
    if (t.host) tags.push('<span class="badge host">HOST</span>');
    if (t.eliminated) tags.push('<span class="badge out">OUT</span>');
    el.innerHTML = `
      <span class="rank">${i + 1}</span>
      <div class="name">${t.name}${tags.join("")}
        <small>${t.confederation} &middot; Group ${t.group}</small>
        <div class="compare">
          <span class="cmp"><span class="cmp-k">Best prior:</span> ${bestPrior(t.best_finish)}</span>
          <span class="cmp"><span class="cmp-k">Expected to reach:</span> ${expStage(t.expected_depth)}</span>
        </div>
      </div>
      <div class="bar-wrap">
        <div class="bar" style="width:${pct}%"></div>
        <span class="bar-val">${t[key].toFixed(1)}</span>
      </div>`;
    el.addEventListener("click", () => openDrawer(t));
    host.appendChild(el);
  });
}

function setupDates() {
  const input = document.getElementById("match-date");
  const dates = [...new Set(DATA.fixtures.map((f) => f.date))].sort();
  const today = "2026-06-19";
  input.min = dates[0];
  input.max = dates[dates.length - 1];
  input.value = dates.includes(today) ? today : dates[0];
  input.addEventListener("change", () => renderMatches(input.value));
  renderMatches(input.value);
}

// Per-side score for a match, in the active view. The absolute view roots for the
// bigger prize; the relative view weights that prize by how big an upset the win
// would be tonight.
function matchScore(t, opp) {
  const base = t.rooting_index;
  if (view === "rooting") return base;
  return base * (1 - pWin(t, opp));
}

function renderMatches(dateStr) {
  const host = document.getElementById("matches");
  const byName = Object.fromEntries(DATA.teams.map((t) => [t.name, t]));
  const todays = DATA.fixtures.filter((f) => f.date === dateStr);
  host.innerHTML = "";
  if (!todays.length) {
    host.innerHTML = '<p class="empty">No group-stage matches on this date.</p>';
    return;
  }
  const key = activeKey();
  todays.forEach((f) => {
    const h = byName[f.home], a = byName[f.away];
    const hs = matchScore(h, a), as = matchScore(a, h);
    const homePick = hs >= as;
    const pick = homePick ? h : a;
    const upset = view !== "rooting" && (homePick ? pWin(h, a) < 0.5 : pWin(a, h) < 0.5);
    const el = document.createElement("div");
    el.className = "match";
    el.innerHTML = `
      <div class="match-top"><span>Group ${f.group}</span><span>Matchday ${f.matchday}</span></div>
      <div class="match-teams">
        <div class="side ${homePick ? "pick" : ""}">
          <div class="tn">${h.name}</div>
          <div class="ti">index ${h[key].toFixed(0)}</div>
        </div>
        <div class="vs">v</div>
        <div class="side right ${homePick ? "" : "pick"}">
          <div class="tn">${a.name}</div>
          <div class="ti">index ${a[key].toFixed(0)}</div>
        </div>
      </div>
      <div class="pick-line">Root for <b>${pick.name}</b>${
        upset ? ", the underdog: an against-the-odds win here would be the bigger surprise." :
        " for the most happiness on offer."
      }</div>`;
    el.querySelectorAll(".side").forEach((s, idx) => {
      s.style.cursor = "pointer";
      s.addEventListener("click", () => openDrawer(idx === 0 ? h : a));
    });
    host.appendChild(el);
  });
}

function openDrawer(t) {
  const body = document.getElementById("drawer-body");
  const kv = (k, v) => `<div class="kv"><span class="k">${k}</span><span class="v">${v}</span></div>`;
  const lastTitle = t.last_major_year === null ? "none on record" : t.last_major_year;
  const status = t.eliminated ? "out"
    : (t.reached_depth > 0 ? "still in (knockouts)" : "still in (group stage)");
  body.innerHTML = `
    <h3>${t.name}</h3>
    <p class="sub">${t.confederation} &middot; Group ${t.group}${t.host ? " &middot; Host" : ""}</p>
    ${kv("Performance, relative (live)", t.surprise_index.toFixed(1))}
    ${kv("Performance, relative (pre-tournament)", t.surprise_index_pre.toFixed(1))}
    ${kv("Performance, absolute", t.rooting_index.toFixed(1))}
    <div class="kv-group">Run vs expectations</div>
    ${kv("Expected to reach", expStage(t.expected_depth))}
    ${kv("Best prior World Cup", bestPrior(t.best_finish))}
    ${kv("Status", status)}
    <div class="kv-group">Memory of a win</div>
    ${kv("World Cup titles", t.wc_titles)}
    ${kv("Last major trophy", lastTitle)}
    ${kv("Memory half-life", t.memory_half_life + " years")}
    <div class="kv-group">Reach and need</div>
    ${kv("Fans reached", fmtM(t.fan_population))}
    ${kv("&nbsp;&nbsp;home", fmtM(t.home_fans))}
    ${kv("&nbsp;&nbsp;diaspora", fmtM(t.diaspora_fans))}
    ${kv("&nbsp;&nbsp;continental solidarity", fmtM(t.solidarity_fans))}
    ${kv("Consumption (GNI pc, PPP)", "$" + fmtInt(t.consumption))}
    ${kv("Marginal-utility weight", t.mu_weight.toFixed(2) + "x")}
    ${kv("Elo rating (reference only)", t.elo)}
    <p class="note">Beating-expectations index = fans reached x marginal-utility
      weight x the present value of a title x how far the team beats its
      pre-tournament odds, with deeper rounds counting more. Lower consumption
      raises the utility weight; an unaccustomed win lingers longer in memory. Win
      probability sets the bar but never weights the score.</p>`;
  document.getElementById("drawer").classList.remove("hidden");
}

function renderMeta() {
  const p = DATA.meta.params;
  document.getElementById("meta").innerHTML =
    `Updated ${DATA.meta.generated.slice(0, 10)} &middot; ` +
    `basis: ${DATA.meta.basis} &middot; ` +
    `<code>eta=${p.eta}</code> ` +
    `<code>memory half-life ${(Math.log(2) / p.r_lo).toFixed(0)}y to ${(Math.log(2) / p.r_hi).toFixed(1)}y</code> ` +
    `<code>later-round weight exp=${p.stage_weight_exp}</code> ` +
    `<code>${fmtInt(p.mc_iterations)} sims for the bar</code>. Methods in the repo README.`;
}

document.getElementById("drawer-close")
  .addEventListener("click", () => document.getElementById("drawer").classList.add("hidden"));

load();
