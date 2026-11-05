"""Sync the "Who's in the room" logos from ukreiif.com (WordPress) into pages/.

WordPress is the source: each stream page's attending organisations logos are replaced
with the ones on its WordPress page, and the script prints what was added or removed.
Run from anywhere:

    python sync/sync_wordpress.py              # update pages/ and print a summary
    python sync/sync_wordpress.py --dry-run    # only print what would change
"""
import argparse
import difflib
import html
import os
import re
import sys
import time
import urllib.error
import urllib.request

from bs4 import BeautifulSoup

WP = 'https://www.ukreiif.com'

# Which WordPress page feeds which of our pages
STREAMS = [
    {'name': 'High Streets', 'wp': '/high-streets-urban-centres-day/', 'page': 'high-streets'},
    {'name': 'Investment', 'wp': '/investment-trends-insights-day/', 'page': 'investment-trends'},
    {'name': 'Transport', 'wp': '/transport-infrastructure-stage/', 'page': 'transport'},
    {'name': 'Sports', 'wp': '/sports-investment-regeneration-summit/', 'page': 'sports'},
    {'name': 'Heritage', 'wp': '/heritage-culture-creative-industries-regeneration-day/', 'page': 'heritage'},
    {'name': 'Healthcare', 'wp': '/healthcare-day/', 'page': 'healthcare'},
    {'name': 'Education', 'wp': '/education-place-day/', 'page': 'education'},
]

PAGES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pages')


class Stop(Exception):
    """Something looks wrong: change nothing and fail the run."""


# ---------- helpers ----------

