"""Fetch Google Trends interest-in-soccer as the free live proxy (pytrends).

Soccer interest has no clean single source, so the brief triangulates. Google
Trends is the best free live proxy: relative search interest for football/soccer
terms by country. pytrends is unofficial and rate-limited, so this script is
best-effort. It writes data/trends.csv on success; build_interest.py uses it if
present and otherwise falls back to the curated culture score in teams.json.

Usage:
    pip install pytrends
    python fetch_trends.py

Trends returns interest *relative to each country's own search volume*, which is
already a reasonable per-capita engagement proxy. We query in country batches
against a fixed reference term to keep the scale comparable.
"""
import csv
import json
import os
import time

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")
TEAMS = os.path.join(DATA, "teams.json")
OUT = os.path.join(DATA, "trends.csv")

# ISO-3166 alpha-2 codes Google Trends uses, keyed by team name.
GEO = {
    "Argentina": "AR", "Brazil": "BR", "Colombia": "CO", "Ecuador": "EC",
    "Paraguay": "PY", "Uruguay": "UY", "Mexico": "MX", "United States": "US",
    "Canada": "CA", "Panama": "PA", "Haiti": "HT", "Curacao": "CW",
    "Spain": "ES", "France": "FR", "England": "GB", "Portugal": "PT",
    "Netherlands": "NL", "Germany": "DE", "Norway": "NO", "Croatia": "HR",
    "Belgium": "BE", "Switzerland": "CH", "Austria": "AT", "Turkiye": "TR",
    "Scotland": "GB", "Czechia": "CZ", "Sweden": "SE", "Bosnia and Herzegovina": "BA",
    "Morocco": "MA", "Senegal": "SN", "Algeria": "DZ", "Cote d'Ivoire": "CI",
    "Egypt": "EG", "Ghana": "GH", "Tunisia": "TN", "South Africa": "ZA",
    "DR Congo": "CD", "Cape Verde": "CV", "Japan": "JP", "Iran": "IR",
    "South Korea": "KR", "Australia": "AU", "Qatar": "QA", "Saudi Arabia": "SA",
    "Uzbekistan": "UZ", "Iraq": "IQ", "Jordan": "JO", "New Zealand": "NZ",
}


def main():
    try:
        from pytrends.request import TrendReq
    except ImportError:
        print("pytrends not installed (pip install pytrends); skipping live "
              "Trends. build_interest.py will fall back to the culture score.")
        return

    with open(TEAMS, encoding="utf-8") as fh:
        teams = [t["name"] for t in json.load(fh)["teams"]]

    pytrends = TrendReq(hl="en-US", tz=0)
    rows = []
    for name in teams:
        geo = GEO.get(name)
        if not geo:
            continue
        try:
            pytrends.build_payload(["football"], timeframe="today 12-m", geo=geo)
            df = pytrends.interest_over_time()
            score = float(df["football"].mean()) if not df.empty else ""
        except Exception as exc:  # noqa: BLE001 - rate limits etc.
            print(f"  ! {name} ({geo}): {exc}")
            score = ""
        rows.append({"name": name, "geo": geo, "trends_score": score})
        time.sleep(2)  # be gentle with the unofficial endpoint

    if not any(r["trends_score"] != "" for r in rows):
        print("No Trends data returned; not overwriting. Falling back to culture score.")
        return

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["name", "geo", "trends_score"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
