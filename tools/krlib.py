"""Shared helpers for the Kid Radd translation tools.

The comic pages are hand-written 2002-era HTML (tables, <font>, unclosed tags),
so instead of a DOM parser we tokenize the raw source and work with byte-exact
offsets. That way the build step can splice translations into the original
markup without re-serializing (and subtly changing) anything else.
"""
import html
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'kidradd')
TRANSLATION = os.path.join(ROOT, 'translation')
PO_DIR = os.path.join(TRANSLATION, 'po')
NOTES_DIR = os.path.join(TRANSLATION, 'notes')
OVERLAY = os.path.join(TRANSLATION, 'overlay')
OUT = os.path.join(ROOT, 'ru')

# Pages are Latin-1-ish with no charset declared; cp1252 is what browsers
# assume and is a superset of the Latin-1 printable range.
SRC_ENCODING = 'cp1252'

# Strings repeated on every page; translated once in ui.po.
UI_STRINGS = {'zoom', 'list', 'Tip: Use the Left/Right arrow keys to navigate.'}
UI_PATTERN = re.compile(r'^Kid Radd &copy;\d{4} by Dan Miller$')

BLOCK_TAGS = {
    'html', 'head', 'body', 'title', 'table', 'tbody', 'thead', 'tr', 'td', 'th',
    'center', 'p', 'div', 'hr', 'frameset', 'frame', 'embed', 'audio', 'source',
    'bgsound', 'map', 'area', 'object', 'param', 'meta', 'link', 'style', 'script',
    'noscript', 'form', 'input', 'textarea',
}
VOID_TAGS = {'br', 'img', 'image', 'wbr', 'hr', 'meta', 'link', 'source',
             'embed', 'area', 'param', 'input', 'frame', 'bgsound'}
LETTERS = re.compile(r'[A-Za-z]')

TOKEN_RE = re.compile(
    r'(?P<comment><!--.*?-->)'
    r'|(?P<raw><(?P<rawname>script|style|title)\b[^>]*>.*?</(?P=rawname)\s*>)'
    r'|(?P<tag></?[A-Za-z][^>]*>)'
    r'|(?P<text>[^<]+|<)',
    re.S | re.I)


class Tok:
    __slots__ = ('kind', 'name', 'start', 'end', 'src')

    def __init__(self, kind, name, start, end, src):
        self.kind, self.name, self.start, self.end, self.src = kind, name, start, end, src

    def __repr__(self):
        return f'Tok({self.kind},{self.name},{self.src[:30]!r})'


def tokenize(s):
    out = []
    for m in TOKEN_RE.finditer(s):
        a, b = m.span()
        if m.group('comment'):
            out.append(Tok('comment', None, a, b, m.group()))
        elif m.group('raw'):
            out.append(Tok('raw', m.group('rawname').lower(), a, b, m.group()))
        elif m.group('tag'):
            t = m.group()
            name = re.match(r'</?([A-Za-z0-9]+)', t).group(1).lower()
            if t.startswith('</'):
                kind = 'close'
            elif name in VOID_TAGS or t.endswith('/>'):
                kind = 'void'
            else:
                kind = 'open'
            out.append(Tok(kind, name, a, b, t))
        else:
            out.append(Tok('text', None, a, b, m.group()))
    return out


def is_boundary(t):
    if t.kind in ('comment', 'raw'):
        return True
    if t.kind in ('open', 'close', 'void') and t.name in BLOCK_TAGS:
        return True
    # Panel anchors (<a name="p3">) separate panels; links (<a href>) stay inline.
    if t.kind == 'open' and t.name == 'a' and re.search(r'\bname\s*=', t.src, re.I):
        return True
    return False


EDGE_WS = re.compile(r'^(?:\s|&nbsp;)+|(?:\s|&nbsp;)+$')


def _matching_close(toks, i):
    """Index of the close tag matching open tag toks[i] within toks, or None."""
    depth = 0
    for j in range(i, len(toks)):
        t = toks[j]
        if t.name != toks[i].name:
            continue
        if t.kind == 'open':
            depth += 1
        elif t.kind == 'close':
            depth -= 1
            if depth == 0:
                return j
    return None


