# World Cup Happiness Index 2026

A rebuild and extension of the 2014 NYT Upshot piece that asked which country's
World Cup win would add the most aggregate happiness. The 2014 answer was
Nigeria. The 48-team 2026 tournament, across the US, Mexico and Canada, pulls in
more low-income and first-time nations, which is exactly the part of the
distribution this index weights most.

This repo is the executable side of the project: a data pipeline (workstream A)
and a live "who to root for" tool (workstream B). The article and technical
appendix live in the writing project and read from here.

## What this measures

The happiness a team's run adds to the world. Win probability is never used to
weight or discount the score. There are two views:

- **Beating expectations (default).** Joy from overperforming: a deep run, valued
  by how unlikely it was, with later rounds counting more. Each team's
  pre-tournament odds set the bar; clearing a low bar is what brings joy, so
  underdogs are rewarded, not penalized.
- **If they win the Cup.** The marginal happiness a title alone would add.

With the default parameters **DR Congo** tops both: about 109 million people, deep
football interest, very low consumption, no World Cup pedigree to take for
granted, and little expected of them, so every round they survive is a jolt of joy
that lands where the marginal value is highest and lingers for years. The 2014
answer moved from Nigeria to its larger, poorer neighbour. Serial winners and rich
favourites fall far down: a title there is worth less per fan and would surprise
no one.

## The model

For each country *i*, the value of winning the Cup is

    W_i = N_i x MU_i x V_i

and the default "beating expectations" value multiplies that by a surprise factor,
`W_i x Surprise_i` (defined below).

- **N_i** affected fan population: engaged home fans (population x interest),
  plus diaspora fans, plus a continental-solidarity share of co-confederation
  neighbours.
- **MU_i** marginal-utility weight under isoelastic utility, `MU_i = (C_REF/c_i)^eta`,
  with `c_i` consumption per head. Default `eta = 1`, sensitivity to 1.5. A
  windfall counts for more where people have less. This is the contestable
  assumption and it is stated openly in `config.py`.
- **V_i** per-fan value of the title: a title is a glow that lingers and slowly
  fades, so we take its present value, discounting future happiness at rate `r_i`,

      V_i = integral_0^inf H0 e^(-r_i t) dt = H0 / r_i,   r_i = R_LO + (R_HI - R_LO) history_i

  `H0` only sets the units, so the discount rate is the lever.

`W_net_i` nets out a documented dark-side externality.

### Why the memory lingers

A championship is not a one-off jolt; it is a glow that fades over time. The
essence sits in how fast it fades. For a country unused to winning, the memory
lingers far longer, so we discount it less and the title is worth more in present
value. A serial winner adapts quickly, the joy fades in a season, and another
title adds little.

This rests on three findings: happiness tracks prediction error, so an
unaccustomed win lands harder (Rutledge, Skandali, Dayan & Dolan 2014, PNAS;
Mellers et al. 1997; Koszegi & Rabin 2006); joy fades through hedonic adaptation,
and repeated rewards adapt faster (Frederick & Loewenstein 1999); and a
surprising, consequential win is encoded durably (flashbulb memory, Brown & Kulik
1977). The daily-mood spike is brief either way (Stieger et al. 2015), so the
lasting value is the low-level remembered and identity glow, which is what the
discount rate captures.

`history_i` in [0,1] is the pedigree score (`data/pedigree.json`,
`build_pedigree.py`): World Cup titles, final appearances, continental titles and
a World Cup semifinal flag, summed and capped. A multiple-time winner sits near 1
(short memory), a debutant at 0 (long memory).

### Beating expectations (the default)

Joy comes from beating the bar. The bar is each team's pre-tournament chance of
reaching each knockout stage, `P_i(reach depth k)`, from an Elo Monte Carlo over
the real draw (`simulate.py`, `build_expectations.py`). The surprise of reaching a
stage is how unlikely it was, `1 - P`, and deeper stages count for more:

    Surprise_i = sum_{k=1..maxk}  (k ** STAGE_WEIGHT_EXP) * (1 - P_i(reach depth k))

`maxk` is the depth a team has actually reached if it is out, else 6 (a live team
keeps its full forward potential). So before kickoff every team carries its full
capacity to surprise; a favourite knocked out early collapses toward zero, and an
underdog that advances banks real, depth-weighted surprise. As favourites fall and
the field narrows, surviving long shots rise, so overperformance matters more as
the tournament goes on. The realized depths come from a live results feed
(`fetch_results.py`, football-data.org); with no feed the committed snapshot has
every team alive pre-knockout.

Expectation as a reference point is the same prediction-error idea that drives the
memory term (Rutledge et al. 2014; Mellers et al. 1997; Koszegi & Rabin 2006). It
is not probability weighting: the odds set the bar, they never shrink the score.

Four upgrades over 2014: (1) fan population reaches beyond home borders, (2) the
happiness bump is modelled, not assumed, (3) the figure is net of a documented
externality, (4) it values the lingering memory of a win and rewards beating
expectations, so a long shot's deep run, remembered for years, counts for far
more than a favourite meeting them.

## Layout

