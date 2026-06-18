"""Build the normalized soccer-interest composite.

Triangulate, do not trust one feed. Components (config.INTEREST_WEIGHTS):
  - trends:    Google Trends search interest (data/trends.csv, if fetched).
  - big_count: FIFA Big Count registered players per capita (data/big_count.csv,
               optional; flagged stale).
  - culture:   curated culture / TV-reach proxy carried in teams.json ("interest").

Each available component is z-scored across the 48 teams, combined with the
configured weights (renormalized over whatever is present), then mapped back onto
the culture score's own mean and spread so the output stays an interpretable
0-1 engaged-fan share. With only the culture component present (the default,
offline), the output passes through unchanged. Writes data/interest.csv, which
the model prefers over the teams.json snapshot.
"""
import csv
import json
import os
import statistics as stats

import config

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")
TEAMS = os.path.join(DATA, "teams.json")
OUT = os.path.join(DATA, "interest.csv")


def _zscore(values):
    present = [v for v in values if v is not None]
    if len(present) < 2:
        return [0.0 for _ in values]
    mu = stats.mean(present)
    sd = stats.pstdev(present) or 1.0
    return [None if v is None else (v - mu) / sd for v in values]


def _load_csv_map(path, key, value):
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                out[row[key]] = float(row[value])
            except (ValueError, KeyError):
                continue
    return out


def main():
    with open(TEAMS, encoding="utf-8") as fh:
        teams = json.load(fh)["teams"]
    names = [t["name"] for t in teams]
    culture = {t["name"]: t["interest"] for t in teams}

    trends = _load_csv_map(os.path.join(DATA, "trends.csv"), "name", "trends_score")
    big = _load_csv_map(os.path.join(DATA, "big_count.csv"), "name", "players_per_1000")

    components = {
        "trends": [trends.get(n) for n in names],
        "big_count": [big.get(n) for n in names],
        "culture": [culture[n] for n in names],
    }
    have = {k: any(v is not None for v in vals) for k, vals in components.items()}
    z = {k: _zscore(components[k]) for k in components}

    # Renormalize weights over the components we actually have data for.
    active = {k: config.INTEREST_WEIGHTS[k] for k in components if have[k]}
    wsum = sum(active.values()) or 1.0

    culture_vals = list(culture.values())
    c_mu, c_sd = stats.mean(culture_vals), (stats.pstdev(culture_vals) or 0.1)

    rows = []
    for i, n in enumerate(names):
        num, den = 0.0, 0.0
        for k, w in active.items():
            if z[k][i] is not None:
                num += w * z[k][i]
                den += w
        composite_z = num / den if den else 0.0
        # Map composite z back onto the culture score's scale; clip to a sane band.
        share = max(0.05, min(0.85, c_mu + composite_z * c_sd))
        rows.append({
            "name": n,
            "interest": round(share, 4),
            "components": "+".join(k for k in active),
        })

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["name", "interest", "components"])
        w.writeheader()
        w.writerows(rows)
    used = ", ".join(k for k in active) or "none"
    print(f"Wrote {OUT} (components used: {used})")


if __name__ == "__main__":
    main()
