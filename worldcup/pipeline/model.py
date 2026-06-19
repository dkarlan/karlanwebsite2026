"""The World Cup Happiness Index model.

The published quantity is the marginal utility to the world if a team wins the
Cup. Not expected utility: win probability is excluded on purpose. The question
is how much joy a title would add, not how likely it is.

Per country i:

    W_i = N_i x MU_i x LU_i

  N_i  affected fan population: engaged home fans (population x interest), plus
       diaspora fans, plus a continental-solidarity share of neighbours.
  MU_i marginal-utility weight, MU_i = (C_REF/c_i)^eta, with c_i consumption per
       head. A windfall counts for more where people have less.
  LU_i per-fan lifetime value of the title, the NPV of a decaying joy stream,
       LU_i = s_i / r_i. Novelty raises the spike s_i; pedigree raises the decay
       rate r_i, so a first-timer's joy is large and long, a serial winner's
       small and brief. See config.py for the citations.

W_net_i nets out a documented dark-side externality. Outputs web/rankings.json
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


def mu_weight(consumption, eta):
    c = max(float(consumption), 500.0)        # floor to avoid blow-ups
    return (config.C_REF / c) ** eta


def lifetime_utility(history):
    """NPV of the remembered-joy stream for one engaged fan."""
    novelty = 1.0 - history
    s = config.NPV_H0 * (1.0 + config.NPV_ALPHA * novelty)
    r = config.NPV_R_LO + (config.NPV_R_HI - config.NPV_R_LO) * history
    return s / r, s, r


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
        solidarity = config.CONTINENTAL_WEIGHT * neighbours
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
        lu, s, r = lifetime_utility(history)
        N = fans[n]["N"]
        w_gross = N * mu * lu
        w_net = w_gross * (1.0 - config.DARKSIDE_FRACTION)
        rows[n] = {
            "N": N, "mu": mu, "lu": lu, "spike": s, "decay": r,
            "w_gross": w_gross, "w_net": w_net, **fans[n],
        }
    return rows


def main():
    teams = _load_workbook()

    base = compute(teams, config.ETA)
    band = compute(teams, config.ETA_SENSITIVITY)
    max_wnet = max(r["w_net"] for r in base.values())
    max_wnet_band = max(r["w_net"] for r in band.values())

    out_teams = []
    for n, t in teams.items():
        b = base[n]
        history = float(t["history"]) if t["history"] else 0.0
        half_life = round(math.log(2) / b["decay"], 1)
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
            "history": round(history, 3),
            "novelty": round(1.0 - history, 3),
            "memory_half_life": half_life,
            "fan_population": round(b["N"]),
            "home_fans": round(b["home_fans"]),
            "diaspora_fans": round(b["diaspora_fans"]),
            "solidarity_fans": round(b["solidarity_fans"]),
            "mu_weight": round(b["mu"], 3),
            "lifetime_utility": round(b["lu"], 3),
            "w_net": b["w_net"],
            "rooting_index": round(100 * b["w_net"] / max_wnet, 1),
            "rooting_index_eta15": round(100 * band[n]["w_net"] / max_wnet_band, 1),
        })

    out_teams.sort(key=lambda x: x["w_net"], reverse=True)

    with open(os.path.join(DATA, "fixtures.json"), encoding="utf-8") as fh:
        fixtures = json.load(fh)

    payload = {
        "meta": {
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "title": "World Cup Happiness Index 2026",
            "basis": "marginal utility to the world if the team wins (no win probability)",
            "params": {
                "eta": config.ETA,
                "eta_sensitivity": config.ETA_SENSITIVITY,
                "npv_h0": config.NPV_H0,
                "npv_alpha": config.NPV_ALPHA,
                "npv_r_lo": config.NPV_R_LO,
                "npv_r_hi": config.NPV_R_HI,
                "diaspora_weight": config.DIASPORA_WEIGHT,
                "continental_weight": config.CONTINENTAL_WEIGHT,
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
    print("Who to root for - marginal happiness to the world if they win\n")
    print(f"{'#':>2}  {'Team':22} {'Index':>6} {'Novelty':>7} {'Half-life':>9} {'GNIpc':>7}")
    for i, x in enumerate(out_teams[:15], 1):
        print(f"{i:>2}  {x['name']:22} {x['rooting_index']:>6} "
              f"{x['novelty']:>7} {x['memory_half_life']:>7}y {x['consumption']:>7}")
    print(f"\nWrote {os.path.join(WEB, 'rankings.json')}")


if __name__ == "__main__":
    main()
