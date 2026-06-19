"""Build the expectation bar: pre-tournament P(reach each knockout stage).

Runs the Elo Monte Carlo (simulate.py) over the real 2026 draw and writes
data/expectations.csv: for each team the probability of reaching R32, R16, QF,
SF, the final and the title, plus expected depth (the expected number of knockout
rounds reached, 0 to 6). The "beating expectations" view reads this as the bar.

Freeze this before kickoff so the bar stays the pre-tournament expectation; the
committed CSV is that snapshot.
"""
import csv
import os

import config
import simulate

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")


def _load_workbook():
    rows = {}
    with open(os.path.join(DATA, "workbook.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows[r["name"]] = r
    return rows


def main():
    teams = _load_workbook()
    groups = {}
    for t in teams.values():
        groups.setdefault(t["group"], []).append(t["name"])
    elo = {n: float(t["elo"]) for n, t in teams.items()}
    hosts = {n for n, t in teams.items() if t["host"] == "1"}

    reach = simulate.expected_reach(groups, elo, hosts)

    out = os.path.join(DATA, "expectations.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "p_r32", "p_r16", "p_qf", "p_sf", "p_final",
                    "p_champion", "expected_depth"])
        for n in teams:
            p = reach[n]
            depth = sum(p[s] for s in simulate.STAGES)  # E[rounds reached]
            w.writerow([n, round(p["R32"], 4), round(p["R16"], 4), round(p["QF"], 4),
                        round(p["SF"], 4), round(p["F"], 4), round(p["Champion"], 4),
                        round(depth, 3)])
    print(f"Wrote {out} ({len(teams)} teams)")


if __name__ == "__main__":
    main()
