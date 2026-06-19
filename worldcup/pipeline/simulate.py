"""Monte Carlo of the 2026 bracket to set the expectation bar.

This produces, for each team, the pre-tournament probability of reaching each
knockout stage under Elo. It is used only to set expectations for the
"beating expectations" view: how unlikely a run is, is how much joy it brings.
It does not weight or discount the welfare numbers.

Format: 12 groups of 4 (round robin), top two of each group plus the eight best
third-placed teams advance to a 32-team single-elimination knockout. Host nations
carry a configurable Elo bump. The knockout bracket is a fixed standard-seeded
bracket (strong teams meet late, no reseeding); the exact FIFA slot mapping can be
substituted without touching the rest of the model.

Depth scale: R32 = 1, R16 = 2, QF = 3, SF = 4, final = 5, champion = 6.
"""
import random

import config

# stage name -> depth
STAGE_DEPTH = {"R32": 1, "R16": 2, "QF": 3, "SF": 4, "F": 5, "Champion": 6}
STAGES = list(STAGE_DEPTH.keys())


def win_prob(elo_a, elo_b):
    return 1.0 / (1.0 + 10 ** (-(elo_a - elo_b) / 400.0))


def _wdl(elo_a, elo_b):
    we = win_prob(elo_a, elo_b)
    closeness = 1.0 - 2.0 * abs(we - 0.5)
    pdraw = 0.27 * closeness
    return (1.0 - pdraw) * we, pdraw, (1.0 - pdraw) * (1.0 - we)


def _eff(team, elo, hosts):
    return elo[team] + (config.ELO_HOME_ADVANTAGE if team in hosts else 0)


def _seed_positions(n):
    order = [1, 2]
    while len(order) < n:
        m = len(order) * 2 + 1
        order = [x for pair in ((s, m - s) for s in order) for x in pair]
    return order


SEED_ORDER_32 = _seed_positions(32)


def _simulate_group(group_teams, elo, hosts, rng):
    pts = {t: 0 for t in group_teams}
    tb = {t: 0.0 for t in group_teams}
    for i in range(len(group_teams)):
        for j in range(i + 1, len(group_teams)):
            a, b = group_teams[i], group_teams[j]
            pw, pd, _ = _wdl(_eff(a, elo, hosts), _eff(b, elo, hosts))
            r = rng.random()
            if r < pw:
                pts[a] += 3; tb[a] += 1; tb[b] -= 1
            elif r < pw + pd:
                pts[a] += 1; pts[b] += 1
            else:
                pts[b] += 3; tb[b] += 1; tb[a] -= 1
    ranked = sorted(group_teams, key=lambda t: (pts[t], tb[t], elo[t], rng.random()),
                    reverse=True)
    return ranked, pts, tb


def _build_bracket(groups, elo, hosts, rng):
    winners, runners, thirds = [], [], []
    for g, gteams in groups.items():
        ranked, pts, tb = _simulate_group(gteams, elo, hosts, rng)
        winners.append(ranked[0]); runners.append(ranked[1])
        thirds.append((ranked[2], pts[ranked[2]], tb[ranked[2]]))
    best_thirds = [t for t, _, _ in sorted(
        thirds, key=lambda x: (x[1], x[2], elo[x[0]], rng.random()), reverse=True)[:8]]
    seed_list = (sorted(winners, key=lambda t: elo[t], reverse=True)
                 + sorted(runners, key=lambda t: elo[t], reverse=True)
                 + sorted(best_thirds, key=lambda t: elo[t], reverse=True))
    slots = [None] * 32
    for seed, team in enumerate(seed_list, start=1):
        slots[SEED_ORDER_32.index(seed)] = team
    return [(slots[k], slots[k + 1]) for k in range(0, 32, 2)]


def expected_reach(groups, elo, hosts, iterations=None, seed=12345):
    """Return team -> {stage: probability of reaching it}."""
    iterations = iterations or config.MC_ITERATIONS
    rng = random.Random(seed)
    teams = [t for ts in groups.values() for t in ts]
    counts = {t: {s: 0 for s in STAGES} for t in teams}

    for _ in range(iterations):
        bracket = _build_bracket(groups, elo, hosts, rng)
        for a, b in bracket:
            counts[a]["R32"] += 1; counts[b]["R32"] += 1
        pairs = bracket
        stage_i = 1
        while len(pairs) >= 1:
            winners = []
            for a, b in pairs:
                winners.append(a if rng.random() < win_prob(_eff(a, elo, hosts),
                                                             _eff(b, elo, hosts)) else b)
            for w in winners:
                counts[w][STAGES[stage_i]] += 1
            if len(winners) == 1:
                break
            pairs = [(winners[k], winners[k + 1]) for k in range(0, len(winners), 2)]
            stage_i += 1

    return {t: {s: counts[t][s] / iterations for s in STAGES} for t in teams}
