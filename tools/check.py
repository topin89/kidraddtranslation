#!/usr/bin/env python3
"""Validate translations and report progress.

    python tools/check.py            # all catalogs
    python tools/check.py ch01 ui    # just these

Checks each translated entry for:
  tags      HTML tags in msgid and msgstr differ (b, i, br, font...)
  glossary  a glossary term in the English has no matching Russian term
  latin     msgstr still contains long runs of English words
  html      bare "<" or "&" that would break the page markup
Exit code is 1 if any tag/html errors were found (warnings don't fail).
"""
import collections
import os
import re
import sys

import polib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import krlib as K

TAG = re.compile(r'<\s*(/?)\s*([A-Za-z]+)')
GLOSSARY = os.path.join(K.TRANSLATION, 'glossary.tsv')


def load_glossary():
    rules = []
    with open(GLOSSARY, encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            en, ru, *rest = line.rstrip('\n').split('\t')
            rules.append((re.compile(en), re.compile(ru), rest[0] if rest else ''))
    return rules


def tags(s):
    return collections.Counter((c + n.lower()) for c, n in TAG.findall(s))


def check_entry(e, glossary):
    errors, warnings = [], []
    if tags(e.msgid) != tags(e.msgstr):
        diff = (tags(e.msgid) - tags(e.msgstr)) + (tags(e.msgstr) - tags(e.msgid))
        errors.append('tags differ: ' + ', '.join(f'<{t}>' for t in sorted(diff)))
    body = re.sub(r'<[^>]*>', '', e.msgstr)
    if re.search(r'<|&(?![A-Za-z]+;|#\d+;)', body):
        errors.append('bare "<" or "&" (use &lt; / &amp;)')
    for en, ru, note in glossary:
        if en.search(e.msgid) and not ru.search(e.msgstr):
            warnings.append(f'glossary: {note or en.pattern}')
    if re.search(r'[A-Za-z]{3,}(?:\s+[A-Za-z]{2,}){2,}', K.plain_text(e.msgstr)):
        warnings.append('latin: looks like untranslated English')
    return errors, warnings


def main():
    want = set(sys.argv[1:])
    glossary = load_glossary()
    n_err = n_warn = 0
    totals = collections.Counter()
    rows = []
    for f in sorted(os.listdir(K.PO_DIR)):
        if not f.endswith('.po') or (want and f[:-3] not in want):
            continue
        po = polib.pofile(os.path.join(K.PO_DIR, f))
        c = collections.Counter()
        for e in po:
            if e.obsolete:
                continue
            c['total'] += 1
            if not e.msgstr:
                continue
            c['fuzzy' if 'fuzzy' in e.flags else 'done'] += 1
            errors, warnings = check_entry(e, glossary)
            where = e.msgctxt or e.msgid[:30]
            for m in errors:
                print(f'ERROR   {f}:{e.linenum} {where}: {m}')
            for m in warnings:
                print(f'warning {f}:{e.linenum} {where}: {m}')
            n_err += len(errors)
            n_warn += len(warnings)
        totals.update(c)
        rows.append((f, c))

    print()
    print(f'{"catalog":10} {"reviewed":>9} {"draft":>6} {"empty":>6} {"total":>6}')
    for f, c in rows + [('TOTAL', totals)]:
        empty = c['total'] - c['done'] - c['fuzzy']
        pct = 100 * (c['done'] + c['fuzzy']) / c['total'] if c['total'] else 0
        print(f'{f:10} {c["done"]:9} {c["fuzzy"]:6} {empty:6} {c["total"]:6}   {pct:5.1f}% translated')
    print(f'\n{n_err} errors, {n_warn} warnings')
    sys.exit(1 if n_err else 0)


if __name__ == '__main__':
    main()
