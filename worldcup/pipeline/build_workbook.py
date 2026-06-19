"""Assemble the master table and a group-stage fixture list.

Merges teams.json with the fetched layers (worldbank.csv, and elo.csv /
interest.csv when present) into data/workbook.csv, the single human-readable
table every later step reads. Also writes data/fixtures.json, a round-robin
group-stage schedule with approximate dates so the live tool has matches to show.

Run the fetch/build scripts first; missing layers fall back to the teams.json
snapshot so this always produces a complete workbook.
"""
import csv
import json
import os
from datetime import date, timedelta

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")


def _load_map(path, key, value):
    out = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get(value) not in (None, ""):
                    out[row[key]] = row[value]
    return out


def build_workbook():
    with open(os.path.join(DATA, "teams.json"), encoding="utf-8") as fh:
        teams = json.load(fh)["teams"]

    wb = {}
    with open(os.path.join(DATA, "worldbank.csv"), encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            wb[row["name"]] = row
    elo = _load_map(os.path.join(DATA, "elo.csv"), "name", "elo")
    interest = _load_map(os.path.join(DATA, "interest.csv"), "name", "interest")

    # Pedigree layer (history, novelty, titles); built by build_pedigree.py.
    ped = {}
    ped_path = os.path.join(DATA, "pedigree.csv")
    if os.path.exists(ped_path):
        with open(ped_path, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                ped[r["name"]] = r

    cols = ["name", "confederation", "group", "host", "population", "consumption",
            "elo", "interest", "diaspora_m", "history", "novelty", "wc_titles",
            "last_major_year", "best_finish"]
    rows = []
    for t in teams:
        w = wb.get(t["name"], {})
        p = ped.get(t["name"], {})
        rows.append({
            "name": t["name"],
            "confederation": t["confederation"],
            "group": t["group"],
            "host": int(bool(t.get("host"))),
            "population": w.get("population", ""),
            "consumption": w.get("gni_pc_ppp", ""),
            "elo": elo.get(t["name"], t["elo"]),
            "interest": interest.get(t["name"], t["interest"]),
            "diaspora_m": t["diaspora_m"],
            "history": p.get("history", ""),
            "novelty": p.get("novelty", ""),
            "wc_titles": p.get("wc_titles", ""),
            "last_major_year": p.get("last_major_year", ""),
            "best_finish": p.get("best_finish", ""),
        })

    out = os.path.join(DATA, "workbook.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out} ({len(rows)} teams)")
    return teams


def build_fixtures(teams):
    """Round-robin group fixtures with approximate 2026 group-stage dates."""
    groups = {}
    for t in teams:
        groups.setdefault(t["group"], []).append(t["name"])

    # Matchday windows (approximate; the real schedule can be dropped in).
    md_start = {1: date(2026, 6, 11), 2: date(2026, 6, 17), 3: date(2026, 6, 23)}
    pairings = [(1, [(0, 1), (2, 3)]), (2, [(0, 2), (3, 1)]), (3, [(0, 3), (1, 2)])]

    fixtures = []
    for gi, g in enumerate(sorted(groups)):
        ts = groups[g]
        if len(ts) != 4:
            continue
        for md, pairs in pairings:
            day = md_start[md] + timedelta(days=gi % 6)
            for hi, ai in pairs:
                fixtures.append({
                    "date": day.isoformat(),
                    "matchday": md,
                    "group": g,
                    "home": ts[hi],
                    "away": ts[ai],
                })
    fixtures.sort(key=lambda f: (f["date"], f["group"]))
    out = os.path.join(DATA, "fixtures.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(fixtures, fh, indent=2)
    print(f"Wrote {out} ({len(fixtures)} group-stage matches)")


def main():
    teams = build_workbook()
    build_fixtures(teams)


if __name__ == "__main__":
    main()
