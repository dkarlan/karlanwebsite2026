"""Fetch live results to drive the "beating expectations" view (phase 2).

Pulls the 2026 World Cup match list from football-data.org and reduces it to, for
each team, the deepest knockout stage reached and whether it has been eliminated.
Writes data/results.json, which the model uses to decide how far a team has beaten
its pre-tournament bar.

Needs a free football-data.org API token in the environment:

    export FOOTBALL_DATA_TOKEN=xxxxxxxx
    python fetch_results.py

Best-effort: with no token or on any network error it leaves the committed
results.json in place (default: pre-knockout, every team alive at depth 0). The
file is also safe to hand-edit during the tournament.
"""
import json
import os
import urllib.error
import urllib.request

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(DATA, "results.json")

API = "https://api.football-data.org/v4/competitions/WC/matches"

# football-data.org stage -> our knockout depth (reaching that stage).
STAGE_DEPTH = {
    "LAST_32": 1, "LAST_16": 2, "QUARTER_FINALS": 3,
    "SEMI_FINALS": 4, "FINAL": 5,
}

# football-data.org team names -> our team names (only where they differ).
NAME_MAP = {
    "Cote d'Ivoire": "Cote d'Ivoire", "Côte d'Ivoire": "Cote d'Ivoire",
    "Korea Republic": "South Korea", "IR Iran": "Iran", "Turkey": "Turkiye",
    "Türkiye": "Turkiye", "USA": "United States", "Cabo Verde": "Cape Verde",
    "Curaçao": "Curacao", "DR Congo": "DR Congo", "Congo DR": "DR Congo",
}


def _norm(name):
    return NAME_MAP.get(name, name)


def _fetch(token):
    req = urllib.request.Request(API, headers={"X-Auth-Token": token})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def _reduce(payload):
    """matches -> {team: {reached_depth, eliminated}}."""
    matches = payload.get("matches", [])
    reached, lost_ko, champion = {}, set(), None
    group_done = all(m["status"] == "FINISHED"
                     for m in matches if m["stage"] == "GROUP_STAGE")
    appeared_ko = set()

    for m in matches:
        depth = STAGE_DEPTH.get(m["stage"])
        if depth is None:
            continue
        home = _norm(m["homeTeam"]["name"]) if m["homeTeam"]["name"] else None
        away = _norm(m["awayTeam"]["name"]) if m["awayTeam"]["name"] else None
        for t in (home, away):
            if t:
                appeared_ko.add(t)
                reached[t] = max(reached.get(t, 0), depth)
        if m["status"] != "FINISHED" or not home or not away:
            continue
        winner = m["score"]["winner"]
        win, lose = (home, away) if winner == "HOME_TEAM" else (away, home)
        if winner in ("HOME_TEAM", "AWAY_TEAM"):
            lost_ko.add(lose)
            if m["stage"] == "FINAL":
                champion = win

    teams = {}
    all_names = set(reached) | {
        _norm(m[side]["name"]) for m in matches for side in ("homeTeam", "awayTeam")
        if m[side]["name"]}
    for t in all_names:
        depth = reached.get(t, 0)
        if t == champion:
            depth, eliminated = 6, False
        else:
            eliminated = (t in lost_ko) or (group_done and t not in appeared_ko)
        teams[t] = {"reached_depth": depth, "eliminated": eliminated}
    return teams


def main():
    token = os.environ.get("FOOTBALL_DATA_TOKEN")
    if not token:
        print("No FOOTBALL_DATA_TOKEN set; keeping committed results.json "
              "(hand-edit it to advance the tournament).")
        return
    try:
        payload = _fetch(token)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f"Results fetch failed ({exc}); keeping committed results.json.")
        return

    teams = _reduce(payload)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"as_of": payload.get("filters", {}), "source": "football-data.org",
                   "teams": teams}, fh, indent=2)
    alive = sum(1 for v in teams.values() if not v["eliminated"])
    print(f"Wrote {OUT}: {len(teams)} teams, {alive} still alive")


if __name__ == "__main__":
    main()
