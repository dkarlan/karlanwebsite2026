"""Fetch World Football Elo Ratings (the free win-probability baseline).

eloratings.net renders its tables client-side from data files, so a plain HTML
GET returns an empty shell. This script tries the known eloratings data
endpoints; on any failure it falls back to the Elo snapshot already carried in
teams.json (top-20 values are the real eloratings figures as of mid-June 2026,
the rest curated). On success it writes data/elo.csv, which the model prefers
over the snapshot.

The point is that the rating source is swappable: drop in a data/elo.csv with
your own numbers (market-implied, Opta-derived) and the model uses them.
"""
import csv
import json
import os
import urllib.request

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")
TEAMS = os.path.join(DATA, "teams.json")
OUT = os.path.join(DATA, "elo.csv")

# eloratings.net serves the full ranking as a TSV: column 2 is its own 2-letter
# country code, column 3 the Elo rating. We map those codes to our team names.
CANDIDATE_URLS = [
    "https://www.eloratings.net/World.tsv",
    "https://www.eloratings.net/2026.tsv",
]

# eloratings 2-letter codes for the 48-team field (EN/SC are England/Scotland).
ELO_CODE = {
    "Spain": "ES", "Argentina": "AR", "France": "FR", "England": "EN",
    "Colombia": "CO", "Brazil": "BR", "Portugal": "PT", "Netherlands": "NL",
    "Germany": "DE", "Norway": "NO", "Croatia": "HR", "Japan": "JP",
    "Ecuador": "EC", "Mexico": "MX", "Belgium": "BE", "Uruguay": "UY",
    "Switzerland": "CH", "Senegal": "SN", "Morocco": "MA", "Iran": "IR",
    "United States": "US", "South Korea": "KR", "Austria": "AT", "Algeria": "DZ",
    "Cote d'Ivoire": "CI", "Turkiye": "TR", "Canada": "CA", "Sweden": "SE",
    "Czechia": "CZ", "Egypt": "EG", "Ghana": "GH", "Paraguay": "PY",
    "Tunisia": "TN", "South Africa": "ZA", "DR Congo": "CD", "Qatar": "QA",
    "Australia": "AU", "Scotland": "SC", "Bosnia and Herzegovina": "BA",
    "Saudi Arabia": "SA", "Panama": "PA", "Uzbekistan": "UZ", "Iraq": "IQ",
    "Jordan": "JO", "Cape Verde": "CV", "Haiti": "HT", "Curacao": "CW",
    "New Zealand": "NZ",
}


def _try_fetch():
    """Return {eloratings_code: rating} or None."""
    for url in CANDIDATE_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                text = resp.read().decode("utf-8", "replace")
            ratings = {}
            for line in text.splitlines():
                parts = line.split("\t")
                if len(parts) >= 4:
                    try:
                        ratings[parts[2].strip()] = round(float(parts[3]))
                    except ValueError:
                        continue
            if len(ratings) > 20:
                print(f"  fetched {len(ratings)} ratings from {url}")
                return ratings
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {url}: {exc}")
    return None


def main():
    with open(TEAMS, encoding="utf-8") as fh:
        teams = json.load(fh)["teams"]

    live = _try_fetch()
    rows = []
    for t in teams:
        elo = t["elo"]
        source = "snapshot"
        code = ELO_CODE.get(t["name"])
        if live and code in live:
            elo = live[code]
            source = "eloratings.net"
        rows.append({"name": t["name"], "elo": elo, "source": source})

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["name", "elo", "source"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {OUT} ({len(rows)} teams; "
          f"{sum(1 for r in rows if r['source'] != 'snapshot')} live)")


if __name__ == "__main__":
    main()
