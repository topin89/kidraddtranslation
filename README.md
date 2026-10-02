# Kid Radd — Russian translation

An offline copy of Dan Miller's *Kid Radd* (2002–2004, `kidradd/`, the 2012
bgreco.net version) plus the tools to produce a Russian edition of it.

The English site in `kidradd/` is the untouched source, apart from removing the
old WebKit `prescaled/` image workaround. The Russian edition is **generated**
into `ru/`. Don't edit files there; they are overwritten on every build.

## Quick start

```sh
pip install -r requirements.txt      # polib (playwright is optional)
python tools/build.py                # -> ru/
```

Then open `ru/comic1.htm` in a browser. It works straight from disk, no server needed.

## Layout

| Path | What |
|---|---|
| `kidradd/` | Original English site (source of truth for text and assets) |
| `translation/po/chNN.po` | Comic text, one catalog per chapter (29 chapters, from `listp.htm`) |
| `translation/po/ui.po` | Strings repeated on every page: zoom / list / notes buttons, tab title, copyright |
| `translation/notes/*.md` | Translator notes, shown by the **notes** button under each panel |
| `translation/glossary.tsv` | Fixed name/term translations, enforced by `check.py` |
| `translation/overlay/` | Files copied over the assets in `ru/`: Cyrillic font, `ru.js`, `ru.css`, and later any GIFs redrawn in Russian |
| `tools/` | `extract.py`, `build.py`, `check.py`, `render_check.py` |
| `ru/` | Build output (git-ignored) |

## Workflow

1. **Translate** in [Poedit](https://poedit.net/): open `translation/po/chNN.po`.
   - Each entry is one bubble or narration box. The context (`comic12#p3.2`) is
     page 12, panel `p3`, second text block.
   - The comments list the panel's sprite images, which usually tell you who's talking.
   - Keep the HTML tags that appear in the English (`<b>`, `<i>`, `<br>`, `<font ...>`).
   - **Drafts are marked fuzzy** ("Needs work" in Poedit). Clearing the flag marks an entry as reviewed.
2. **Check**: `python tools/check.py` reports broken tags, glossary misses and progress per chapter.
3. **Build**: `python tools/build.py` includes drafts. `--strict` builds only reviewed text.
   Untranslated strings stay in English.
4. **Fit check** (optional): `python tools/render_check.py` renders the English and Russian
   pages in headless Chromium. It lists panels where Russian text made the comic
   area grow, and saves screenshots to `ru/_render_check/`.
5. `python tools/extract.py` regenerates the catalogs from the HTML and keeps existing
   translations. You only need it if the English pages or the extraction rules change.

### Translator notes

Add a section to any `.md` file in `translation/notes/`:

```md
## comic12#p3
The pun here is on ... **bold**, *italic*, [links](https://example.com) work.

A blank line starts a new paragraph.
```

The heading is the page and panel (`title`, `p1`, `p2`, ...). Panels without a note
show a greyed-out button.

### Animation cue

When a panel plays a one-shot GIF animation that lasts 3 s or more, the **next**
arrow starts pulsing once the animation reaches its last frame. `build.py` reads
the durations from the GIF files (`ru/kr-anim.js`). The threshold is
`ANIM_THRESHOLD_MS` in `translation/overlay/ru.js`.

## Scope and status

- In scope: comic pages `comic1`–`comic601` (plus `comic425a`).
- Deferred:
  - GIFs with English text baked in (battle messages, signs, copyright cards).
    Later they go into `translation/overlay/` under the same filename.
  - Non-comic pages (FAQ, making-of, Bogey game, store, links).
  - An HQ recording of the Flash finale (`comic601.swf`).

## Credits and licences

- *Kid Radd* © 2002–2004 Dan Miller. The 2012 no-frames viewer is by Brad Greco (bgreco.net).
- `translation/overlay/vag_round_cyr.ttf` is "VAG Round Cyrillic". Cyrillic glyphs ©
  2008–2022 dsp2oo3, <http://wks.arai-kibou.ru/fontlab.php>. It's used for the chapter
  title captions, in place of the Latin-only `vag_rundschrift.ttf`.
