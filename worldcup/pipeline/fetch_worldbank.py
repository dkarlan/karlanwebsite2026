"""Fetch population and consumption from the World Bank.

Sources (project data-source map):
  - Population: World Bank WDI series SP.POP.TOTL (UN World Population
    Prospects feeds this).
  - Consumption / MU weight: GNI per capita, PPP (NY.GNP.PCAP.PP.CD) as the
    free, complete cross-country series. The brief's first choice is the World
    Bank Poverty and Inequality Platform mean consumption per head; PIP has no
    value for every team and a heavier API, so we use GNI per capita (PPP) as
    the documented cross-check series here and note PIP as the upgrade path.

Writes data/worldbank.csv. Runs against the live API; on any network failure it
leaves an existing snapshot in place so the rest of the pipeline still runs.
"""
import csv
import json
import os
import time
import urllib.request

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")
TEAMS = os.path.join(DATA, "teams.json")
OUT = os.path.join(DATA, "worldbank.csv")

POP = "SP.POP.TOTL"
GNI_PPP = "NY.GNP.PCAP.PP.CD"


def _fetch_indicator(iso, indicator, retries=4):
    """Most-recent non-empty value for a country/indicator, or None."""
    url = (
        f"https://api.worldbank.org/v2/country/{iso}/indicator/{indicator}"
        f"?format=json&mrnev=1&per_page=5"
    )
    delay = 2
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                data = json.load(resp)
            if isinstance(data, list) and len(data) > 1 and data[1]:
                for row in data[1]:
                    if row.get("value") is not None:
                        return float(row["value"]), row["date"]
            return None, None
        except Exception as exc:  # noqa: BLE001 - log and back off
            if attempt == retries - 1:
                print(f"  ! {iso}/{indicator}: {exc}")
                return None, None
            time.sleep(delay)
            delay *= 2
    return None, None


def main():
    with open(TEAMS, encoding="utf-8") as fh:
        teams = json.load(fh)["teams"]

    rows = []
    for t in teams:
        iso = t["wb_iso"]
        name = t["name"]
        print(f"  {name} ({iso})")
        pop, pop_yr = _fetch_indicator(iso, POP)
        gni, gni_yr = _fetch_indicator(iso, GNI_PPP)
        if t.get("pop_override"):          # England / Scotland inside GBR
            pop, pop_yr = float(t["pop_override"]), "override"
        rows.append({
            "name": name,
            "wb_iso": iso,
            "population": int(pop) if pop else "",
            "population_year": pop_yr or "",
            "gni_pc_ppp": round(gni) if gni else "",
            "gni_year": gni_yr or "",
        })

    if not any(r["population"] for r in rows):
        print("No data fetched; keeping existing snapshot.")
        return

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {OUT} ({len(rows)} teams)")


if __name__ == "__main__":
    main()
