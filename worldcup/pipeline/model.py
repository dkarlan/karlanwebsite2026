"""The World Cup Happiness Index model.

Per country i the welfare from winning the Cup is

    W_i = N_i * h * MU_i

  N_i  affected fan population: engaged home fans (population * interest), plus
       diaspora fans, plus a continental-solidarity share of co-confederation
       neighbours.
  h    per-fan happiness shock in Cantril-ladder points (config.H_PER_FAN).
  MU_i marginal-utility weight under isoelastic utility, MU_i = (C_REF/c_i)^eta,
       with c_i mean consumption per head (GNI per capita PPP here).

The published object is expected, net and dynamic:

    E[ΔW from i] = P(champion_i) * W_net_i  -  (loss aversion) * E[beaten finalist's loss]

  W_net_i = W_i minus a documented dark-side externality haircut.

Outputs data/../web/rankings.json for the live tool and prints the ranking.
Run after the fetch/build steps (or via run_all.py).
"""
import csv
import json
import os
from datetime import datetime, timezone

import config
import simulate

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")
WEB = os.path.join(HERE, "..", "web")


def _load_workbook():
    rows = {}
    with open(os.path.join(DATA, "workbook.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows[r["name"]] = r
    return rows


def _load_state():
    path = os.path.join(DATA, "state.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {"stage": "group", "eliminated": []}


def mu_weight(consumption, eta):
    c = max(float(consumption), 500.0)        # floor to avoid blow-ups
    return (config.C_REF / c) ** eta


def fan_population(teams):
    """N_i with home, diaspora and continental-solidarity components."""
    home = {}
    for t in teams.values():
        home[t["name"]] = float(t["population"]) * float(t["interest"])
    # Continental solidarity: a small share of co-confederation neighbours' fans.
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


def compute(teams, eta, h):
    fans = fan_population(teams)
    rows = {}
    for t in teams.values():
        n = t["name"]
        mu = mu_weight(t["consumption"], eta)
        N = fans[n]["N"]
        w_gross = N * h * mu
        w_net = w_gross * (1.0 - config.DARKSIDE_FRACTION)
        rows[n] = {
            "N": N, "mu": mu, "w_gross": w_gross, "w_net": w_net,
            **fans[n],
        }
    return rows


def main():
    wb = _load_workbook()
    teams = wb  # name -> row dict
    groups = {}
    for t in teams.values():
        groups.setdefault(t["group"], []).append(t["name"])
    elo = {n: float(t["elo"]) for n, t in teams.items()}
    hosts = {n for n, t in teams.items() if t["host"] == "1"}
    state = _load_state()

    # Welfare at the default eta and at the sensitivity eta (for the band).
    base = compute(teams, config.ETA, config.H_PER_FAN)
    band = compute(teams, config.ETA_SENSITIVITY, config.H_PER_FAN)

    # Win probabilities and the expected beaten-finalist loss, from Monte Carlo.
    value_for_loss = {n: base[n]["w_gross"] for n in base}
    probs, loser_loss = simulate.simulate(groups, elo, hosts, state,
                                           team_value=value_for_loss)

    max_wnet = max(r["w_net"] for r in base.values())
    out_teams = []
    for n, t in teams.items():
        b = base[n]
        p_champ = probs[n]["Champion"]
        expected_net = p_champ * b["w_net"] - config.LOSS_AVERSION * loser_loss[n]
        out_teams.append({
            "name": n,
            "confederation": t["confederation"],
            "group": t["group"],
            "host": t["host"] == "1",
            "population": int(float(t["population"])),
            "consumption": int(float(t["consumption"])),
            "elo": round(elo[n]),
            "interest": round(float(t["interest"]), 3),
            "fan_population": round(b["N"]),
            "home_fans": round(b["home_fans"]),
            "diaspora_fans": round(b["diaspora_fans"]),
            "solidarity_fans": round(b["solidarity_fans"]),
            "mu_weight": round(b["mu"], 3),
            "w_net": b["w_net"],
            "rooting_index": round(100 * b["w_net"] / max_wnet, 1),
            "rooting_index_eta15": round(
                100 * band[n]["w_net"] / max(r["w_net"] for r in band.values()), 1),
            "p_champion": round(p_champ, 4),
            "p_round_of_16": round(probs[n]["R16"], 3),
            "p_quarterfinal": round(probs[n]["QF"], 3),
            "p_semifinal": round(probs[n]["SF"], 3),
            "p_final": round(probs[n]["F"], 3),
            "expected_net_welfare": expected_net,
        })

    # Normalize the expected-value column to an index too (max positive = 100).
    max_exp = max((x["expected_net_welfare"] for x in out_teams), default=1.0) or 1.0
    for x in out_teams:
        x["expected_index"] = round(100 * x["expected_net_welfare"] / max_exp, 1)

    out_teams.sort(key=lambda x: x["w_net"], reverse=True)

    with open(os.path.join(DATA, "fixtures.json"), encoding="utf-8") as fh:
        fixtures = json.load(fh)

    payload = {
        "meta": {
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "title": "World Cup Happiness Index 2026",
            "stage": state.get("stage", "group"),
            "params": {
                "eta": config.ETA,
                "eta_sensitivity": config.ETA_SENSITIVITY,
                "h_per_fan": config.H_PER_FAN,
                "diaspora_weight": config.DIASPORA_WEIGHT,
                "continental_weight": config.CONTINENTAL_WEIGHT,
                "loss_aversion": config.LOSS_AVERSION,
                "darkside_fraction": config.DARKSIDE_FRACTION,
                "prob_source": config.PROB_SOURCE,
                "mc_iterations": config.MC_ITERATIONS,
            },
        },
        "teams": out_teams,
        "fixtures": fixtures,
    }
    os.makedirs(WEB, exist_ok=True)
    with open(os.path.join(WEB, "rankings.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    # Console summary.
    print(f"\nWorld Cup Happiness Index 2026  (eta={config.ETA}, h={config.H_PER_FAN})")
    print("Who to root for — by net happiness if they win the Cup\n")
    print(f"{'#':>2}  {'Team':22} {'Index':>6} {'P(win)':>7} {'Fans(M)':>8} {'GNIpc':>7}")
    for i, x in enumerate(out_teams[:15], 1):
        print(f"{i:>2}  {x['name']:22} {x['rooting_index']:>6} "
              f"{x['p_champion']*100:>6.1f}% {x['fan_population']/1e6:>8.0f} "
              f"{x['consumption']:>7}")
    print(f"\nWrote {os.path.join(WEB, 'rankings.json')}")


if __name__ == "__main__":
    main()
