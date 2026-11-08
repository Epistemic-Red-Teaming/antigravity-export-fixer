#!/usr/bin/env python3
"""fix_antigravity_export.py — make an exported Antigravity artifact HTML portable.

The problem (verified 2026-11-07 against Google's own /generative_ui docs):
Antigravity widgets are styled with the app's theme colors, supplied at view
time as CSS variables (--background, --foreground, --card, --primary, ...).
"Export Artifact" ships the file WITHOUT those definitions — Google documents
this ("The exported file doesn't include the Antigravity App's theme colors,
so it can look different when you open it in a browser"). In practice the
result is worse than "different": every var(--x) reference resolves to
nothing, dark panels go transparent and light graphics go black, so content
(e.g. SVG infographics) renders invisible in a standalone browser. The file
also depends on a live external script (the gstatic Tailwind runtime) to
generate its layout CSS in the browser at open time.

What this script does, in order:
  1. Scans the export for every var(--name) it references.
  2. Injects a <style> block defining those variables from a theme JSON
     (default: theme-onyx-dark.json next to this script — values sampled
     from in-app screenshots of the deck being fixed; see that file).
  3. Optionally (--css harvested.css) BAKES the layout CSS: removes the
     external Tailwind runtime <script> tag and inlines a stylesheet that
     was harvested from one real browser run of the export (see below).
     With theme + baked CSS the output makes zero external requests and
     renders the same offline as online.

How to harvest the CSS for step 3 (once per export design, ~15 seconds):
  - Add a snippet that, after load, clicks the artifact's "Expand All"
    control (so every element exists in the DOM and the Tailwind runtime
    generates every class), waits, then serializes document.styleSheets
    and POSTs it to a local server.   - Any browser works; the runtime does the compiling for you.
    harvest_css.py, packaged alongside this script, automates the whole
    capture: it serves the doctored copy and saves the POSTed stylesheet.

Usage:
  python3 fix_antigravity_export.py EXPORT.html [-o OUT.html]
          [--theme theme.json] [--css harvested.css]

Stdlib only. The original file is never modified; output defaults to
<name>-fixed.html next to the input.
"""
import argparse, json, re, sys
from pathlib import Path

SCRIPT_RE = re.compile(
    r'<script[^>]*src="https://www\.gstatic\.com/antigravity/[^"]*"[^>]*>\s*</script>',
    re.IGNORECASE)
VAR_RE = re.compile(r'var\((--[a-z0-9-]+)')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('export', type=Path, help='the exported Antigravity HTML file')
    ap.add_argument('-o', '--out', type=Path, help='output path (default: <name>-fixed.html)')
    ap.add_argument('--theme', type=Path,
                    default=Path(__file__).with_name('theme-onyx-dark.json'),
                    help='theme JSON mapping --var names to values')
    ap.add_argument('--css', type=Path,
                    help='harvested layout CSS to bake in (also removes the runtime script tag)')
    args = ap.parse_args()

    html = args.export.read_text(encoding='utf-8')
    theme = {k: v for k, v in json.loads(args.theme.read_text(encoding='utf-8')).items()
             if k.startswith('--')}

    referenced = sorted(set(VAR_RE.findall(html)))
    missing = [v for v in referenced if v not in theme]
    if missing:
        print(f'ERROR: the export references variables the theme does not define: {missing}',
              file=sys.stderr)
        print('Add values for them to the theme JSON and re-run; nothing was written.',
              file=sys.stderr)
        return 1

    root_block = ':root {\n' + '\n'.join(f'  {k}: {theme[k]};' for k in referenced) + '\n}'
    inject = f'<style id="antigravity-theme">\n{root_block}\n</style>\n'

    baked_note = 'theme only (layout still loads the Tailwind runtime script)'
    if args.css:
        css = args.css.read_text(encoding='utf-8')
        html, n = SCRIPT_RE.subn('', html)
        if n == 0:
            print('ERROR: --css given but no gstatic Tailwind script tag was found to remove; '
                  'refusing to bake blindly.', file=sys.stderr)
            return 1
        inject += f'<style id="baked-layout-css">\n{css}\n</style>\n'
        baked_note = f'theme + baked layout CSS ({len(css)} chars, runtime script removed)'

    m = re.search(r'<head[^>]*>', html, re.IGNORECASE)
    if not m:
        print('ERROR: no <head> tag found; cannot inject styles.', file=sys.stderr)
        return 1
    html = html[:m.end()] + '\n' + inject + html[m.end():]

    out = args.out or args.export.with_name(args.export.stem + '-fixed.html')
    out.write_text(html, encoding='utf-8')
    external = re.findall(r'(?:src|href)="https?://[^"]+"', html)
    print(f'wrote {out} ({len(html)} chars)')
    print(f'  variables defined: {len(referenced)} ({", ".join(referenced)})')
    print(f'  mode: {baked_note}')
    print(f'  external references remaining: {len(external)} {external if external else ""}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
