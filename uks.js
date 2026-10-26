/* ===== UKREiiF Content Streams – shared scripts for all stream pages =====
   Loaded by loader.js after the page HTML is in place. */

(function () {
  // Programme day tabs: each group works independently, with keyboard navigation.
  document.querySelectorAll('.uks-tabs').forEach(function (group) {
    var tabs = Array.prototype.slice.call(group.querySelectorAll('.uks-tab'));
    var panels = group.querySelectorAll('.uks-tab-panel');

    var select = function (selected, focus) {
      tabs.forEach(function (tab) {
        var active = tab === selected;
        tab.setAttribute('aria-selected', active ? 'true' : 'false');
        tab.tabIndex = active ? 0 : -1;
      });
      panels.forEach(function (panel) {
        panel.hidden = panel.id !== selected.getAttribute('aria-controls');
      });
      if (focus) selected.focus();
    };

    tabs.forEach(function (tab, index) {
      tab.addEventListener('click', function () { select(tab, false); });
      tab.addEventListener('keydown', function (event) {
        var next;
        if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
        else if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
        else if (event.key === 'Home') next = 0;
        else if (event.key === 'End') next = tabs.length - 1;
        else return;
        event.preventDefault();
        select(tabs[next], true);
      });
    });
  });

  // Attending organisations: sort logos A-Z by alt text (or file name), ignoring a leading "The"
  document.querySelectorAll('.uks-orgs').forEach(function (gallery) {
    var key = function (fig) {
      var img = fig.querySelector('img');
      if (!img) return '';
      var label = (img.getAttribute('alt') || '').trim();
      if (!label) {
        label = (img.getAttribute('src') || '')
          .split('/').pop()
          .replace(/\.(png|jpe?g|webp|svg)$/i, '')
          .replace(/_[0-9a-f-]{36}$/i, '') // Event Maker's _<uuid> suffix
          .replace(/[-_]+/g, ' ');
      }
      return label.toLowerCase().replace(/^(the|a|an)\s+/, '').trim();
    };

    Array.prototype.slice.call(gallery.children)
      .sort(function (a, b) { return key(a).localeCompare(key(b), 'en'); })
      .forEach(function (fig) { gallery.appendChild(fig); });
  });

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
