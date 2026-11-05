# ukreiif-streams

Content Stream pages for the UKREiiF Event Maker site (2027.ukreiif.com): the Content Streams
holding page and one page per stream. Built the same way as `ukreiif-leaders-group`, but every
class and id uses the `uks-` prefix so the two can never clash.

| File | What it does |
|---|---|
| `loader.js` | Fetches `pages/<data-page>.html` into the Event Maker placeholder, then loads `uks.css` and `uks.js`. |
| `uks.css` | All styles. Scoped to `.uks` / `uks-`, plus the rule that removes Event Maker's container padding. |
| `uks.js` | Sorts the attending-organisation logos A-Z and loads the HubSpot form embed. |
| `pages/content-streams.html` | Content Streams holding page. |
| `pages/high-streets.html` | High Streets &amp; Urban Centres Day. |
| `pages/investment-trends.html` | Investment and Finance Trends &amp; Insights. |
| `pages/transport.html` | Transport &amp; Infrastructure Stage, with three programme day tabs. |
| `pages/sports.html` | Sports Investment &amp; Regeneration Summit, with Wednesday and Thursday programme tabs. |
| `pages/heritage.html` | Heritage, Culture &amp; Creative Industries Zone. |
| `pages/healthcare.html` | Healthcare Day, with Cinema Stage and Roundtable Room programme groups. |
| `pages/education.html` | Education &amp; Place Day. |

Served by GitHub Pages: `https://deividuska.github.io/ukreiif-streams/`

## Event Maker snippet

Paste once into the page's codeit block. `data-page` is the file name in `pages/` without `.html`.

```html
<div class='container uks-full {{ settings.spacing }}' data-section-id='{{ section.id }}' data-section-type='codeit'>
  <div id="uks-page" data-page="content-streams"></div>
  <script src="https://deividuska.github.io/ukreiif-streams/loader.js"></script>
</div>
```

Edit a page in `pages/`, commit and push: it's live within about a minute.
When `uks.css` or `uks.js` changes, bump `CSS_VERSION` in `loader.js`.

## HubSpot forms

Portal `20215586`. Each form is a `<div class="hs-form-frame" data-form-id="…">` in the page HTML;
`uks.js` adds HubSpot's embed script, which fills it in.

- Holding page: `5fbdab84-75e1-4c22-9e97-9cd38ced4888`
- Stream pages: `f184626f-2cbd-44d3-bed8-46748d654a4a`

The form renders inside an iframe, so field and button styling is set in HubSpot (form style settings), not in `uks.css`.

## Investment and Finance Trends & Insights page

Use this snippet in the new Event Maker page's codeit block:

```html
<div class='container uks-full {{ settings.spacing }}' data-section-id='{{ section.id }}' data-section-type='codeit'>
  <div id="uks-page" data-page="investment-trends"></div>
  <script src="https://deividuska.github.io/ukreiif-streams/loader.js"></script>
</div>
```

The page reuses the High Streets layout, shared CSS/JS and stream registration form.
Its title, date, six programme entries, nine previous voices, 63 attending organisations
and About copy follow the supplied Investment reference screenshot. The shared script
sorts attending organisations alphabetically.

Missing source assets currently use labelled placeholders: the Man session-partner logo,
all nine speaker portraits and all 63 organisation logos. The `bg` organisation label
is transcribed from its logo in the reference; confirm its full name when supplying assets.
The hero uses the existing Investment stream card's Event Maker image URL; the About
section reuses the existing High Streets Event Maker image.

## Sync logos from WordPress

`sync/sync_wordpress.py` reads the "Who's in the room" logos (`.wp-block-group.hcc-section`) on
each stream's ukreiif.com page and makes our attending organisations logos match. WordPress is
the source for which logos show: logos added only here are removed by the next sync, so add
them on WordPress. A logo we already have keeps our name (matched by name or image file, allowing
for small differences like "FC" / "Football Club"); only new logos take their WordPress alt text,
so give those a proper alt text when uploading. Nothing else on the pages is touched.

Run it on your PC from the repo folder:

```bash
python sync/sync_wordpress.py --dry-run
```

shows what would change without touching anything. Then

```bash
python sync/sync_wordpress.py
```

updates the files in `pages/`. Commit and push as usual to publish.

- **Which pages:** `STREAMS` at the top of the script.
- **Safety:** if a WordPress page fails to load, has no "Who's in the room" section or shows
  fewer than 10 logos, or our logo block isn't recognised, the script stops and changes nothing.
- **First time only:** `pip install -r sync/requirements.txt`
