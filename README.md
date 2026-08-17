# Chamber Events Harvester

Scrapes events from a list of chamber-of-commerce / business-association
websites and publishes them as a single subscribable calendar feed
(`docs/events.ics`), so anyone can add the whole set of events to Google
Calendar, Apple Calendar, or Outlook once and have it stay up to date
automatically, with no per-event prompts.

Sites currently configured (see `config/sites.yaml`):

| Site | Status |
|---|---|
| Glendora Chamber of Commerce | ✅ working |
| Monrovia Chamber of Commerce | ✅ working |
| Ontario Chamber of Commerce (ChamberMaster) | ✅ working |
| American Business Association - Inland Empire (ABAIE) | ✅ working |
| Inland Empire Chamber of Commerce | ✅ working (partial — see note below) |
| Irwindale Chamber of Commerce | ❌ not yet — see note below |
| American Business Association - Los Angeles (ABALA) | ❌ not yet — see note below |

## How it works

1. `python -m harvester.main` fetches each site in `config/sites.yaml`.
2. For every site it first looks for [schema.org `Event`
   JSON-LD](https://schema.org/Event) markup, which is what most modern
   event-calendar platforms (WordPress "The Events Calendar", GrowthZone /
   ChamberMaster, etc.) embed for SEO / Google rich results. This needs no
   per-site tuning and keeps working even if a site's page layout changes.
3. If a site has no JSON-LD, it falls back to a configurable CSS-selector
   scraper (`parser: css` + a `css:` block in `sites.yaml` — see comments
   in that file), or a site-specific parser under `harvester/parsers/` for
   platforms whose markup needs more than selectors (GrowthZone/ChamberMaster
   detail-page fetches, ABAIE's ASP.NET repeater, embedded `data:text/calendar`
   links).
4. For sites whose event data only exists after JavaScript runs (SPAs, JS-
   injected widgets), `harvester/fetchers.fetch_rendered_html()` renders the
   page with headless Chromium via Playwright first. Enable it per-site with
   `render: true` in `sites.yaml` (not currently used by any site — see the
   limitations section).
5. All harvested events are merged, given a stable UID (hash of
   site+title+start time, so re-runs update existing calendar entries
   instead of duplicating them), and written out as one iCalendar file:
   `docs/events.ics`.
6. A GitHub Actions workflow (`.github/workflows/harvest.yml`) runs this
   automatically every night at ~2:00 AM Pacific and commits the refreshed
   `docs/events.ics` back to the repo. It can also be triggered manually
   from the Actions tab ("Run workflow").

If a site returns zero events, the run still succeeds (other sites keep
working) and logs diagnostics to help add the right CSS selectors.

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m harvester.main
# output: docs/events.ics
```

## One-time setup: publish the feed

The feed needs to live at a stable public URL for calendar apps to
subscribe to.

1. In the GitHub repo: **Settings &rarr; Pages &rarr; Source: Deploy from a
   branch**, then pick the branch and folder Pages should serve.
2. Depending on which folder you pick, the feed URL is either:
   - Branch + `/` (root): `https://onevector.github.io/Claude/docs/events.ics`
   - Branch + `/docs`: `https://onevector.github.io/Claude/events.ics`

   This repo is currently configured for **root**, so the live URL is:
   **`https://onevector.github.io/Claude/docs/events.ics`**

## Subscribing (one-time per calendar app, then fully automatic)

### Google Calendar
1. Go to [calendar.google.com](https://calendar.google.com)
2. Left sidebar &rarr; **Other calendars** &rarr; **+** &rarr; **From URL**
3. Paste the `events.ics` URL from the step above
4. Click **Add calendar**

Google then polls the feed on its own schedule (typically within 24 hours,
often sooner) and silently adds/updates events — no prompts.

### Apple Calendar (Mac)
File &rarr; New Calendar Subscription&hellip; &rarr; paste the URL &rarr;
set Auto-refresh to "Every day".

### Outlook
Add calendar &rarr; Subscribe from web &rarr; paste the URL.

## Notes / limitations

- **Refresh timing**: our workflow regenerates `events.ics` every night at
  ~2:00 AM Pacific, but each calendar app decides *its own* poll interval
  for subscribed feeds (Google in particular does not let you force an
  exact time) — the guarantee is that fresh data is available by 2 AM, not
  that every app pulls it at exactly 2 AM.
- **DST**: GitHub Actions cron is UTC-only, so the 2 AM Pacific schedule
  drifts to 1 AM during Pacific Standard Time. Not adjusted for; a nightly
  refresh doesn't need to be precise to the hour.
- **Irwindale Chamber**: not currently returning events. Its calendar is a
  FullCalendar.js widget (chamberorganizer.com-powered); rendering it with
  Playwright shows zero event chips in the default month-grid view. Either
  there are genuinely no near-term events, or a list/agenda view needs to
  be triggered that hasn't been found yet.
- **ABALA**: not currently returning events. Confirmed to be a Wix SPA;
  even after full Playwright rendering (JS executed, page fully loaded)
  no event markup appears in the DOM, while the string `wix-events` does
  appear in the page's script bundles - this points to the widget living
  in a Shadow DOM / Custom Element, which `page.content()` can't see.
  Reaching it would need shadow-DOM-piercing extraction (e.g.
  `page.evaluate()` walking shadow roots from the browser side), not just
  JS rendering.
- **Inland Empire Chamber**: only exposes one "next event" via an embedded
  ICS link. Their actual events platform is Glue Up
  (`https://iercc.glueup.com/organization/813/events/`), but as of
  investigation it lists the same single event — no extra coverage gained
  by adding it as a second source right now. Worth re-checking later.
- **Adding more sites**: add an entry to `config/sites.yaml`. Try
  `parser: jsonld` first; if the harvester logs "No events found" for it,
  inspect the page for an events list and add a `css:` selector block
  (`parser: css`, see the comment at the top of `sites.yaml`).
