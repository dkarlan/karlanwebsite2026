"""Turn raw pedigree facts into a history score and a novelty premium.

Reads data/pedigree.json (World Cup and continental records per team), sums
weighted points (config.PEDIGREE_WEIGHTS), divides by config.PEDIGREE_CAP and
clips to [0,1] to get history_i. novelty_i = 1 - history_i.

  history_i ~ 1  serial World Cup winner, joy fades fast, little novelty
  history_i ~ 0  debutant or never successful, joy lasts, maximum novelty

Writes data/pedigree.csv, merged into the workbook by build_workbook.py.
"""
import csv
import json
import os

import config

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")


def history_score(facts):
    w = config.PEDIGREE_WEIGHTS
    pts = (w["wc_titles"] * facts["wc_titles"]
           + w["wc_finals"] * facts["wc_finals"]
           + w["confed_titles"] * facts["confed_titles"]
           + w["ever_semi"] * (1 if facts["wc_semi"] else 0))
    return max(0.0, min(1.0, pts / config.PEDIGREE_CAP))


def main():
    with open(os.path.join(DATA, "pedigree.json"), encoding="utf-8") as fh:
        ped = json.load(fh)["teams"]

    rows = []
    for name, facts in ped.items():
        h = history_score(facts)
        rows.append({
            "name": name,
            "history": round(h, 4),
            "novelty": round(1.0 - h, 4),
            "wc_titles": facts["wc_titles"],
            "last_major_year": facts["last_major_year"] if facts["last_major_year"] else "",
            "debut": int(bool(facts["debut"])),
            "best_finish": facts.get("best_finish", ""),
        })

    out = os.path.join(DATA, "pedigree.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out} ({len(rows)} teams)")


if __name__ == "__main__":
    main()
