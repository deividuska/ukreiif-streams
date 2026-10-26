/* ===== UKREiiF Content Streams – shared scripts for all stream pages =====
   Loaded by loader.js after the page HTML is in place. */

(function () {
  // HubSpot forms – only on pages that have <div class="hs-form-frame" data-form-id="…">.
  // The embed script finds those divs itself when it loads, so it just needs adding once.
  if (document.querySelector('.uks .hs-form-frame') && !document.getElementById('uks-hs-embed')) {
    var hs = document.createElement('script');
    hs.id = 'uks-hs-embed';
    hs.src = 'https://js.hsforms.net/forms/embed/20215586.js';
    hs.defer = true;
    document.body.appendChild(hs);
  }
})();
