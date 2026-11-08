# Antigravity HTML Export Infographic Fixer

Makes an exported Antigravity artifact (generative-UI HTML) render correctly
in a standalone browser — including fully offline.

## The problem

Antigravity widgets are styled with the app's theme colors, supplied at view
time as CSS variables (`--background`, `--foreground`, `--card`, `--primary`,
…). Google's own documentation states that **Export Artifact does not include
the theme colors**, so the exported file "can look different" in a browser.
In practice it is worse than different: every `var(--x)` reference resolves to
nothing, so dark panels go transparent and light graphics go black — entire
infographics render as solid black rectangles. The exported file also depends
on a live external script (Google's Tailwind runtime) to generate its layout
CSS in the browser at open time, so it needs the internet and Google's server
uptime to render at all.

First found on a 28-slide deck whose graphics used 9 theme variables in 382
places, defined none of them, and contained no style block of its own.

## What the fixer does

1. Scans the export for every `var(--name)` it references.
2. Injects the missing definitions from a theme file (colors sampled from
   in-app screenshots of the artifact being fixed).
3. Optionally bakes in the layout CSS the runtime generates: the external
   script tag is removed and the stylesheet is inlined. The result makes
   **zero external requests** and renders the same offline as online.
   If the theme file lacks a value for any referenced variable, the script
   refuses to run rather than ship a half-fix.

## Files in this package

| File | What it is |
| --- | --- |
| `fix_export.py` + `FIX_MY_EXPORT.bat` | The one-command driver. On Windows, drag the broken export onto the .bat; anywhere, `python fix_export.py EXPORT.html`. It runs the capture and the fix for you. |
| `fix_antigravity_export.py` | The fixer itself (used directly for the manual two-step below). Stdlib-only Python. |
| `theme-onyx-dark.json` | The color table it injects (21 tokens). Eight values were sampled 2026-11-07 from in-app screenshots (bg `#191414`, panels `#282424`, orange `#cc4100`, text `#ffffff`, muted `#a8a9b2`, border `#383434`); the rest of the standard set is filled in by derivation from those (same-role tokens set equal) or, for the error red and corner radius, the token family's conventional dark-theme defaults. Every value's provenance is recorded in the file itself. Edit to taste. |
| `harvest_css.py` | Captures a fresh layout stylesheet for a new export design: serves a doctored copy of the export; open it in any browser, wait ~30 s, and the generated CSS is saved for step 3. |
| `example-harvested.css` | A real captured layout stylesheet (9,088 bytes), so you can see what a capture looks like before making your own. |

## Quickstart

**The easy way (Windows):** drag the broken exported HTML file onto
`FIX_MY_EXPORT.bat` in this folder. A console window opens, your browser
opens with it, and about 30 seconds later `EXPORT-fixed.html` appears next
to the original. Same thing from a terminal on any OS:

```
python fix_export.py EXPORT.html
```

**Manually, in two steps** — theme only (fixes the black graphics; layout still loads Google's script):

```
python3 fix_antigravity_export.py EXPORT.html
```

Full fix (offline-capable), two steps:

```
python3 harvest_css.py EXPORT.html        # then open the printed URL, wait ~30 s
python3 fix_antigravity_export.py EXPORT.html --css EXPORT-harvested.css
```

Output defaults to `EXPORT-fixed.html`. The original file is never modified.

## Limits, stated plainly

- Theme values are not Google's official theme tokens: eight are **samples
  from screenshots**; the wider standard set is derived from those samples or
  set to the token family's conventional defaults, each marked in the file.
  The fixed file matches the in-app look for the colors the artifact mainly
  uses; an artifact leaning heavily on a derived token may differ slightly
  from its in-app rendering in those accents.
- A harvested stylesheet covers the design it was captured from. A different
  artifact design needs its own 30-second capture.
- Verified end-to-end on a 28-slide deck in a plain browser: slides 1, 2
  and 4 eyeballed (a taxonomy graphic that was a black block became fully
  readable); the other 25 share the same styling system and were present
  in the document during capture, but were not individually eyeballed.
- This fixes portability only; an export's *contents* are untouched. Check
  what your artifact contains before sharing it — generated artifacts can
  carry local file paths and other machine details verbatim.

Built 2026-11-07 by Research Partner with Ian Camp, after the ArgonThreadRnD
deck rendered as black rectangles in every standalone browser while looking
fine inside Antigravity.
