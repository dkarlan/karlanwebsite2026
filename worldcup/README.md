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

The marginal happiness to the world if a team wins the Cup. **Not** expected
happiness. Win probability is deliberately excluded: the question is how much joy
a title would add, not how likely the title is. Rooting is free, so root for the
win that would matter most.

With the default parameters the pick is **DR Congo**: about 109 million people,
deep football interest, very low consumption, and no World Cup pedigree to take
for granted, so a title would land where the marginal value of joy is highest and
the memory would linger for years. The 2014 answer moved from Nigeria to its
larger, poorer neighbour. Serial winners like Brazil and Germany fall far down the
list: rich, and so used to winning that the glow of another title fades in a
season.

## The model

For each country *i*:

    W_i = N_i x MU_i x V_i

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

Four upgrades over 2014: (1) fan population reaches beyond home borders, (2) the
happiness bump is modelled, not assumed, (3) the figure is net of a documented
externality, (4) it values the lingering memory of a win, so a first-ever or
long-awaited title, remembered for years, counts for far more than a serial
winner's, which fades in a season.

## Layout

```
worldcup/
  data/
    teams.json        48-team field, the 5 Dec 2025 group draw, snapshot inputs
    pedigree.json     World Cup / continental records per team (curated)
    worldbank.csv     population + consumption (generated; committed snapshot)
    elo.csv           Elo ratings, shown as reference only (generated)
    interest.csv      soccer-interest composite (generated)
    pedigree.csv      history + novelty score (generated)
    workbook.csv      the merged master table (generated)
    fixtures.json     group-stage schedule (generated)
  pipeline/
    config.py         every parameter, with the reasoning and sensitivity bands
    fetch_worldbank.py  World Bank WDI: population + GNI per capita (PPP)
    fetch_elo.py        World Football Elo Ratings (reference column only)
    fetch_trends.py     Google Trends soccer interest via pytrends (optional)
    build_interest.py   z-score interest composite
    build_pedigree.py   history + novelty score from pedigree.json
    build_workbook.py   merge layers + build fixtures
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
- Elo ratings (eloratings.net) are fetched and shown as a strength reference only;
  they do not enter the score, since probability is excluded.

## Calibration references

- Rutledge, Skandali, Dayan & Dolan (2014, PNAS), a computational and neural
  model of momentary subjective well-being (happiness tracks reward prediction
  error: the novelty premium).
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
- The group draw is the official 5 December 2025 draw. The group-stage fixture
  dates are approximate placeholders for the live tool.
