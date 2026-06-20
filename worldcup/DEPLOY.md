# Deploy the Utilitarian World Cup Guide to deankarlan.com

This is a copy-paste deploy guide for a Claude Code session that has access to
the **live site repo** (`nukellogg/DK_PersonalSite`, deployed to Azure Front
Door, served at https://www.deankarlan.com/). The finished tool lives in **this**
repo (`dkarlan/karlanwebsite2026`) on branch
**`claude/world-cup-happiness-index-721lp6`**.

If you are the session with the live-site repo loaded, do the following.

## What to deploy

The page is four static files in `worldcup/web/` (no build step, vanilla
HTML/CSS/JS):

- `index.html`
- `app.js`
- `styles.css`
- `rankings.json`

There is also a single self-contained fallback at `worldcup/standalone.html`
(CSS, JS, and data all inlined into one file) if copying four files cross-repo
is awkward — drop that in as `/worldcup/index.html` and you're done.

## Steps

1. **Get the files.** Add/fetch `dkarlan/karlanwebsite2026` (branch
   `claude/world-cup-happiness-index-721lp6`) into your session, or pull the four
   files from `worldcup/web/`. If cross-repo access isn't possible, use
   `worldcup/standalone.html` instead (single file, see above).

2. **Create the page folder.** In the live site, make a `worldcup/` folder at
   the web root and copy the four files into it, keeping their names. (Or, with
   the standalone fallback: save `standalone.html` as `worldcup/index.html`.)

3. **Check asset paths.** `index.html` links `styles.css`, `app.js`, and fetches
   `rankings.json` with **relative** paths, so they resolve correctly when all
   four sit together in `/worldcup/`. No change needed unless the site rewrites
   asset URLs.

4. **Add the nav link.** In the site's main navigation, add an item **right next
   to the "OCE@USAID Museum" item**:

   ```html
   <li><a href="/worldcup/">Utilitarian World Cup Guide</a></li>
   ```

   (The page's own copy of the nav already mirrors deankarlan.com, so the link
   target is `/worldcup/`.)

5. **Routing / SPA fallback.** If the site uses a single-page fallback (Azure
   Static Web Apps `staticwebapp.config.json`, or a catch-all rewrite), make sure
   `/worldcup/*` is served as real static files and not rewritten to the SPA
   shell. Example exclusion for `staticwebapp.config.json`:

   ```json
   {
     "navigationFallback": {
       "rewrite": "/index.html",
       "exclude": ["/worldcup/*"]
     }
   }
   ```

6. **Commit and push to `master`** so Azure redeploys.

7. **Verify** that https://www.deankarlan.com/worldcup/ loads: a 48-bar chart,
   the two view toggles ("Performance, relative to expectations" /
   "Performance, absolute") and the Live / Pre-tournament toggle, the compare
   table, the essay, and the Future Matches list.

## Optional: live auto-update

The page works fully without this. To auto-refresh scores during the
tournament, wire up the scheduled GitHub Action in
`worldcup/deploy/worldcup-live-update.yml` (runs every 10 minutes on match
days), which needs a `FOOTBALL_DATA_TOKEN` repo secret from football-data.org.
Get the page live first; add this later.
