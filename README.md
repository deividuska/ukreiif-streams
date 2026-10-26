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
