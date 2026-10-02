#!/usr/bin/env python3
"""Extract comic text into PO catalogs (one per chapter, plus ui.po).

Safe to re-run: existing translations, translator comments and flags are
kept. Entries are keyed by msgctxt "comicN#panel.index", so each bubble is
translated in its own context even when the English repeats.

    python tools/extract.py
"""
import datetime
import os
import sys

import polib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import krlib as K


def new_po(title):
    po = polib.POFile(wrapwidth=0)
    po.metadata = {
        'Project-Id-Version': f'Kid Radd RU — {title}',
        'Language': 'ru',
        'MIME-Version': '1.0',
        'Content-Type': 'text/plain; charset=UTF-8',
        'Content-Transfer-Encoding': '8bit',
        'Plural-Forms': 'nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : '
                        'n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);',
        'X-Generator': 'kidradd tools/extract.py',
    }
    return po


def merge(path, fresh):
    """Carry translations from the PO at `path` (if any) into `fresh`."""
    if not os.path.exists(path):
        return fresh, 0
    old = polib.pofile(path, wrapwidth=0)
    fresh.metadata.update({k: v for k, v in old.metadata.items()
                           if k.startswith(('Last-Translator', 'Language-Team', 'PO-Revision-Date', 'X-Poedit'))})
    by_ctx = {(e.msgctxt, e.msgid): e for e in old if not e.obsolete}
    by_ctx_only = {e.msgctxt: e for e in old if not e.obsolete}
    used = set()
    changed = 0
    for e in fresh:
        o = by_ctx.get((e.msgctxt, e.msgid))
        if o is None:
            o = by_ctx_only.get(e.msgctxt)
            if o is not None and o.msgstr:
                # Source text changed under the same id: keep the old
                # translation but flag it for review.
                e.flags.append('fuzzy')
                e.previous_msgid = o.msgid
                changed += 1
        if o is None:
            continue
        used.add(id(o))
        e.msgstr = o.msgstr
        e.tcomment = o.tcomment
        for f in o.flags:
            if f not in e.flags:
                e.flags.append(f)
    for o in old:
        if id(o) not in used and o.msgstr and not o.obsolete:
            o.obsolete = True
            fresh.append(o)
        elif o.obsolete:
            fresh.append(o)
    return fresh, changed


def main():
    os.makedirs(K.PO_DIR, exist_ok=True)
    chs = K.chapters()
    titles = {no: t for no, t, _ in chs}
    catalogs = {}
    ui = new_po('UI')
    ui_seen = {}

    for page in K.comic_pages():
        s = K.read_src(page + '.htm')
        sprites = K.panel_sprites(s)
        no = K.chapter_of(page, chs)
        po = catalogs.setdefault(no, new_po(f'Chapter {no}: {titles[no]}'))
        for u in K.segment(s, page):
            if K.is_ui(u):
                if u.msgid in ui_seen:
                    ui_seen[u.msgid].occurrences.append((f'kidradd/{page}.htm', str(u.line)))
                    continue
                e = polib.POEntry(msgid=u.msgid, msgstr='',
                                  occurrences=[(f'kidradd/{page}.htm', str(u.line))])
                if u.panel == 'head':
                    e.comment = 'Browser tab title.'
                ui_seen[u.msgid] = e
                ui.append(e)
                continue
            hint = [f'{u.page} panel {u.panel}']
            if u.slot:
                hint.append(f'slot: {u.slot}')
            sp = sprites.get(u.panel)
            if sp:
                hint.append('images: ' + ', '.join(sp))
            po.append(polib.POEntry(
                msgctxt=u.ctxt, msgid=u.msgid, msgstr='',
                comment='\n'.join(hint),
                occurrences=[(f'kidradd/{page}.htm', str(u.line))]))

    # Strings the tools add to the Russian pages themselves.
    for msgid, note in [('notes', 'Label of the Translator Notes button (fits in a 39px box, like "zoom"/"list").'),
                        ('Translator notes', 'Heading of the notes popup.'),
                        ('close', 'Close button of the notes popup.')]:
        ui.append(polib.POEntry(msgid=msgid, msgstr='', comment=note))

    for e in ui:  # keep references short: the first few pages are enough
        if len(e.occurrences) > 3:
            e.occurrences = e.occurrences[:3]

    report = []
    for no, po in sorted(catalogs.items()):
        path = K.po_path_for_chapter(no)
        po, changed = merge(path, po)
        po.save(path)
        report.append((os.path.relpath(path, K.ROOT), len([e for e in po if not e.obsolete]), changed))
    path = os.path.join(K.PO_DIR, 'ui.po')
    ui, changed = merge(path, ui)
    ui.save(path)
    report.append((os.path.relpath(path, K.ROOT), len(ui), changed))

    total = sum(n for _, n, _ in report)
    for p, n, c in report:
        print(f'{p:28} {n:5} entries' + (f'  ({c} changed sources, marked fuzzy)' if c else ''))
    print(f'{"total":28} {total:5}')


if __name__ == '__main__':
    main()
