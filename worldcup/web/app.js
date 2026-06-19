// World Cup Happiness Index 2026 - live "who to root for" tool.
// Reads rankings.json (written by the pipeline). The headline number is the
// marginal happiness to the world if a team wins: fan population, times the
// marginal-utility weight, times the lifetime value of the title (novelty raises
// the joy, pedigree makes it fade faster). Win probability is excluded by design.

const VIEWS = {
  rooting: {
    key: "rooting_index",
    label: "Marginal happiness",
    note: "Happiness added to the world by a title: fans reached, times the per-fan " +
      "lifetime value, weighted up where people have less and where a win would be " +
      "novel rather than routine.",
  },
  eta15: {
    key: "rooting_index_eta15",
    label: "Tilt to the poor",
    note: "The same measure, with a stronger preference for low-income countries " +
      "(utility curvature eta = 1.5 instead of 1).",
  },
};

let DATA = null;
let view = "rooting";

function fmtInt(n) { return n.toLocaleString("en-US"); }
function fmtM(n) { return (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + "M"; }
function titleTag(t) {
  if (t.last_major_year === null && t.wc_titles === 0) return "never won a major";
  if (t.wc_titles === 0) return "never won the Cup";
  return t.wc_titles + (t.wc_titles === 1 ? " title" : " titles");
}

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
  const top = [...DATA.teams].sort((a, b) => b.rooting_index - a.rooting_index)[0];
  const why = top.wc_titles === 0
    ? "a huge, devoted following, low incomes, and no title to take for granted"
    : "a huge following weighted up by low incomes";
  document.getElementById("headline").innerHTML =
    `This year, root for <b>${top.name}</b>: ${why}. A win there would add more ` +
    `happiness to the world than a win anywhere else.`;
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
    const badge = t.wc_titles === 0
      ? `<span class="badge">${t.last_major_year === null ? "DEBUT-ERA" : "NEVER WON"}</span>` : "";
    el.innerHTML = `
      <span class="rank">${i + 1}</span>
      <div class="name">${t.name}${t.host ? '<span class="badge host">HOST</span>' : ""}${badge}
        <small>${t.confederation} &middot; Group ${t.group}</small></div>
      <div class="bar-wrap">
        <div class="bar" style="width:${pct}%"></div>
        <span class="bar-val">${t[key].toFixed(1)}</span>
      </div>
      <div class="p">${t.novelty.toFixed(2)}<br><small>novelty</small></div>`;
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
          <div class="ti">happiness index ${h.rooting_index.toFixed(0)}</div>
        </div>
        <div class="vs">v</div>
        <div class="side right ${homePick ? "" : "pick"}">
          <div class="tn">${a.name}</div>
          <div class="ti">happiness index ${a.rooting_index.toFixed(0)}</div>
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
  const lastTitle = t.last_major_year === null ? "none on record" : t.last_major_year;
  body.innerHTML = `
    <h3>${t.name}</h3>
    <p class="sub">${t.confederation} &middot; Group ${t.group}${t.host ? " &middot; Host" : ""}</p>
    ${kv("Marginal-happiness index", t.rooting_index.toFixed(1))}
    ${kv("Tilt-to-poor index (eta 1.5)", t.rooting_index_eta15.toFixed(1))}
    <div class="kv-group">Novelty</div>
    ${kv("World Cup titles", t.wc_titles)}
    ${kv("Last major trophy", lastTitle)}
    ${kv("Novelty (0 to 1)", t.novelty.toFixed(2))}
    ${kv("Novelty multiplier", (t.title_value / DATA.meta.params.h0).toFixed(2) + "x")}
    <div class="kv-group">Reach and need</div>
    ${kv("Fans reached", fmtM(t.fan_population))}
    ${kv("&nbsp;&nbsp;home", fmtM(t.home_fans))}
    ${kv("&nbsp;&nbsp;diaspora", fmtM(t.diaspora_fans))}
    ${kv("&nbsp;&nbsp;continental solidarity", fmtM(t.solidarity_fans))}
    ${kv("Consumption (GNI pc, PPP)", "$" + fmtInt(t.consumption))}
    ${kv("Marginal-utility weight", t.mu_weight.toFixed(2) + "x")}
    ${kv("Elo rating (reference only)", t.elo)}
    <p class="note">Index = fans reached x marginal-utility weight x the value of
      a title. Lower consumption raises the utility weight. A team with little
      history of winning gets a bigger bump, so its joy is worth more. Win
      probability is not part of the score.</p>`;
  document.getElementById("drawer").classList.remove("hidden");
}

function renderMeta() {
  const p = DATA.meta.params;
  document.getElementById("meta").innerHTML =
    `Updated ${DATA.meta.generated.slice(0, 10)} &middot; ` +
    `basis: ${DATA.meta.basis} &middot; ` +
    `<code>eta=${p.eta}</code> <code>novelty alpha=${p.novelty_alpha}</code> ` +
    `<code>diaspora=${p.diaspora_weight}</code> <code>solidarity=${p.continental_weight}</code>. ` +
    `Methods in the repo README.`;
}

document.getElementById("drawer-close")
  .addEventListener("click", () => document.getElementById("drawer").classList.add("hidden"));

load();
