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
  V_i  per-fan value of the title, a base shock scaled up by novelty:
       V_i = H0 * (1 + NOVELTY_ALPHA * novelty_i), novelty_i = 1 - history_i. A
       long-awaited or first-ever win is worth more. See config.py for citations.

W_net_i nets out a documented dark-side externality. Outputs web/rankings.json
and prints the ranking. Run after the fetch/build steps (or via run_all.py).
"""
import csv
import json
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


def title_value(history):
    """Per-fan happiness value of a title, scaled up by novelty."""
    novelty = 1.0 - history
    return config.H0 * (1.0 + config.NOVELTY_ALPHA * novelty)


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
        tv = title_value(history)
        N = fans[n]["N"]
        w_gross = N * mu * tv
        w_net = w_gross * (1.0 - config.DARKSIDE_FRACTION)
        rows[n] = {
            "N": N, "mu": mu, "title_value": tv,
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
            "fan_population": round(b["N"]),
            "home_fans": round(b["home_fans"]),
            "diaspora_fans": round(b["diaspora_fans"]),
            "solidarity_fans": round(b["solidarity_fans"]),
            "mu_weight": round(b["mu"], 3),
            "title_value": round(b["title_value"], 3),
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
                "h0": config.H0,
                "novelty_alpha": config.NOVELTY_ALPHA,
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
    print(f"{'#':>2}  {'Team':22} {'Index':>6} {'Novelty':>7} {'Fans(M)':>8} {'GNIpc':>7}")
    for i, x in enumerate(out_teams[:15], 1):
        print(f"{i:>2}  {x['name']:22} {x['rooting_index']:>6} "
              f"{x['novelty']:>7} {x['fan_population']/1e6:>8.0f} {x['consumption']:>7}")
    print(f"\nWrote {os.path.join(WEB, 'rankings.json')}")


if __name__ == "__main__":
    main()
