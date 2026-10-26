/* ===== UKREiiF Content Streams – page loader =====
   Event Maker only holds a placeholder:
     <div id="uks-page" data-page="content-streams"></div>
     <script src="https://deividuska.github.io/ukreiif-streams/loader.js"></script>
   This fetches pages/<data-page>.html from this repo, puts it into the placeholder,
   then loads uks.css and uks.js (HubSpot forms etc.). */

(function () {
  // Bump this whenever uks.css changes, so browsers fetch the new file instead of a cached one
  var CSS_VERSION = '1.4.0';

  var root = document.getElementById('uks-page');
  if (!root) return;

  // Load everything from wherever this script lives (GitHub Pages, or a local copy when testing)
  var base = document.currentScript.src.replace(/loader\.js.*$/, '');

  var css = document.createElement('link');
  css.rel = 'stylesheet';
  css.href = base + 'uks.css?v=' + CSS_VERSION;
  document.head.appendChild(css);

  // no-cache: the browser re-checks GitHub each visit, so a push shows up as soon as Pages republishes
  fetch(base + 'pages/' + root.getAttribute('data-page') + '.html', { cache: 'no-cache' })
    .then(function (res) {
      if (!res.ok) throw new Error(res.status);
      return res.text();
    })
    .then(function (html) {
      root.innerHTML = html;
      var js = document.createElement('script');
      js.src = base + 'uks.js?v=' + CSS_VERSION;
      document.body.appendChild(js);
    })
    .catch(function (err) {
      console.error('UKREiiF Streams: could not load page', err);
    });
})();
