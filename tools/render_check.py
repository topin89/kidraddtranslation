#!/usr/bin/env python3
"""Find panels where the Russian text no longer fits.

Renders each page in English (kidradd/) and Russian (ru/) with headless
Chromium and compares the size of every panel's 256x224 comic area. Tables
stretch to fit their content, so a Russian panel that grew means a bubble
overflowed. Screenshots of flagged panels (English + Russian) are saved to
ru/_render_check/.

    python tools/build.py && python tools/render_check.py            # pages with any translation
    python tools/render_check.py comic1 comic2                       # specific pages
    python tools/render_check.py --all

Needs: pip install playwright. Uses $CHROMIUM (path to a Chromium binary) if
set, else Playwright's own browser ("python -m playwright install chromium").
"""
import argparse
import os
import sys

import polib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import krlib as K

MEASURE = '''() => {
  const out = {};
  document.querySelectorAll('a.panel').forEach(a => {
    const td = a.querySelector('td[width="256"][height="224"]');
    if (!td || out[a.name]) return;
    const outer = td.closest('table').getBoundingClientRect();
    out[a.name] = [Math.round(outer.width), Math.round(outer.height)];
  });
  return out;
}'''


def translated_pages():
    pages = set()
    for f in os.listdir(K.PO_DIR):
        if f.endswith('.po') and f != 'ui.po':
            for e in polib.pofile(os.path.join(K.PO_DIR, f)):
                if e.msgstr and not e.obsolete:
                    pages.add(e.msgctxt.split('#')[0])
    return [p for p in K.comic_pages() if p in pages]


def url(root, page, hash_=''):
    return 'file://' + os.path.join(root, page + '.htm') + (('#' + hash_) if hash_ else '')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pages', nargs='*')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--tolerance', type=int, default=1, help='pixels of growth to ignore')
    ap.add_argument('--out', help='built Russian site to check (default: ru/)')
    ap.add_argument('--chapters', help='only pages of these chapters, e.g. "2,3,5"')
    args = ap.parse_args()
    if args.out:
        K.OUT = os.path.abspath(args.out)

    from playwright.sync_api import sync_playwright

    pages = args.pages or (K.comic_pages() if args.all else translated_pages())
    if args.chapters:
        want = {int(c) for c in args.chapters.split(',')}
        chs = K.chapters()
        pages = [p for p in pages if K.chapter_of(p, chs) in want]
    if not pages:
        print('No translated pages yet.')
        return
    shots = os.path.join(K.OUT, '_render_check')
    os.makedirs(shots, exist_ok=True)
    flagged = []
    with sync_playwright() as p:
        kw = {'executable_path': os.environ['CHROMIUM']} if os.environ.get('CHROMIUM') else {}
        browser = p.chromium.launch(**kw)
        page = browser.new_page(viewport={'width': 560, 'height': 420})
        for name in pages:
            sizes = {}
            for lang, root in (('en', K.SRC), ('ru', K.OUT)):
                page.goto(url(root, name))
                page.wait_for_load_state('load')
                sizes[lang] = page.evaluate(MEASURE)
            for panel, (w, h) in sizes['ru'].items():
                ew, eh = sizes['en'].get(panel, (w, h))
                if w > ew + args.tolerance or h > eh + args.tolerance:
                    flagged.append((name, panel, ew, eh, w, h))
                    for lang, root in (('en', K.SRC), ('ru', K.OUT)):
                        page.goto(url(root, name, panel))
                        page.wait_for_timeout(150)
                        el = page.locator(f'a.panel.visible table').first
                        el.screenshot(path=os.path.join(shots, f'{name}_{panel}_{lang}.png'))
        browser.close()

    for name, panel, ew, eh, w, h in flagged:
        print(f'{name}#{panel}: comic area {ew}x{eh} -> {w}x{h}')
    print(f'\n{len(pages)} pages checked, {len(flagged)} panels overflow'
          + (f'; screenshots in {os.path.relpath(shots, K.ROOT)}/' if flagged else ''))
    sys.exit(1 if flagged else 0)


if __name__ == '__main__':
    main()
