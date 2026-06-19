# World Cup Happiness Index: handoff to deankarlan.com

This project is built and tested in `dkarlan/karlanwebsite2026`, branch
`claude/world-cup-happiness-index-721lp6`, in the `worldcup/` folder. The live
site deploys from a different repo, `nukellogg/DK_PersonalSite` (master, to Azure
Front Door), which this session cannot reach. So this is a drop-in package: do the
five steps below from the **Karlan Website Build** pinned session, which has
`DK_PersonalSite` checked out.

Nothing here is published. Pushes from the World Cup session go only to the
`karlanwebsite2026` dev branch, which does not feed deankarlan.com.

## What the page is

A self-contained static tool (`worldcup/web/`: `index.html`, `app.js`,
`styles.css`, `rankings.json`) plus the Python pipeline (`worldcup/pipeline/`) and
data (`worldcup/data/`) that regenerate `rankings.json`. It already mirrors the
deankarlan.com top nav, so it reads as part of the site, and it links the prior
pieces (2014 original and reconsidered, 2018 Oxford, 2022 CGD) on the front page.

## Five steps to integrate (in DK_PersonalSite, master)

1. **Copy the folder.** Put the whole `worldcup/` folder at the root of
   `DK_PersonalSite`, so the tool is served at `/worldcup/`.

2. **Add the nav link.** In `DK_PersonalSite/index.html`, in the `<nav>` list, add
   a World Cup item right after the OCE@USAID Museum item:

   ```html
   <li><a href="/worldcup/">World Cup</a></li>
   ```

   (The existing nav uses `showPage(...)` for in-page routes; the World Cup tool is
   a separate static page, so it is a normal link, not a `showPage` call.)

3. **Add the updater workflow.** Copy
   `worldcup/deploy/worldcup-live-update.yml` to
   `DK_PersonalSite/.github/workflows/worldcup-live-update.yml`. It runs every 10
   minutes during the tournament window (June and July, match hours only),
   recomputes the ranking when results change, and commits the refreshed
   `worldcup/data/results.json` and `worldcup/web/rankings.json`. Scheduled
   workflows run from the default branch, so this must be on master.

4. **Set the secret.** In DK_PersonalSite, add an Actions secret
   `FOOTBALL_DATA_TOKEN` with a free football-data.org API key. Without it the
   updater is a safe no-op (the committed pre-knockout snapshot stays put), and
   you can still advance the bracket by hand in `worldcup/data/results.json`.

5. **Let Azure serve the static subpath.** If the site has an SPA fallback that
   rewrites all routes to `/index.html` (e.g. a `staticwebapp.config.json`), add an
   exception so `/worldcup/*` is served as-is. Otherwise `/worldcup/` may load the
   homepage instead of the tool.

## Regenerate locally (optional)

```bash
cd worldcup/pipeline
python run_all.py --offline   # rebuild rankings.json from committed snapshots
python run_all.py             # or fetch live World Bank, Elo, results
```

## Notes

- Freeze `worldcup/data/expectations.csv` from pre-tournament Elo (the committed
  file is that freeze). Do not rebuild it mid-tournament or the "beating
  expectations" bar will drift.
- The other nav items use absolute `https://www.deankarlan.com/...` links, so they
  work from `/worldcup/` immediately.
- The original 2014 NYT link is now the confirmed URL you provided.
