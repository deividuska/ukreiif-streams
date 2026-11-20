"""Sync sponsors and "Who's in the room" logos from ukreiif.com (WordPress) into pages/.

WordPress is the source for two parts of each stream page:
- sponsors and partners next to the video (labels, logos, order)
- the attending organisations logos ("Who's in the room")
The script prints what was added, removed or changed.
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
import urllib.parse
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
    headers = {'User-Agent': 'ukreiif-streams-sync'}
    # On GitHub, a Cloudflare rule on ukreiif.com lets requests with this secret key through
    if os.environ.get('SYNC_KEY'):
        headers['X-Sync-Key'] = os.environ['SYNC_KEY']
    req = urllib.request.Request(f'{url}?sync={int(time.time())}', headers=headers)
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


def esc_url(u):
    """A link for our HTML: non-ASCII characters percent-encoded (as browsers send them)."""
    return esc(urllib.parse.quote(u, safe=":/?#[]@!$&'()*+,;=%~"))


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

def first_img(fig):
    """The real picture in a WordPress figure. Lazy loading adds a copy in <noscript> and a
    blank placeholder pointing at data-src, so one picture shows up as several <img> tags."""
    img = next((i for i in fig.find_all('img')
                if (i.get('data-src') or i.get('src', '')).startswith('http')), None)
    if img:
        src = img.get('data-src') or img['src']
        return {'src': src, 'alt': text(img.get('alt') or '') or logo_name(src)}


def read_wp_sponsors(soup, url):
    """Sponsor groups in page order: [{'label': 'Associate Partner', 'logos': [...]}, ...].
    Each group on WordPress is an .hcc-partners block with a label and a row of logos."""
    groups = []
    for row in soup.select('.hcc-partners__row'):
        box = row.find_parent(class_='hcc-partners')
        labels = [l for l in (box.select('.hcc-partners__label') if box else [])
                  if l.find_parent(class_='hcc-partners') is box and text(l.get_text(' '))]
        if len(labels) != 1:
            raise Stop(f'{url}: a sponsor logo row has {len(labels)} labels, expected 1')
        # One logo per item in the row (a centred image is wrapped in a div instead of a figure)
        logos = [x for x in map(first_img, row.find_all(['figure', 'div'], recursive=False)) if x]
        if not logos:
            raise Stop(f'{url}: the sponsor group "{text(labels[0].get_text(" "))}" has no logos')
        groups.append({'label': text(labels[0].get_text(' ')), 'logos': logos})
    if not groups:
        raise Stop(f'{url} no longer shows any sponsors')
    return groups


def read_wp_logos(soup, url):
    section = next((s for s in soup.select('.wp-block-group.hcc-section')
                    if ' '.join(s.get_text(' ').split()).lower().startswith('who')), None)
    if not section:
        raise Stop(f"{url} no longer shows a \"Who's in the room\" section")
    out = [x for x in map(first_img, section.select('figure.wp-block-image')) if x]
    if len(out) < 10:
        raise Stop(f'{url} shows only {len(out)} logos, expected many more')
    return out


# ---------- read and write our pages ----------

ITEM = r' {8}<figure class="uks-org"><img [^\n]*</figure>'


def render(w):
    return f'        <figure class="uks-org"><img src="{esc_url(w["src"])}" alt="{esc(w["alt"])}"></figure>'


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


def match_logos(ours, theirs):
    """WordPress index -> our logo showing the same organisation. Stricter matches go first."""
    match = {}
    for level in range(4):
        for i, w in enumerate(theirs):
            if i in match:
                continue
            o = next((o for o in ours if id(o) not in {id(m) for m in match.values()}
                      and same_logo(o, w, level)), None)
            if o:
                match[i] = o
    return match


def merge_logos(ours, theirs):
    """WordPress decides which logos show. A logo we already have keeps our name, so WordPress
    alt text only matters for new logos."""
    match = match_logos(ours, theirs)
    out, notes, switched = [], [], 0
    for i, w in enumerate(theirs):
        o = match.get(i)
        if o:
            switched += esc_url(o['src']) != esc_url(w['src'])
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


# ---------- sponsors ----------

# Our sponsor block: the <div class="uks-sponsors ..."> that closes just before the hero text column
SPONSORS = re.compile(r'( {8})<div class="(uks-sponsors[^"]*)">\n.*?\n {8}</div>(?=\n {6}</div>)', re.S)


def read_our_sponsors(block):
    """Our sponsor logos as {'label', 'src', 'alt', 'cls'} in page order."""
    soup = BeautifulSoup(block, 'html.parser')
    out, label = [], None
    for el in soup.find_all(['p', 'div']):
        cls = el.get('class') or []
        if el.name == 'p' and 'uks-sponsor-heading' in cls:
            label = text(el.get_text())
        elif el.name == 'div' and 'uks-sponsor' in cls:
            eyebrow = el.find('p', class_='uks-eyebrow')
            img = el.find('img')
            if not img or not (eyebrow or label):
                raise Stop('a sponsor without a logo or label')
            out.append({'label': text(eyebrow.get_text()) if eyebrow else label,
                        'src': html.unescape(img['src']), 'alt': text(img.get('alt') or ''),
                        'cls': ' '.join(img.get('class') or [])})
    return out


def render_sponsors(classes, groups):
    """Our sponsor block. One logo under a label shows label and logo together; several logos
    under one label get one heading above them, which needs the grouped grid layout."""
    classes = [c for c in classes if c != 'uks-sponsors-headline-pair']
    grouped = 'uks-sponsors-grouped' in classes
    if any(len(g['logos']) > 1 for g in groups) and not grouped:
        classes += [c for c in ('uks-sponsors-grid', 'uks-sponsors-grouped') if c not in classes]
        grouped = True

    def headline(g):
        return grouped and len(g['logos']) == 1 and 'headline' in g['label'].lower()

    if sum(map(headline, groups)) == 2:
        classes.append('uks-sponsors-headline-pair')  # two headline partners share the top row

    def img(x):
        c = f'class="{x["cls"]}" ' if x.get('cls') else ''
        return f'<img {c}src="{esc_url(x["src"])}" alt="{esc(x["alt"])}">'

    lines = [f'        <div class="{" ".join(classes)}">']
    for g in groups:
        label = esc(g['label'].upper())
        if len(g['logos']) == 1:
            lines += [f'          <div class="uks-sponsor{" uks-sponsor-headline" if headline(g) else ""}">',
                      f'            <p class="uks-eyebrow">{label}</p>',
                      f'            {img(g["logos"][0])}',
                      '          </div>']
        else:
            lines.append(f'          <p class="uks-eyebrow uks-sponsor-heading">{label}</p>')
            for x in g['logos']:
                lines += ['          <div class="uks-sponsor">', f'            {img(x)}', '          </div>']
    lines.append('        </div>')
    return '\n'.join(lines)


def sync_sponsors(page, stream, wp_groups):
    found = list(SPONSORS.finditer(page))
    if len(found) != 1:
        raise Stop(f'pages/{stream["page"]}.html: sponsor block not recognised, so it was left alone')
    m = found[0]
    ours = read_our_sponsors(m.group(0))
    theirs = [w for g in wp_groups for w in g['logos']]
    match = match_logos(ours, theirs)
    notes, groups, switched, i = [], [], 0, 0
    for g in wp_groups:
        logos = []
        for w in g['logos']:
            o = match.get(i)
            if o:
                # Same organisation: keep our name and size class, take the WordPress picture
                switched += esc_url(o['src']) != esc_url(w['src'])
                if o['label'].upper() != g['label'].upper():
                    notes.append(f'sponsor **{o["alt"]}**: label {o["label"].upper()} -> {g["label"].upper()}')
                logos.append({'src': w['src'], 'alt': o['alt'], 'cls': o['cls']})
            else:
                notes.append(f'sponsor added: **{w["alt"]}** ({g["label"].upper()})')
                logos.append(w)
            i += 1
        groups.append({'label': g['label'], 'logos': logos})
    matched = {id(o) for o in match.values()}
    notes += [f'sponsor removed: **{o["alt"]}**' for o in ours if id(o) not in matched]
    order = [id(match[k]) for k in sorted(match)]
    if order != [id(o) for o in ours if id(o) in matched]:
        notes.append('sponsor order changed')
    if switched:
        notes.append(f'{switched} sponsor logos switch to the WordPress copy of the same image (names kept)')
    new = render_sponsors(m.group(2).split(), groups)
    return page[:m.start()] + new + page[m.end():], notes


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
            url = WP + st['wp']
            soup = BeautifulSoup(fetch(url), 'html.parser')
            new, sponsor_notes = sync_sponsors(original, st, read_wp_sponsors(soup, url))
            new, notes = sync_logos(new, st, read_wp_logos(soup, url))
            notes = sponsor_notes + notes
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
        lines = ['No changes: our sponsors and logos match WordPress.']
    print('\n'.join(lines))

    if not args.dry_run:
        for name, page in files.items():
            with open(path(name), 'w', encoding='utf-8', newline='') as f:
                f.write(page.replace('\n', '\r\n') if crlf[name] else page)


if __name__ == '__main__':
    main()
