// World Cup Happiness Index 2026 - live "who to root for" tool.
// Reads rankings.json (written by the pipeline) and renders three views plus a
// day-by-day match guide. No build step, no dependencies.

const VIEWS = {
  rooting: {
    key: "rooting_index",
    label: "If they win the Cup",
    note: "Aggregate happiness added by a title: fans reached, times the per-fan " +
      "lift, weighted up where people have less. This is the prize, before the odds.",
  },
  expected: {
    key: "expected_index",
    label: "Expected impact",
    note: "The prize multiplied by each team's odds of actually winning, net of " +
      "the beaten finalist's loss. What is realistically on the table.",
  },
  eta15: {
    key: "rooting_index_eta15",
    label: "Tilt to the poor",
    note: "The same prize, but with a stronger preference for low-income countries " +
      "(utility curvature eta = 1.5 instead of 1).",
  },
};

let DATA = null;
let view = "rooting";

function fmtInt(n) { return n.toLocaleString("en-US"); }
function fmtM(n) { return (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + "M"; }

async function load() {
  const res = await fetch("rankings.json");
  DATA = await res.json();
  renderHeadline();
  bindToggle();
  renderRanking();
  setupDates();
  renderMeta();
}

function teamsByView() {
  const key = VIEWS[view].key;
  return [...DATA.teams].sort((a, b) => b[key] - a[key]);
}

function renderHeadline() {
  const root = [...DATA.teams].sort((a, b) => b.rooting_index - a.rooting_index)[0];
  const exp = [...DATA.teams].sort((a, b) => b.expected_index - a.expected_index)[0];
  document.getElementById("headline").innerHTML =
    `For the biggest happiness gain, root for <b>${root.name}</b>. ` +
    `Balancing for who can actually win it, the smart pick is <b>${exp.name}</b>.`;
}

function bindToggle() {
  document.querySelectorAll("#view-toggle button").forEach((btn) => {
    btn.addEventListener("click", () => {
      view = btn.dataset.view;
      document.querySelectorAll("#view-toggle button")
        .forEach((b) => b.classList.toggle("active", b === btn));
      renderRanking();
    });
  });
}

function renderRanking() {
  document.getElementById("view-note").textContent = VIEWS[view].note;
  const key = VIEWS[view].key;
  const teams = teamsByView();
  const max = Math.max(...teams.map((t) => t[key])) || 1;
  const host = document.getElementById("ranking");
  host.innerHTML = "";

  teams.forEach((t, i) => {
    const pct = Math.max(1.5, (t[key] / max) * 100);
    const el = document.createElement("div");
    el.className = "row" + (i === 0 ? " top" : "");
    el.innerHTML = `
      <span class="rank">${i + 1}</span>
      <div class="name">${t.name}${t.host ? '<span class="badge">HOST</span>' : ""}
        <small>${t.confederation} &middot; Group ${t.group}</small></div>
      <div class="bar-wrap">
        <div class="bar" style="width:${pct}%"></div>
        <span class="bar-val">${t[key].toFixed(1)}</span>
      </div>
      <div class="p">${(t.p_champion * 100).toFixed(1)}%<br><small>to win</small></div>`;
    el.addEventListener("click", () => openDrawer(t));
    host.appendChild(el);
  });
}

function setupDates() {
  const input = document.getElementById("match-date");
  const dates = [...new Set(DATA.fixtures.map((f) => f.date))].sort();
  const today = "2026-06-18";
  input.min = dates[0];
  input.max = dates[dates.length - 1];
  input.value = dates.includes(today) ? today : dates[0];
  input.addEventListener("change", () => renderMatches(input.value));
  renderMatches(input.value);
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
  todays.forEach((f) => {
    const h = byName[f.home], a = byName[f.away];
    const homePick = h.rooting_index >= a.rooting_index;
    const pick = homePick ? h : a;
    const gap = Math.abs(h.rooting_index - a.rooting_index).toFixed(0);
    const el = document.createElement("div");
    el.className = "match";
    el.innerHTML = `
      <div class="match-top"><span>Group ${f.group}</span><span>Matchday ${f.matchday}</span></div>
      <div class="match-teams">
        <div class="side ${homePick ? "pick" : ""}">
          <div class="tn">${h.name}</div>
          <div class="ti">rooting index ${h.rooting_index.toFixed(0)}</div>
        </div>
        <div class="vs">v</div>
        <div class="side right ${homePick ? "" : "pick"}">
          <div class="tn">${a.name}</div>
          <div class="ti">rooting index ${a.rooting_index.toFixed(0)}</div>
        </div>
      </div>
      <div class="pick-line">Root for <b>${pick.name}</b>${
        gap > 0 ? ` (a win adds about ${gap} points more happiness than the other result)` : ""
      }.</div>`;
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
  body.innerHTML = `
    <h3>${t.name}</h3>
    <p class="sub">${t.confederation} &middot; Group ${t.group}${t.host ? " &middot; Host" : ""}</p>
    ${kv("Rooting index (win the Cup)", t.rooting_index.toFixed(1))}
    ${kv("Tilt-to-poor index (eta 1.5)", t.rooting_index_eta15.toFixed(1))}
    ${kv("Expected-impact index", t.expected_index.toFixed(1))}
    ${kv("Chance of winning", (t.p_champion * 100).toFixed(1) + "%")}
    ${kv("Reaches the final", (t.p_final * 100).toFixed(1) + "%")}
    ${kv("Fans reached", fmtM(t.fan_population))}
    ${kv("&nbsp;&nbsp;home", fmtM(t.home_fans))}
    ${kv("&nbsp;&nbsp;diaspora", fmtM(t.diaspora_fans))}
    ${kv("&nbsp;&nbsp;continental solidarity", fmtM(t.solidarity_fans))}
    ${kv("Consumption (GNI pc, PPP)", "$" + fmtInt(t.consumption))}
    ${kv("Marginal-utility weight", t.mu_weight.toFixed(2) + "x")}
    ${kv("Elo rating", t.elo)}
    <p class="note">Rooting index is fan population times the per-fan happiness
      shock times the marginal-utility weight, net of a dark-side externality,
      indexed to the top team. A lower consumption level raises the utility weight,
      so a windfall counts for more.</p>`;
  document.getElementById("drawer").classList.remove("hidden");
}

function renderMeta() {
  const p = DATA.meta.params;
  document.getElementById("meta").innerHTML =
    `Updated ${DATA.meta.generated.slice(0, 10)} &middot; stage: ${DATA.meta.stage} &middot; ` +
    `<code>eta=${p.eta}</code> <code>h=${p.h_per_fan}</code> ` +
    `<code>diaspora=${p.diaspora_weight}</code> <code>solidarity=${p.continental_weight}</code> ` +
    `<code>loss aversion=${p.loss_aversion}</code> &middot; probabilities: ${p.prob_source}, ` +
    `${fmtInt(p.mc_iterations)} simulations. Methods in the repo README.`;
}

document.getElementById("drawer-close")
  .addEventListener("click", () => document.getElementById("drawer").classList.add("hidden"));

load();
