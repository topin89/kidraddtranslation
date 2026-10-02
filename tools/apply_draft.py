#!/usr/bin/env python3
"""Apply draft translations from a TSV file to a PO catalog, marking them fuzzy.

    python tools/apply_draft.py translation/po/ch05.po draft.tsv

TSV lines are "<msgctxt or msgid>\t<translation>"; "#" lines are comments.
Unknown ids abort without saving. Prints how many entries are still empty.
"""
import sys, json, polib
po_path, draft_path = sys.argv[1], sys.argv[2]
draft = {}
for line in open(draft_path, encoding='utf-8'):
    line = line.rstrip('\n')
    if not line or line.startswith('#'): continue
    k, v = line.split('\t', 1)
    draft[k] = v
po = polib.pofile(po_path, wrapwidth=0)
keyed = {e.msgctxt or e.msgid: e for e in po if not e.obsolete}
missing = [k for k in draft if k not in keyed]
if missing: sys.exit('unknown ids: ' + ', '.join(missing))
for k, v in draft.items():
    e = keyed[k]; e.msgstr = v
    if 'fuzzy' not in e.flags: e.flags.append('fuzzy')
po.save()
left = [e.msgctxt for e in po if not e.obsolete and not e.msgstr]
print(f'{po_path}: {len(draft)} applied, {len(left)} still empty', left[:10])
