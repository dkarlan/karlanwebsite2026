"""Model parameters for the World Cup Happiness Index.

Every contestable assumption lives here, stated openly rather than buried in
code. Change a value, rerun run_all.py, and the ranking and the live tool both
update. The defaults follow the project brief; the comments give the reasoning
and the sensitivity band where the brief asks for one.
"""

# ---------------------------------------------------------------------------
# Marginal-utility curvature (the contestable assumption)
# ---------------------------------------------------------------------------
# Isoelastic utility u(c) = c^(1-ETA)/(1-ETA), so marginal utility MU ~ c^(-ETA).
# ETA = 1 is log utility (a 1% gain in consumption is worth the same to everyone,
# so absolute welfare weight scales like 1/c). ETA = 1.5 tilts further toward the
# poor. Run the model at both and report the band.
ETA = 1.0
ETA_SENSITIVITY = 1.5

# Reference consumption used to normalize the MU weight so it reads near 1.0 for
# a middle-income country instead of an unitless raw number. MU_i = (C_REF/c_i)^ETA.
# 10,000 international dollars is roughly the global median GNI per capita (PPP).
C_REF = 10000.0

# ---------------------------------------------------------------------------
# Per-fan happiness shock h (Cantril-ladder points from a title)
# ---------------------------------------------------------------------------
# A national-team triumph lifts subjective wellbeing briefly. Kavetsos &
# Szymanski (2010) find hosting/major-tournament success raises life satisfaction
# by a small but real amount; Dolan et al. and the wider literature put a major
# sporting high in the low tenths of a ladder point, decaying over weeks. We use a
# flat per-engaged-fan shock in ladder points (0-10 scale). This is an upper-ish
# estimate for a championship and is the unit that makes W_i interpretable as
# "ladder-points of happiness, MU-weighted, summed over fans."
H_PER_FAN = 0.10            # ladder points per engaged fan from winning the Cup
H_SENSITIVITY = (0.05, 0.20)

# ---------------------------------------------------------------------------
# Fan population reach (Extension 1 + 3): beyond home borders
# ---------------------------------------------------------------------------
# Engaged home fans = population * interest_share. Diaspora fans are counted at
# DIASPORA_WEIGHT of the home interest share (a migrant who emigrated is, if
# anything, more attached to the national team, so 1.0 is defensible). Continental
# solidarity: co-confederation neighbors feel a fraction of the joy of a regional
# side winning, captured as CONTINENTAL_WEIGHT of their own engaged-fan mass.
DIASPORA_WEIGHT = 1.0
CONTINENTAL_WEIGHT = 0.05

# ---------------------------------------------------------------------------
# Net welfare (Extension 2): subtract the losing side and the dark side
# ---------------------------------------------------------------------------
# The final has a loser. Their fans suffer a loss; loss aversion makes a defeat
# sting more than the symmetric win pleases, so the loser's loss is scaled above
# 1. We net the *expected* loser's loss inside the simulation (we know who the
# likely finalists are), not a fixed counterparty.
LOSS_AVERSION = 1.25        # a final defeat hurts 1.25x what the win delights

# Dark-side externality (Card & Dahl 2011): upset losses by a favored team raise
# family violence. We model a small negative term proportional to the favorite's
# engaged-fan mass, triggered in expectation by the probability the team is favored
# and loses. Expressed as a fraction of that team's gross W, deliberately modest
# and flagged as illustrative.
DARKSIDE_FRACTION = 0.04

# ---------------------------------------------------------------------------
# Probability source of record
# ---------------------------------------------------------------------------
# "elo" runs a Monte Carlo over the real 2026 bracket using Elo win
# probabilities (the free baseline). Swap in market or Opta numbers by writing a
# data/win_probabilities.csv and setting this to "file".
PROB_SOURCE = "elo"
ELO_HOME_ADVANTAGE = 60     # Elo points added for the three host nations at home
MC_ITERATIONS = 20000       # Monte Carlo tournament simulations

# ---------------------------------------------------------------------------
# Soccer-interest composite weights (build_interest.py)
# ---------------------------------------------------------------------------
# No clean single source, so triangulate and report a band. Weights on the
# z-scored components of the composite. Google Trends is the best free live proxy;
# FIFA Big Count is registered players (stale, flagged); the curated culture score
# stands in for TV reach / federation following until those feeds are wired in.
INTEREST_WEIGHTS = {
    "trends": 0.45,
    "big_count": 0.20,
    "culture": 0.35,
}
