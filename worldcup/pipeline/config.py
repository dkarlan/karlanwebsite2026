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

# Subsistence offset (Stone-Geary). We add a fixed amount to consumption before
# taking the weight: MU = (C_REF / (c + CONSUMPTION_OFFSET))^ETA. This gently
# compresses the weighting among the very poorest (so super-poor and merely-poor
# are close, but never identical, and poverty is never ignored), while leaving
# richer countries almost unchanged, so the gap between the poor and the rich is
# preserved. Raise it to compress the poor end more; set it to zero for the pure
# isoelastic curve.
CONSUMPTION_OFFSET = 3000.0

# ---------------------------------------------------------------------------
# Per-fan value of a title (present value of a lingering memory)
# ---------------------------------------------------------------------------
# A title is not a one-off jolt; it is a glow that lingers and slowly fades. We
# value it as the present value of that fading stream of happiness, discounting
# future happiness at rate r_i:
#
#     V_i = integral_0^inf  H0 * e^(-r_i t) dt  =  H0 / r_i
#
# The essence sits in the discount rate. For a country unused to winning, the
# memory lingers far longer, so we discount it less and the title is worth more
# today. Pedigree sets the rate:
#
#     r_i = R_LO + (R_HI - R_LO) * history_i,    history_i in [0,1]
#
# Low pedigree  -> low rate  -> long memory (half-life ln2/R_LO ~ 14 years).
# Serial winner -> high rate -> shorter memory (half-life ln2/R_HI ~ 4 years).
# H0 only sets the units, so the half-life band (R_LO, R_HI) is the real lever.
H0 = 0.10
R_LO = 0.05
R_HI = 0.173

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
# feel a share of their own engaged-fan mass when a regional side wins. The share
# is set per confederation: Africa and Asia carry the most, on the premise that
# neither continent has ever won a World Cup, so continental pride is more at
# stake. Europe and South America, with many past winners and fierce intra-rivalry,
# carry the least.
DIASPORA_WEIGHT = 1.0
CONTINENTAL_WEIGHTS = {
    "CAF": 0.20,        # Africa: never won, strong shared pride
    "AFC": 0.20,        # Asia: never won, strong shared pride
    "CONCACAF": 0.06,   # never won, but a smaller, looser bloc
    "OFC": 0.05,
    "CONMEBOL": 0.02,   # five-time winners present, intra-rivalry, little shared joy
    "UEFA": 0.02,       # many past winners, intra-rivalry, little shared joy
}

# ---------------------------------------------------------------------------
# Display scale (gap compression)
# ---------------------------------------------------------------------------
# Raw welfare is dominated by the largest, poorest country (DR Congo), which leaves
# every other team looking identical near zero. The numbers are also noisy estimates
# of a contestable quantity, so the size of that lead is not to be taken literally.
# We therefore display each view on a compressed scale, keeping the order and the
# leader at 100 but lifting and spreading the rest so the comparisons are legible:
#
#     index_i = 100 * (W_i / W_max) ** SCORE_CONCAVITY
#
# Currently off (1.0 = identity, raw gaps shown). The spread now comes from the
# consumption floor above, a structural change to the weighting, rather than a
# display transform. Lower it below 1 only if you want extra cosmetic compression.
SCORE_CONCAVITY = 1.0

# ---------------------------------------------------------------------------
# Dark-side externality (NOT currently incorporated)
# ---------------------------------------------------------------------------
# Card & Dahl (2011) show that upset losses by a favored team raise domestic
# violence. That real cost is not modelled here. A flat fraction would only scale
# every team equally and cancel out of the normalized index, so it is left at zero
# rather than pretending to net it out. Captured as a caveat in the writeup and a
# priority for a future version, where it would fall harder on the favored side.
DARKSIDE_FRACTION = 0.0

# ---------------------------------------------------------------------------
# Soccer-interest composite weights (build_interest.py)
# ---------------------------------------------------------------------------
INTEREST_WEIGHTS = {
    "trends": 0.45,
    "big_count": 0.20,
    "culture": 0.35,
}

# ---------------------------------------------------------------------------
# Beating expectations (the default view)
# ---------------------------------------------------------------------------
# Joy comes from beating the bar. The bar is each team's pre-tournament chance of
# reaching each knockout stage, from an Elo Monte Carlo (simulate.py,
# build_expectations.py). The surprise of reaching a stage is how unlikely it was,
# 1 - P(reach stage), and deeper stages count for more (an upset in the
# quarterfinals matters more than one in the round of 32). With STAGE_WEIGHT_EXP =
# 1 the weight on a stage equals its depth (R32 = 1 ... champion = 6); raise it to
# punch up the late rounds further.
#
#   surprise_i = sum_{k=1..maxk} (k ** STAGE_WEIGHT_EXP) * (1 - P_i(reach depth k))
#
# maxk = the depth a team actually reached if eliminated, else 6 (a live team keeps
# its full forward potential). So before kickoff every team carries its full
# capacity to surprise; teams that flop fall to zero, and underdogs that advance
# bank real surprise. The index multiplies the title's present value by surprise_i.
STAGE_WEIGHT_EXP = 1.0
ELO_HOME_ADVANTAGE = 60     # Elo points for the three host nations at home
MC_ITERATIONS = 20000       # Monte Carlo tournament simulations for the bar