```
worldcup/
  data/
    teams.json        48-team field, the 5 Dec 2025 group draw, snapshot inputs
    pedigree.json     World Cup / continental records per team (curated)
    worldbank.csv     population + consumption (generated; committed snapshot)
    elo.csv           Elo ratings: the expectation bar and a reference (generated)
    interest.csv      soccer-interest composite (generated)
    pedigree.csv      history + novelty score (generated)
    expectations.csv  pre-tournament P(reach each stage), the bar (generated)
    results.json      live tournament state for beating-expectations (hand or feed)
    workbook.csv      the merged master table (generated)
    fixtures.json     group-stage schedule (generated)
  pipeline/
    config.py         every parameter, with the reasoning and sensitivity bands
    fetch_worldbank.py  World Bank WDI: population + GNI per capita (PPP)
    fetch_elo.py        World Football Elo Ratings (the expectation bar)
    fetch_trends.py     Google Trends soccer interest via pytrends (optional)
    fetch_results.py    live results via football-data.org (optional; phase 2)
    build_interest.py   z-score interest composite
    build_pedigree.py   history + novelty score from pedigree.json
    build_workbook.py   merge layers + build fixtures
    build_expectations.py  Elo Monte Carlo -> P(reach each stage)
    simulate.py         Monte Carlo of the 48-team format (sets the bar)
    model.py            welfare math, writes web/rankings.json
    run_all.py          fetch + build + model
  web/
    index.html, app.js, styles.css   the live tool (static, no build step)
    rankings.json     model output the tool reads (generated)
```

## Run it

```bash
cd worldcup/pipeline

# Full pipeline, fetching live data where the network allows:
python run_all.py

# Or use the committed snapshots, no network:
python run_all.py --offline

# Optional live Google Trends layer:
pip install -r requirements.txt
python fetch_trends.py && python build_interest.py && python model.py
```

For the live "beating expectations" view, set a free football-data.org token to
pull results; otherwise edit `data/results.json` by hand to advance the bracket:

```bash
export FOOTBALL_DATA_TOKEN=xxxxxxxx
python fetch_results.py && python model.py
```

Then open the tool:

```bash
cd ../web && python -m http.server 8000   # http://localhost:8000
```

## Tuning

Everything lives in `config.py`, each value commented with its reasoning. The
biggest levers:

- `ETA` (1 to 1.5): how hard the index favours low-income countries.
- `R_LO` / `R_HI`: the discount rates at the no-pedigree and serial-winner ends,
  i.e. the memory half-lives (default about 14 years versus 1.4 years). The
  closer they are, the less pedigree matters.
- `STAGE_WEIGHT_EXP`: how much more a late-round upset counts than an early one
  (1 = weight equals depth; raise it to punch up deep runs).
- `PEDIGREE_WEIGHTS` / `PEDIGREE_CAP`: what counts as a "history of success".
- `DIASPORA_WEIGHT`, `CONTINENTAL_WEIGHT`: how far fandom reaches beyond home.

Change a number, rerun `python model.py`, and the ranking and the tool update.

## Data sources

- Population, consumption: World Bank WDI (`SP.POP.TOTL`, `NY.GNP.PCAP.PP.CD`).
  GNI per capita (PPP) is the complete, free cross-country series; the World Bank
  Poverty and Inequality Platform mean consumption is the upgrade path.
- Pedigree: World Cup and confederation-championship records (`pedigree.json`,
  curated; spot-check before print).
- Soccer interest: triangulated. Google Trends (free live proxy), FIFA Big Count
  (registered players, stale), and a curated culture/TV-reach score, as a z-score
  composite.
- Subjective-wellbeing calibration for the joy size and decay: Gallup World Poll
  Cantril ladder via the World Happiness Report, plus the references below.
- Expectation bar and Elo: World Football Elo Ratings (eloratings.net), simulated
  over the draw to get each team's pre-tournament chance of reaching each stage.
  This sets the bar for the beating-expectations view; it never weights the score.
  Market-implied or Opta numbers can be dropped in via a probabilities file.
- Live results: football-data.org (free tier) via `fetch_results.py`; the bracket
  can also be advanced by hand in `results.json`.

## Calibration references

- Rutledge, Skandali, Dayan & Dolan (2014, PNAS), a computational and neural
  model of momentary subjective well-being (happiness tracks reward prediction
  error: the basis for both the memory term and beating expectations).
- Mellers, Schwartz, Ho & Ritov (1997, Psychological Science), decision affect
  theory (surprise amplifies emotional reactions).
- Koszegi & Rabin (2006, QJE), a model of reference-dependent preferences
  (expectations as the reference point).
- Frederick & Loewenstein (1999), hedonic adaptation (joy fades, and repeated
  rewards adapt faster: the discount rate rises with pedigree).
- Brown & Kulik (1977, Cognition), flashbulb memories (surprising, consequential
  wins are encoded durably: the glow lingers).
- Stieger, Goetz & Gehrig (2015, Frontiers in Psychology), soccer results affect
  well-being only briefly (the daily-mood spike is short, so the lasting value is
  the remembered glow that the discount rate captures).
- Kavetsos & Szymanski (2010), Card & Dahl (2011), Edmans, Garcia & Norli (2007),
  Depetris-Chauvin, Durante & Campante (2020): sporting events and wellbeing, the
  dark-side externality, sentiment magnitude, and the development dividend.

## Caveats

- `eta` and the memory half-lives are value-laden modelling choices, not measured
  constants. The mechanisms are well-established; the magnitudes are seeded from
  the literature and exposed for tuning. The tool shows the eta band.
- Diaspora, solidarity and interest figures are documented estimates; they are the
  levers most worth refining.
- Pedigree facts in `pedigree.json` are curated to appendix standard but should be
  spot-checked before print.
- The expectation bar (`expectations.csv`) should be frozen from pre-tournament
  Elo; the committed snapshot is that freeze. The group draw is the official
  5 December 2025 draw, and the group-stage fixture dates are approximate
  placeholders for the live tool.
- The group draw is the official 5 December 2025 draw. The group-stage fixture
  dates are approximate placeholders for the live tool.
