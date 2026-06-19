"""The World Cup Happiness Index model.

The published quantity is the marginal utility to the world if a team wins the
Cup. Not expected utility: win probability is excluded on purpose. The question
is how much joy a title would add, not how likely it is.

Per country i:

    W_i = N_i x MU_i x V_i

  N_i  affected fan population: engaged home fans (population x interest), plus
       diaspora fans, plus a continental-solidarity share of neighbours.
  MU_i marginal-utility weight, MU_i = (C_REF/c_i)^eta, with c_i consumption per
       head. A windfall counts for more where people have less.
  V_i  per-fan value of the title: the present value of a fading glow,
       V_i = H0 / r_i, with r_i the discount rate set by pedigree. The memory
       lingers longer for a country unused to winning, so its title is discounted
       less and worth more today. See config.py for the citations.

W_net_i applies an optional externality haircut, currently zero (the dark-side
cost from Card & Dahl 2011 is not modelled; see config). Outputs web/rankings.json
and prints the ranking. Run after the fetch/build steps (or via run_all.py).
"""
import csv
import json
import math
import os
from datetime import datetime, timezone

import config

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")
WEB = os.path.join(HERE, "..", "web")


def _load_workbook():
    rows = {}
    with open(os.path.join(DATA, "workbook.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows[r["name"]] = r
    return rows


def _load_expectations():
    """team -> {1: P(reach R32), ..., 6: P(champion), 'depth': expected depth}."""
    path = os.path.join(DATA, "expectations.csv")
    out = {}
    if not os.path.exists(path):
        return out
    cols = ["p_r32", "p_r16", "p_qf", "p_sf", "p_final", "p_champion"]
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out[r["name"]] = {k + 1: float(r[c]) for k, c in enumerate(cols)}
            out[r["name"]]["depth"] = float(r["expected_depth"])
    return out


def _load_results():
    """team -> {'reached_depth': int, 'eliminated': bool}; default empty."""
    path = os.path.join(DATA, "results.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("teams", {})
    return {}


def surprise_score(probs, reached_depth, eliminated):
    """Depth-weighted sum of how unlikely each reached (or still-reachable) stage was.

    maxk = the depth reached if the team is out, else 6 (a live team keeps its full
    forward potential). Deeper stages count more via the depth weight.
    """
    if not probs:
        return 0.0
    maxk = reached_depth if eliminated else 6
    total = 0.0
    for k in range(1, maxk + 1):
        weight = k ** config.STAGE_WEIGHT_EXP
        total += weight * (1.0 - probs.get(k, 0.0))
    return total


def mu_weight(consumption, eta):
    # Stone-Geary subsistence offset: add a fixed amount before weighting, so the
    # poorest are compressed together (but never identical) and the poor-rich gap
    # is preserved.
    c = float(consumption) + config.CONSUMPTION_OFFSET
    return (config.C_REF / c) ** eta


def title_value(history):
    """Per-fan present value of a title and its discount rate.

    The title is a glow that fades at rate r; its present value is H0 / r. A
    low-pedigree team's memory lingers (low r), so its title is worth more.
    """
    r = config.R_LO + (config.R_HI - config.R_LO) * history
    return config.H0 / r, r


def fan_population(teams):
    """N_i with home, diaspora and continental-solidarity components."""
    home = {t["name"]: float(t["population"]) * float(t["interest"]) for t in teams.values()}
    by_conf = {}
    for t in teams.values():
        by_conf.setdefault(t["confederation"], []).append(t["name"])
    out = {}
    for t in teams.values():
        n = t["name"]
        diaspora = float(t["diaspora_m"]) * 1e6 * float(t["interest"]) * config.DIASPORA_WEIGHT
        neighbours = sum(home[o] for o in by_conf[t["confederation"]] if o != n)
        solidarity = config.CONTINENTAL_WEIGHTS.get(t["confederation"], 0.05) * neighbours
        out[n] = {
            "home_fans": home[n],
            "diaspora_fans": diaspora,
            "solidarity_fans": solidarity,
            "N": home[n] + diaspora + solidarity,
        }
    return out


def compute(teams, eta):
    fans = fan_population(teams)
    rows = {}
    for t in teams.values():
        n = t["name"]
        history = float(t["history"]) if t["history"] else 0.0
        mu = mu_weight(t["consumption"], eta)
        tv, r = title_value(history)
        N = fans[n]["N"]
        w_gross = N * mu * tv
        w_net = w_gross * (1.0 - config.DARKSIDE_FRACTION)
        rows[n] = {
            "N": N, "mu": mu, "title_value": tv, "decay": r,
            "w_gross": w_gross, "w_net": w_net, **fans[n],
        }
    return rows


def main():
    teams = _load_workbook()

    base = compute(teams, config.ETA)
    band = compute(teams, config.ETA_SENSITIVITY)
    expectations = _load_expectations()
    results = _load_results()

    # Surprise factor per team (independent of eta). Two snapshots against the
    # same frozen pre-tournament bar: "pre" applies no results (every team alive at
    # full potential, the original pre-tournament ranking); "live" applies the
    # actual results so far. They coincide until the knockouts begin.
    surprise_live, surprise_pre = {}, {}
    for n in teams:
        probs = expectations.get(n, {})
        res = results.get(n, {})
        surprise_live[n] = surprise_score(
            probs, int(res.get("reached_depth", 0)), bool(res.get("eliminated", False)))
        surprise_pre[n] = surprise_score(probs, 0, False)

    max_wnet = max(r["w_net"] for r in base.values())
    max_wnet_band = max(r["w_net"] for r in band.values())
    max_live = max(base[n]["w_net"] * surprise_live[n] for n in teams) or 1.0
    max_live_b = max(band[n]["w_net"] * surprise_live[n] for n in teams) or 1.0
    max_pre = max(base[n]["w_net"] * surprise_pre[n] for n in teams) or 1.0
    max_pre_b = max(band[n]["w_net"] * surprise_pre[n] for n in teams) or 1.0

    # Display on a compressed scale (keeps order and the leader at 100).
    p = config.SCORE_CONCAVITY

    def scaled(num, den):
        return round(100 * (num / den) ** p, 1) if den else 0.0

    out_teams = []
    for n, t in teams.items():
        b = base[n]
        history = float(t["history"]) if t["history"] else 0.0
        res = results.get(n, {})
        exp = expectations.get(n, {})
        out_teams.append({
            "name": n,
            "confederation": t["confederation"],
            "group": t["group"],
            "host": t["host"] == "1",
            "population": int(float(t["population"])),
            "consumption": int(float(t["consumption"])),
            "elo": round(float(t["elo"])),
            "interest": round(float(t["interest"]), 3),
            "wc_titles": int(t["wc_titles"]) if t["wc_titles"] else 0,
            "last_major_year": t["last_major_year"] or None,
            "best_finish": t.get("best_finish", ""),
            "history": round(history, 3),
            "novelty": round(1.0 - history, 3),
            "memory_half_life": round(math.log(2) / b["decay"], 1),
            "fan_population": round(b["N"]),
            "home_fans": round(b["home_fans"]),
            "diaspora_fans": round(b["diaspora_fans"]),
            "solidarity_fans": round(b["solidarity_fans"]),
            "mu_weight": round(b["mu"], 3),
            "present_value": round(b["title_value"], 3),
            "expected_depth": round(exp.get("depth", 0.0), 2),
            "reached_depth": int(res.get("reached_depth", 0)),
            "eliminated": bool(res.get("eliminated", False)),
            "surprise": round(surprise_live[n], 2),
            "surprise_pre": round(surprise_pre[n], 2),
            "w_net": b["w_net"],
            "rooting_index": scaled(b["w_net"], max_wnet),
            "rooting_index_eta15": scaled(band[n]["w_net"], max_wnet_band),
            "surprise_index": scaled(b["w_net"] * surprise_live[n], max_live),
            "surprise_index_eta15": scaled(band[n]["w_net"] * surprise_live[n], max_live_b),
            "surprise_index_pre": scaled(b["w_net"] * surprise_pre[n], max_pre),
            "surprise_index_pre_eta15": scaled(band[n]["w_net"] * surprise_pre[n], max_pre_b),
        })

    out_teams.sort(key=lambda x: x["surprise_index"], reverse=True)

    with open(os.path.join(DATA, "fixtures.json"), encoding="utf-8") as fh:
        fixtures = json.load(fh)

    live_changed = any(r.get("eliminated") or int(r.get("reached_depth", 0)) > 0
                       for r in results.values())
    payload = {
        "meta": {
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "title": "World Cup Happiness Index 2026",
            "live_changed": live_changed,
            "basis": "performance relative to expectations (default), or absolute performance if they win; never weighted by win probability",
            "params": {
                "eta": config.ETA,
                "eta_sensitivity": config.ETA_SENSITIVITY,
                "h0": config.H0,
                "r_lo": config.R_LO,
                "r_hi": config.R_HI,
                "stage_weight_exp": config.STAGE_WEIGHT_EXP,
                "mc_iterations": config.MC_ITERATIONS,
                "diaspora_weight": config.DIASPORA_WEIGHT,
                "continental_weights": config.CONTINENTAL_WEIGHTS,
                "score_concavity": config.SCORE_CONCAVITY,
                "darkside_fraction": config.DARKSIDE_FRACTION,
            },
        },
        "teams": out_teams,
        "fixtures": fixtures,
    }
    os.makedirs(WEB, exist_ok=True)
    with open(os.path.join(WEB, "rankings.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    print(f"\nWorld Cup Happiness Index 2026  (eta={config.ETA})")
    print("Who to root for - happiness from beating expectations\n")
    print(f"{'#':>2}  {'Team':22} {'Surprise':>8} {'ExpDepth':>8} {'WinCup':>7} {'GNIpc':>7}")
    for i, x in enumerate(out_teams[:15], 1):
        print(f"{i:>2}  {x['name']:22} {x['surprise_index']:>8} "
              f"{x['expected_depth']:>8} {x['rooting_index']:>7} {x['consumption']:>7}")
    print(f"\nWrote {os.path.join(WEB, 'rankings.json')}")


if __name__ == "__main__":
    main()
