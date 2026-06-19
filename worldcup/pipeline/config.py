"""Model parameters for the World Cup Happiness Index.

Every contestable assumption lives here, stated openly. Change a value, rerun
run_all.py (or model.py), and the ranking and the live tool both update.

The published object is the marginal utility to the world if a team wins, NOT
expected utility. Win probability is deliberately excluded: the question is how
much joy a title would add, not how likely it is. Two history effects shape that
joy, both pointing toward teams unaccustomed to winning:

  - Novelty raises the size of the bump. Happiness tracks prediction error, so a
    long-awaited or first-ever win lands harder than a serial winner's next one
    (Rutledge et al. 2014 PNAS; Mellers et al. 1997; Koszegi & Rabin 2006).
  - Memory raises how long it lasts. Joy fades through hedonic adaptation, and
    repeated rewards adapt faster (Frederick & Loewenstein 1999), while a
    surprising, consequential win is encoded durably (flashbulb memory, Brown &
    Kulik 1977). So a no-pedigree team's joy decays slowly, a serial winner's
    fast. Measured daily-mood spikes are brief either way (Stieger et al. 2015),
    so the lasting value is the low-level remembered/identity utility, not the spike.
"""

# ---------------------------------------------------------------------------
# Marginal-utility curvature (the contestable assumption)
# ---------------------------------------------------------------------------
# Isoelastic utility u(c) = c^(1-ETA)/(1-ETA), so marginal utility MU ~ c^(-ETA).
# ETA = 1 is log utility (absolute welfare weight scales like 1/c). ETA = 1.5
# tilts further toward the poor. The tool shows both as a band.
ETA = 1.0
ETA_SENSITIVITY = 1.5

# Reference consumption normalizing the MU weight near 1 for a middle-income
# country: MU_i = (C_REF/c_i)^ETA. Roughly global median GNI per capita (PPP).
C_REF = 10000.0

# ---------------------------------------------------------------------------
# Per-fan value of a title (novelty-scaled)
# ---------------------------------------------------------------------------
# The happiness a title brings one engaged fan, in Cantril-ladder points: a base
# value scaled up by novelty, so a long-awaited or first-ever win is worth more.
# Happiness tracks prediction error, so an unexpected, unaccustomed win lands
# harder (Rutledge et al. 2014 PNAS; Mellers et al. 1997; Koszegi & Rabin 2006).
#
#     value_i = H0 * (1 + NOVELTY_ALPHA * novelty_i),   novelty_i = 1 - history_i
#
# H0 only sets the units (it scales every team equally), so NOVELTY_ALPHA is the
# real lever: at 0.8 a pure first-timer's title is worth 1.8x a serial winner's.
H0 = 0.10
NOVELTY_ALPHA = 0.8

# ---------------------------------------------------------------------------
# Pedigree score (history_i): history of success in international play
# ---------------------------------------------------------------------------
# Raw facts live in data/pedigree.json. Points are summed and divided by
# PEDIGREE_CAP, then clipped to [0,1]; a multiple-time World Cup winner sits near
# 1, a debutant at 0. Tune the weights to change what "success" counts as.
PEDIGREE_WEIGHTS = {
    "wc_titles": 5.0,      # World Cup wins
    "wc_finals": 2.5,      # World Cup final appearances (including wins)
    "confed_titles": 1.0,  # continental championship titles
    "ever_semi": 1.0,      # has reached at least one World Cup semifinal
}
PEDIGREE_CAP = 54.0        # points mapping to history = 1 (Brazil-level pedigree)

# ---------------------------------------------------------------------------
# Fan population reach (beyond home borders)
# ---------------------------------------------------------------------------
# Engaged home fans = population * interest. Diaspora fans count at DIASPORA_WEIGHT
# of the home interest share. Continental solidarity: co-confederation neighbours
# feel CONTINENTAL_WEIGHT of their own engaged-fan mass.
DIASPORA_WEIGHT = 1.0
CONTINENTAL_WEIGHT = 0.05

# ---------------------------------------------------------------------------
# Dark-side externality (net welfare)
# ---------------------------------------------------------------------------
# A modest haircut for documented negative externalities around high-stakes
# tournament matches (fan violence and the Card & Dahl 2011 effect). Flagged as
# illustrative; expressed as a fraction of gross welfare.
DARKSIDE_FRACTION = 0.04

# ---------------------------------------------------------------------------
# Soccer-interest composite weights (build_interest.py)
# ---------------------------------------------------------------------------
INTEREST_WEIGHTS = {
    "trends": 0.45,
    "big_count": 0.20,
    "culture": 0.35,
}