def _trim(toks):
    """Strip wrapper markup from both ends of a run, keeping inner inline tags.

    Returns (tokens, start_offset, end_offset) or None when nothing is left.
    """
    toks = list(toks)
    changed = True
    while changed and toks:
        changed = False
        first, last = toks[0], toks[-1]
        if first.kind == 'text' and not EDGE_WS.sub('', first.src):
            toks.pop(0); changed = True; continue
        if last.kind == 'text' and not EDGE_WS.sub('', last.src):
            toks.pop(); changed = True; continue
        if first.kind in ('void', 'close'):
            toks.pop(0); changed = True; continue
        if last.kind in ('void', 'open'):
            toks.pop(); changed = True; continue
        if first.kind == 'open':
            j = _matching_close(toks, 0)
            if j is None:
                toks.pop(0); changed = True; continue
            if j == len(toks) - 1:
                toks.pop(); toks.pop(0); changed = True; continue
        if last.kind == 'close':
            opened = any(t.kind == 'open' and t.name == last.name for t in toks[:-1])
            if not opened:
                toks.pop(); changed = True; continue
    if not toks:
        return None
    start, end = toks[0].start, toks[-1].end
    # Trim whitespace/&nbsp; inside the edge text tokens too.
    if toks[0].kind == 'text':
        m = re.match(r'(?:\s|&nbsp;)*', toks[0].src)
        start += m.end()
    if toks[-1].kind == 'text':
        m = re.search(r'(?:\s|&nbsp;)*$', toks[-1].src)
        end -= len(toks[-1].src) - m.start()
    return toks, start, end


def normalize(s):
    return re.sub(r'\s+', ' ', s).strip()


def plain_text(s):
    return html.unescape(re.sub(r'<[^>]*>', '', s))


class Unit:
    """One translatable piece of text in a page."""
    __slots__ = ('page', 'panel', 'index', 'start', 'end', 'msgid', 'slot', 'line')

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    @property
    def ctxt(self):
        return f'{self.page}#{self.panel}.{self.index}'


PANEL_RE = re.compile(r'<a\s+name\s*=\s*"?([A-Za-z0-9_]+)"?', re.I)
SLOT_RE = re.compile(r'<!--\s*(.*?)\s*(?://)?\s*-->', re.S)


def segment(s, page):
    """Split page source into translatable Units (plus UI units)."""
    toks = tokenize(s)
    units = []
    panel = 'start'
    counters = {}
    slot = ''
    run = []

    def flush():
        if not run:
            return
        r = _trim(run)
        run.clear()
        if not r:
            return
        _, a, b = r
        raw = s[a:b]
        if not LETTERS.search(plain_text(raw)):
            return
        n = counters.get(panel, 0) + 1
        counters[panel] = n
        units.append(Unit(page=page, panel=panel, index=n, start=a, end=b,
                          msgid=normalize(raw), slot=slot,
                          line=s.count('\n', 0, a) + 1))

    for t in toks:
        if t.kind == 'raw' and t.name == 'title':
            flush()
            m = re.match(r'<title[^>]*>(.*)</title\s*>', t.src, re.S | re.I)
            inner = m.group(1)
            a = t.start + m.start(1)
            units.append(Unit(page=page, panel='head', index=1, start=a,
                              end=a + len(inner), msgid=normalize(inner),
                              slot='title', line=s.count('\n', 0, a) + 1))
            continue
        if is_boundary(t):
            flush()
            if t.kind == 'open' and t.name == 'a':
                panel = PANEL_RE.match(t.src).group(1)
                slot = ''
            elif t.kind == 'comment':
                m = SLOT_RE.match(t.src)
                slot = normalize(m.group(1)) if m else ''
            continue
        run.append(t)
    flush()
    return units


def is_ui(unit):
    return unit.panel == 'head' or unit.msgid in UI_STRINGS or bool(UI_PATTERN.match(unit.msgid))


# --------------------------------------------------------------------------
# Pages and chapters

def comic_pages():
    """Comic page basenames (without .htm) in reading order."""
    names = []
    for f in os.listdir(SRC):
        m = re.match(r'comic(\d+)(a?)\.htm$', f)
        if m:
            names.append((int(m.group(1)), m.group(2), f[:-4]))
    return [n for _, _, n in sorted(names)]


