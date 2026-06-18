# World Cup Happiness Index 2026

A rebuild and extension of the 2014 NYT Upshot piece that asked which country's
World Cup win would add the most aggregate happiness. The 2014 answer was
Nigeria. The 48-team 2026 tournament, across the US, Mexico and Canada, pulls in
more low-income and first-time nations, which is exactly the part of the
distribution this index weights most.

This repo is the executable side of the project: a data pipeline (workstream A)
and a live "who to root for" tool (workstream B). The article and technical
appendix live in the writing project and read from here.

## The headline

Run the pipeline (below) and the model prints the ranking. With the default
parameters the 2026 pick is **DR Congo**: a country of about 109 million, deep
football interest, and very low consumption, so a title would land where the
marginal value of joy is highest. The answer moved from Nigeria to its even
larger, even poorer neighbour. Balancing for who can realistically win, **Brazil**
tops the expected-impact view: a huge, devoted fan base attached to a genuine
contender.

## The model

For each country *i*, the welfare from winning the Cup is

    W_i = N_i x h x MU_i

- **N_i** affected fan population: engaged home fans (population x interest),
  plus diaspora fans, plus a continental-solidarity share of co-confederation
  neighbours.
- **h** per-fan happiness shock from a win, in Cantril-ladder points, estimated
  from the wellbeing-from-football literature rather than assumed.
- **MU_i** marginal-utility weight under isoelastic utility, `MU_i = (C_REF/c_i)^eta`,
  with `c_i` mean consumption per head. Default `eta = 1`, sensitivity to 1.5.
  This is the contestable assumption and it is stated openly in `config.py`.

The published object is expected, net and dynamic:

    E[dW from i] = P(champion_i) x W_net_i  -  (loss aversion) x E[beaten finalist's loss]

`W_net_i` is `W_i` minus a documented dark-side externality. `P(champion_i)`
comes from a Monte Carlo over the real 2026 bracket and updates each round.

Four upgrades over 2014: (1) fan population reaches beyond home borders, (2) the
happiness bump is estimated, (3) the figure is net of the losing side and
negative externalities, (4) it is probability-weighted and updates as teams go out.

## Layout

```
worldcup/
  data/
    teams.json        48-team field, the 5 Dec 2025 group draw, snapshot inputs
    worldbank.csv     population + consumption (generated; committed snapshot)
    elo.csv           Elo ratings (generated)
    interest.csv      soccer-interest composite (generated)
    workbook.csv      the merged master table (generated)
    fixtures.json     group-stage schedule (generated)
    state.json        tournament state for the live loop (optional)
  pipeline/
    config.py         every parameter, with the reasoning and sensitivity bands
    fetch_worldbank.py  World Bank WDI: population + GNI per capita (PPP)
    fetch_elo.py        World Football Elo Ratings (free win-prob baseline)
    fetch_trends.py     Google Trends soccer interest via pytrends (optional)
    build_interest.py   z-score interest composite
    build_workbook.py   merge layers + build fixtures
    simulate.py         Monte Carlo of the 48-team format
    model.py            welfare math, writes web/rankings.json
    update_round.py     advance tournament state for the live loop
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

## Round-by-round updates

The recommendation is dynamic. As the tournament progresses, edit the state and
rerun the model:

```bash
cd worldcup/pipeline
python update_round.py eliminate "South Africa" "Czechia"   # group-stage exits
python update_round.py knockout R32 bracket.json            # lock the round of 32
python model.py                                             # refresh rankings.json
```

`bracket.json` is a list of pairs, 16 for R32 down to 1 for the final.

## Data sources

- Population, consumption: World Bank WDI (`SP.POP.TOTL`, `NY.GNP.PCAP.PP.CD`).
  The brief's first choice for the utility weight is the World Bank Poverty and
  Inequality Platform mean consumption; GNI per capita (PPP) is the complete,
  free cross-check used here, with PIP as the upgrade path.
- Win probabilities: World Football Elo Ratings (eloratings.net), simulated over
  the bracket. Market-implied or Opta numbers can be dropped in via `elo.csv` or
  a `win_probabilities.csv` and `config.PROB_SOURCE`.
- Soccer interest: triangulated. Google Trends (free live proxy), FIFA Big Count
  (registered players, stale), and a curated culture/TV-reach score, combined as
  a z-score composite.
- Subjective-wellbeing calibration for `h`: Gallup World Poll Cantril ladder via
  the World Happiness Report.

## Calibration references

- Kavetsos and Szymanski (2010, J. Econ. Psychology) on sporting events and
  national wellbeing (the size of `h`).
- Card and Dahl (2011, QJE) on upset football losses and family violence (the
  dark-side externality).
- Edmans, Garcia and Norli (2007, J. Finance) on football results and next-day
  stock returns (sentiment magnitude).
- Depetris-Chauvin, Durante and Campante (2020, AER) on national-team success,
  cohesion and conflict (the development-dividend angle).

## Caveats

- `eta` is a value judgement, not a measurement. The tool exposes the band.
- Diaspora, solidarity and interest figures are documented estimates; they are
  the levers most worth refining.
- The group draw is the official 5 December 2025 draw. The knockout bracket is
  approximated by a fixed standard seeding; the exact FIFA R32 slot mapping can be
  substituted in `simulate.py` without changing the rest of the model.
- The group-stage fixture dates are approximate placeholders for the live tool.
- Elo ratings beyond the current top 20 in the committed snapshot are estimates;
  `fetch_elo.py` refreshes them when the source is reachable.