def fetch(url):
    # The query string skips the site's page cache, so we always see the latest version
    req = urllib.request.Request(f'{url}?sync={int(time.time())}',
                                 headers={'User-Agent': 'ukreiif-streams-sync'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        by = 'Cloudflare' if 'cloudflare' in (e.headers.get('Server') or '').lower() else e.headers.get('Server') or 'the site'
        raise Stop(f'{url} answered {e.code} ({e.reason}), blocked by {by}'
                   + (f', ray id {e.headers["cf-ray"]}' if e.headers.get('cf-ray') else ''))
    except urllib.error.URLError as e:
        raise Stop(f'{url} could not be reached: {e.reason}')


def text(s):
    """Decoded text with single spaces."""
    return ' '.join(html.unescape(s).split())


def esc(s):
    """Text to HTML the way our pages write it: escaped, non-ASCII as entities."""
    return html.escape(s).encode('ascii', 'xmlcharrefreplace').decode()


def name_key(s):
    """Names for comparing: ignores case, spacing, punctuation and a leading 'The'."""
    s = re.sub(r'^the\s+', '', text(s).lower().replace('&', 'and'))
    return re.sub(r'[^a-z0-9]', '', s)


def img_key(url):
    """Same picture on both sites: file name without folder, size, extension or Event Maker id."""
    f = url.rsplit('/', 1)[-1].lower()
    f = re.sub(r'_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '', f)
    while re.search(r'\.(png|jpe?g|webp|svg|gif)$', f):
        f = re.sub(r'\.(png|jpe?g|webp|svg|gif)$', '', f)
    f = re.sub(r'-\d+x\d+$', '', f)
    return re.sub(r'[^a-z0-9]', '', f)


def logo_name(url):
    """A readable name for a logo that has no alt text on WordPress."""
    f = re.sub(r'(?i)\.(png|jpe?g|webp|svg|gif)$', '', url.rsplit('/', 1)[-1])
    f = re.sub(r'-\d+x\d+$', '', f)
    return ' '.join(re.split(r'[-_]+', f)).strip()


# ---------- read WordPress ----------

def read_wp_logos(url):
    soup = BeautifulSoup(fetch(url), 'html.parser')
    section = next((s for s in soup.select('.wp-block-group.hcc-section')
                    if ' '.join(s.get_text(' ').split()).lower().startswith('who')), None)
    if not section:
        raise Stop(f"{url} no longer shows a \"Who's in the room\" section")
    out = []
    # One logo per figure. Lazy loading adds a copy in <noscript> and a blank placeholder
    # pointing at data-src, so one picture shows up as several <img> tags.
    for fig in section.select('figure.wp-block-image'):
        img = next((i for i in fig.find_all('img')
                    if (i.get('data-src') or i.get('src', '')).startswith('http')), None)
        if not img:
            continue
        src = img.get('data-src') or img['src']
        out.append({'src': src, 'alt': text(img.get('alt') or '') or logo_name(src)})
    if len(out) < 10:
        raise Stop(f'{url} shows only {len(out)} logos, expected many more')
    return out


# ---------- read and write our pages ----------

ITEM = r' {8}<figure class="uks-org"><img [^\n]*</figure>'


def render(w):
    return f'        <figure class="uks-org"><img src="{esc(w["src"])}" alt="{esc(w["alt"])}"></figure>'


# Words that don't tell organisations apart, so "Chelsea FC" matches "Chelsea Football Club"
FILLER = {'the', 'of', 'and', 'fc', 'afc', 'football', 'club', 'group', 'ltd', 'limited', 'plc',
          'nhs', 'trust', 'foundation', 'logo', 'final', 'vector', 'png', 'jpg', 'uk', 'london',
          'management', 'investment', 'investments', 'managers', 'capital', 'partners', 'hotels'}


def core(s):
    """Name (or file name) without filler words: 'Chelsea Football Club' -> 'chelsea'."""
    ws = re.findall(r'[a-z0-9]+', text(s).lower().replace('&', ' and ').replace('’', '').replace("'", ''))
    return ''.join(w for w in ws if w not in FILLER)


def same_logo(o, w, level):
    """Does our logo o show the same organisation as WordPress logo w? Stricter levels go first."""
    ours = {name_key(o['alt']), img_key(o['src'])} - {''}
    theirs = {name_key(w['alt']), img_key(w['src'])} - {''}
    if level == 0:
        return bool(ours & theirs)
    ours = {core(o['alt']), core(img_key(o['src']))} - {''}
    theirs = {core(w['alt']), core(img_key(w['src']))} - {''}
    if level == 1:
        return bool(ours & theirs)
    if level == 2:  # one name inside the other, e.g. "Canterbury" / "Canterbury Cathedral"
        return any(len(a) >= 4 and len(b) >= 4 and (a in b or b in a) for a in ours for b in theirs)
    # typos, e.g. "historic royal places" / "Historic Royal Palaces"
    return any(difflib.SequenceMatcher(None, a, b).ratio() >= 0.85 for a in ours for b in theirs)


def merge_logos(ours, theirs):
    """WordPress decides which logos show. A logo we already have keeps our name, so WordPress
    alt text only matters for new logos."""
    match = {}  # WordPress index -> our logo
    for level in range(4):
        for i, w in enumerate(theirs):
            if i in match:
                continue
            o = next((o for o in ours if id(o) not in {id(m) for m in match.values()}
                      and same_logo(o, w, level)), None)
            if o:
                match[i] = o
    out, notes, switched = [], [], 0
    for i, w in enumerate(theirs):
        o = match.get(i)
        if o:
            switched += o['src'] != w['src']
            out.append(render({'src': w['src'], 'alt': o['alt']}))
        else:
            notes.append(f'added **{w["alt"]}**')
            out.append(render(w))
    matched = {id(m) for m in match.values()}
    notes += [f'removed **{o["alt"]}**' for o in ours if id(o) not in matched]
    if notes and len(ours) != len(theirs):
        notes.append(f'{len(ours)} -> {len(theirs)} logos')
    if switched:
        notes.append(f'{switched} logos switch to the WordPress copy of the same image (names kept)')
    return out, notes


def sync_logos(page, stream, logos):
    m = re.search(r'<div class="uks-orgs">\n(.*?)\n {6}</div>', page, re.S)
    if not m:
        raise Stop(f'pages/{stream["page"]}.html has no attending organisations block')
    region = m.group(1)
    items = re.findall(ITEM, region)
    if '\n'.join(items) != region:
        raise Stop(f'pages/{stream["page"]}.html: logo layout not recognised, so it was left alone')
    ours = [{'src': html.unescape(re.search(r'src="([^"]*)"', i).group(1)),
             'alt': text(re.search(r'alt="([^"]*)"', i).group(1))} for i in items]
    new, notes = merge_logos(ours, logos)
    return page[:m.start(1)] + '\n'.join(new) + page[m.end(1):], notes


# ---------- run ----------

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--dry-run', action='store_true', help='show changes without writing files')
    args = ap.parse_args()
    sys.stdout.reconfigure(errors='replace')  # Windows consoles can't show every character
    sys.stderr.reconfigure(errors='replace')

    def path(name):
        return os.path.join(PAGES, name + '.html')

    # Work with \n line endings and put each file's own style back when writing
    files, crlf, report = {}, {}, {}
    try:
        for st in STREAMS:
            if not os.path.exists(path(st['page'])):
                raise Stop(f'pages/{st["page"]}.html is missing (listed in STREAMS as {st["name"]})')
            with open(path(st['page']), encoding='utf-8', newline='') as f:
                raw = f.read()
            crlf[st['page']] = '\r\n' in raw
            original = raw.replace('\r\n', '\n')
            new, notes = sync_logos(original, st, read_wp_logos(WP + st['wp']))
            if new != original:
                files[st['page']] = new
            report[st['name']] = notes
    except Stop as e:
        print(f'STOPPED, nothing was changed: {e}', file=sys.stderr)
        sys.exit(1)

    lines = ['## Changes from WordPress', '']
    for section, notes in report.items():
        if notes:
            lines += [f'### {section}'] + [f'- {html.unescape(n)}' for n in notes] + ['']
    if files:
        lines += ['Files: ' + ', '.join(f'`pages/{n}.html`' for n in files)]
    else:
        lines = ['No changes: our logos match WordPress.']
    print('\n'.join(lines))

    if not args.dry_run:
        for name, page in files.items():
            with open(path(name), 'w', encoding='utf-8', newline='') as f:
                f.write(page.replace('\n', '\r\n') if crlf[name] else page)


if __name__ == '__main__':
    main()