def page_number(page):
    return int(re.match(r'comic(\d+)', page).group(1))


def chapters():
    """[(chapter_no, title, first_page_no)] parsed from listp.htm."""
    s = read_src('listp.htm')
    out = []
    for m in re.finditer(r'<b>([^<]*?)\s*\((\d+) of \d+\)</b>', s):
        title, no = m.group(1).strip(), int(m.group(2))
        link = re.search(r'href="comic(\d+)\.htm', s[m.end():])
        out.append((no, title, int(link.group(1))))
    return out


def chapter_of(page, chs=None):
    chs = chs or chapters()
    n = page_number(page)
    cur = chs[0][0]
    for no, _, first in chs:
        if n >= first:
            cur = no
    return cur


def read_src(name):
    with open(os.path.join(SRC, name), encoding=SRC_ENCODING, newline='') as f:
        return f.read()


def po_path_for_chapter(no):
    return os.path.join(PO_DIR, f'ch{no:02d}.po')


def panel_sprites(s):
    """{panel: [image basenames]} for character/scene hints in PO comments."""
    skip = {'raddlogo.gif', 'prev.gif', 'next.gif', 'spacer.gif', 'menu.gif'}
    out = {}
    parts = re.split(r'(<a\s+name\s*=\s*"?[A-Za-z0-9_]+"?)', s, flags=re.I)
    panel = 'start'
    for p in parts:
        m = PANEL_RE.match(p)
        if m:
            panel = m.group(1)
            continue
        imgs = re.findall(r'<img[^>]*\bsrc="([^"]+)"', p, re.I)
        out.setdefault(panel, [])
        for i in imgs:
            b = os.path.basename(i)
            if b not in skip and b not in out[panel]:
                out[panel].append(b)
    return out


# --------------------------------------------------------------------------
# GIF timing

def gif_timing(path):
    """Return dict(frames, delays_ms, loop) for a GIF, or None if unreadable.

    loop: None = no NETSCAPE block (plays once), 0 = forever, n = loop count.
    Delays follow browser behaviour: a delay of <= 10 ms is shown as 100 ms
    (Chrome and Firefox both do this).
    """
    try:
        with open(path, 'rb') as f:
            d = f.read()
    except OSError:
        return None
    if d[:3] != b'GIF':
        return None
    p = 13
    flags = d[10]
    if flags & 0x80:
        p += 3 * (2 << (flags & 7))
    delays, loop, pending = [], None, 0
    n = len(d)
    try:
        while p < n:
            b = d[p]
            if b == 0x3B:
                break
            if b == 0x21:
                label = d[p + 1]
                p += 2
                if label == 0xF9 and d[p] >= 4:
                    pending = int.from_bytes(d[p + 2:p + 4], 'little') * 10
                elif label == 0xFF and d[p] == 11 and d[p + 1:p + 12] in (b'NETSCAPE2.0', b'ANIMEXTS1.0'):
                    q = p + 12
                    if d[q] >= 3 and d[q + 1] == 1:
                        loop = int.from_bytes(d[q + 2:q + 4], 'little')
                while d[p]:
                    p += d[p] + 1
                p += 1
            elif b == 0x2C:
                lflags = d[p + 9]
                p += 10
                if lflags & 0x80:
                    p += 3 * (2 << (lflags & 7))
                p += 1  # LZW minimum code size
                while d[p]:
                    p += d[p] + 1
                p += 1
                delays.append(pending if pending > 10 else 100)
                pending = 0
            else:
                break
    except IndexError:
        pass  # truncated file: use what we have
    return {'frames': len(delays), 'delays': delays, 'loop': loop}


def play_once_ms(path):
    """Time until the final frame appears, for GIFs that stop animating.

    Returns None for single-frame or infinitely looping GIFs.
    """
    t = gif_timing(path)
    if not t or t['frames'] < 2 or t['loop'] == 0:
        return None
    one = sum(t['delays'])
    plays = 1 if t['loop'] is None else t['loop'] + 1  # finite NETSCAPE count
    return one * (plays - 1) + sum(t['delays'][:-1])
