#!/usr/bin/env python3
"""harvest_css.py — capture the layout CSS an Antigravity export generates in a browser.

The export's layout styles are produced at open time by a runtime script.
This helper writes a temporary copy of the export with a small script added:
when the copy is opened in any browser, it expands the artifact fully, waits
until the generated stylesheet stops growing, and POSTs the stylesheet back
to this helper, which saves it as a .css file next to the export.

Usage:
  python3 harvest_css.py EXPORT.html [-o OUT.css] [--port 8902]

Then open the printed URL in a browser and wait ~30 seconds. If the machine
serving this is not the machine with the browser, tunnel the port first
(e.g. ssh -R 80:127.0.0.1:8902 nokey@localhost.run) and open the tunnel URL
for the /harvest-export.html path instead.
Stdlib only. Ctrl+C stops the server after the capture lands.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SNIPPET = """
<script>
window.addEventListener('load', () => {
  const collect = () => {
    let css = '';
    const grab = (s) => { try { for (const r of s.cssRules) css += r.cssText + '\\n'; } catch (e) {} };
    for (const s of document.styleSheets) grab(s);
    if (document.adoptedStyleSheets) for (const s of document.adoptedStyleSheets) grab(s);
    return css;
  };
  setTimeout(() => {
    const b = [...document.querySelectorAll('button')].find(x => /expand all/i.test(x.textContent || ''));
    if (b) b.click();
    let best = collect(), stable = 0, rounds = 0;
    const iv = setInterval(() => {
      rounds++;
      if (rounds === 2) {
        const sel = document.querySelector('select');
        if (sel) for (const o of sel.options) { sel.value = o.value; sel.dispatchEvent(new Event('change', {bubbles: true})); }
      }
      const now = collect();
      if (now.length > best.length) { best = now; stable = 0; } else { stable++; }
      if ((stable >= 3 && rounds >= 6) || rounds >= 30) {
        clearInterval(iv);
        fetch('/capture', {method: 'POST', headers: {'Content-Type': 'text/css'}, body: best})
          .then(() => { document.title = 'CAPTURED ' + best.length; });
      }
    }, 1000);
  }, 2500);
});
</script>
</body>"""


def main() -> int:
    ap = argparse.ArgumentParser(description='Harvest generated CSS from an Antigravity export.')
    ap.add_argument('export', type=Path)
    ap.add_argument('-o', '--out', type=Path)
    ap.add_argument('--port', type=int, default=8902)
    args = ap.parse_args()

    html = args.export.read_text(encoding='utf-8')
    if '</body>' not in html:
        print('ERROR: no </body> in the export; cannot inject the capture script.')
        return 1
    page = html.replace('</body>', SNIPPET, 1).encode('utf-8')
    out = args.out or args.export.with_name(args.export.stem + '-harvested.css')

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith('/harvest-export'):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(page)
            else:
                self.send_response(404); self.end_headers()

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            if self.path == '/capture':
                out.write_bytes(body)
                print(f'captured {len(body)} bytes -> {out}')
            self.send_response(200); self.end_headers(); self.wfile.write(b'ok')

        def log_message(self, *a):
            pass

    print(f'Open in a browser: http://127.0.0.1:{args.port}/harvest-export.html')
    print('Wait ~30 seconds; the tab title changes to "CAPTURED <bytes>". Ctrl+C to stop.')
    ThreadingHTTPServer(('127.0.0.1', args.port), H).serve_forever()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
