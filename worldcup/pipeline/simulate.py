"""Monte Carlo of the 2026 World Cup to get P(reach round) and P(champion).

Format: 12 groups of 4 (round robin), top two of each group plus the eight best
third-placed teams advance to a 32-team single-elimination knockout (R32, R16,
QF, SF, final). Match outcomes are driven by Elo win probabilities; host nations
carry a configurable Elo bump because they play at home.

The knockout bracket is approximated by a fixed standard-seeded bracket: the 32
qualifiers are ranked (group winners, then runners-up, then best thirds, Elo as
tie-break) and placed in canonical seed positions so strong teams meet late and
no reseeding occurs between rounds. The exact FIFA R32 slot mapping can be
substituted without touching the rest of the model.

Dynamic updates: pass a `state` dict to start partway through. Supported:
  {"stage": "group", "eliminated": [...]}                  # default, pre-tournament
  {"stage": "R32"|"R16"|"QF"|"SF"|"F", "bracket": [[a,b],...]}  # lock a knockout round
The live tool advances `stage`/`bracket` as results come in and reruns.
"""
import math
import random

import config

STAGES = ["R32", "R16", "QF", "SF", "F", "Champion"]


def win_prob(elo_a, elo_b):
    """P(A beats B), draws excluded (knockout)."""
    return 1.0 / (1.0 + 10 ** (-(elo_a - elo_b) / 400.0))


def _wdl(elo_a, elo_b):
    """Group-stage win/draw/loss probabilities for A."""
    we = win_prob(elo_a, elo_b)                      # expected points share
    closeness = 1.0 - 2.0 * abs(we - 0.5)            # 1 when even, 0 when lopsided
    pdraw = 0.27 * closeness
    pwin = (1.0 - pdraw) * we
    ploss = (1.0 - pdraw) * (1.0 - we)
    return pwin, pdraw, ploss


def _eff_elo(team, elo, hosts):
    e = elo[team]
    if team in hosts:
        e += config.ELO_HOME_ADVANTAGE
    return e


# Canonical single-elimination seed order for 32 slots: produces 1v32, 16v17,
# 8v25, ... so seeds are spread across the bracket.
def _seed_positions(n):
    order = [1, 2]
    while len(order) < n:
        m = len(order) * 2 + 1
        order = [x for pair in ((s, m - s) for s in order) for x in pair]
    return order


SEED_ORDER_32 = _seed_positions(32)


def _simulate_group(group_teams, elo, hosts, rng):
    """Round robin; return team -> (points, tiebreak) and ranked list."""
    pts = {t: 0 for t in group_teams}
    tb = {t: 0.0 for t in group_teams}               # Elo-weighted goal-diff proxy
    for i in range(len(group_teams)):
        for j in range(i + 1, len(group_teams)):
            a, b = group_teams[i], group_teams[j]
            pw, pd, _ = _wdl(_eff_elo(a, elo, hosts), _eff_elo(b, elo, hosts))
            r = rng.random()
            if r < pw:
                pts[a] += 3
                tb[a] += 1; tb[b] -= 1
            elif r < pw + pd:
                pts[a] += 1; pts[b] += 1
            else:
                pts[b] += 3
                tb[b] += 1; tb[a] -= 1
    ranked = sorted(group_teams,
                    key=lambda t: (pts[t], tb[t], elo[t], rng.random()),
                    reverse=True)
    return ranked, pts, tb


def _play_knockout(bracket, elo, hosts, rng, reached):
    """Play a fixed bracket to a winner. Return (champion, beaten finalist)."""
    stage_idx = STAGES.index("R32") if len(bracket) * 2 == 32 else _stage_for(len(bracket) * 2)
    teams_in = [t for pair in bracket for t in pair]
    for t in teams_in:
        reached[t].add(STAGES[stage_idx])
    round_pairs = bracket
    runner_up = None
    while len(round_pairs) >= 1:
        winners, losers = [], []
        for a, b in round_pairs:
            pa = win_prob(_eff_elo(a, elo, hosts), _eff_elo(b, elo, hosts))
            if rng.random() < pa:
                winners.append(a); losers.append(b)
            else:
                winners.append(b); losers.append(a)
        stage_idx += 1
        for w in winners:
            reached[w].add(STAGES[stage_idx])
        if len(winners) == 1:
            return winners[0], losers[0]
        round_pairs = [(winners[k], winners[k + 1]) for k in range(0, len(winners), 2)]
    return None, None


def _stage_for(n_teams):
    return STAGES.index({32: "R32", 16: "R16", 8: "QF", 4: "SF", 2: "F"}[n_teams])


def _build_bracket_from_groups(groups, elo, hosts, rng):
    """Simulate all groups, select 32, seed them into a fixed bracket."""
    winners, runners, thirds = [], [], []
    for g, gteams in groups.items():
        ranked, pts, tb = _simulate_group(gteams, elo, hosts, rng)
        winners.append(ranked[0])
        runners.append(ranked[1])
        thirds.append((ranked[2], pts[ranked[2]], tb[ranked[2]]))
    best_thirds = [t for t, _, _ in sorted(
        thirds, key=lambda x: (x[1], x[2], elo[x[0]], rng.random()), reverse=True)[:8]]

    # Overall seeding: winners, then runners, then best thirds; Elo within tier.
    seed_list = (
        sorted(winners, key=lambda t: elo[t], reverse=True)
        + sorted(runners, key=lambda t: elo[t], reverse=True)
        + sorted(best_thirds, key=lambda t: elo[t], reverse=True)
    )
    slots = [None] * 32
    for seed, team in enumerate(seed_list, start=1):
        slots[SEED_ORDER_32.index(seed)] = team
    return [(slots[k], slots[k + 1]) for k in range(0, 32, 2)]


def simulate(groups, elo, hosts, state, team_value=None, iterations=None, seed=12345):
    """Run the Monte Carlo.

    Returns (probs, exp_loser_loss) where
      probs[t][stage]    = probability team t reaches that stage / wins,
      exp_loser_loss[t]  = expected gross value of the finalist t beats when t is
                           champion (sum over sims of team_value[runner-up] when t
                           wins, divided by iterations). Zero if team_value is None.
    """
    iterations = iterations or config.MC_ITERATIONS
    rng = random.Random(seed)
    all_teams = [t for gteams in groups.values() for t in gteams]
    counts = {t: {s: 0 for s in STAGES} for t in all_teams}
    loser_loss = {t: 0.0 for t in all_teams}
    team_value = team_value or {}

    stage = (state or {}).get("stage", "group")
    eliminated = set((state or {}).get("eliminated", []))
    locked = (state or {}).get("bracket")

    for _ in range(iterations):
        reached = {t: set() for t in all_teams}
        if stage == "group":
            live_groups = {g: [t for t in ts if t not in eliminated]
                           for g, ts in groups.items()}
            bracket = _build_bracket_from_groups(live_groups, elo, hosts, rng)
        else:
            bracket = [tuple(p) for p in locked]
        champ, runner = _play_knockout(bracket, elo, hosts, rng, reached)
        if champ:
            reached[champ].add("Champion")
            loser_loss[champ] += team_value.get(runner, 0.0)
        for t, stages in reached.items():
            for s in stages:
                counts[t][s] += 1

    probs = {t: {s: counts[t][s] / iterations for s in STAGES} for t in all_teams}
    exp_loser_loss = {t: loser_loss[t] / iterations for t in all_teams}
    return probs, exp_loser_loss
