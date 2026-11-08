#!/usr/bin/env python3
"""fix_export.py — the one-command version.

    python fix_export.py EXPORT.html

Does the whole job with no other steps:
  1. Serves a doctored copy of the export locally and opens it in your
     browser (if the browser does not open by itself, the URL is printed —
     open it manually).
  2. The page expands the artifact and sends its generated layout CSS back
     (takes ~10–40 seconds; the tab title changes to "CAPTURED ...").
  3. Runs fix_antigravity_export.py with that CSS to write EXPORT-fixed.html
     next to the original, then stops the server.

On Windows you never need the command line at all: drag the exported HTML
file onto FIX_MY_EXPORT.bat in this folder.

Stdlib only.
"""
import subprocess, sys, tempfile, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from harvest_css import SNIPPET  # the capture script injected into the copy

import functools
print = functools.partial(print, flush=True)  # show prompts at once, even when piped


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print(__doc__)
        return 0
    export = Path(sys.argv[1]).expanduser()
    if not export.is_file():
        print(f'ERROR: no such file: {export}')
        return 1
    html = export.read_text(encoding='utf-8')
    if '</body>' not in html:
        print('ERROR: no </body> in the export; cannot inject the capture script.')
        return 1
    page = html.replace('</body>', SNIPPET, 1).encode('utf-8')

    captured = {}
    done = threading.Event()

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
                captured['css'] = body
                done.set()
            self.send_response(200); self.end_headers(); self.wfile.write(b'ok')

        def log_message(self, *a):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), H)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{port}/harvest-export.html'
    print(f'Opening your browser to capture the layout styles: {url}')
    print('(If nothing opens, paste that address into any browser yourself.)')
    try:
        webbrowser.open(url)
    except Exception:
        pass
    print('Waiting for the capture (the tab title changes to "CAPTURED ...")...')
    if not done.wait(timeout=180):
        print('ERROR: no capture arrived within 3 minutes. Is the page open in a browser?')
        server.shutdown()
        return 1
    server.shutdown()
    css = captured['css']
    print(f'Captured {len(css)} bytes of layout CSS. Building the fixed file...')
    with tempfile.NamedTemporaryFile('wb', suffix='.css', delete=False) as tf:
        tf.write(css)
        css_path = tf.name
    out = export.with_name(export.stem + '-fixed.html')
    r = subprocess.run([sys.executable, str(HERE / 'fix_antigravity_export.py'),
                        str(export), '--css', css_path, '-o', str(out)])
    Path(css_path).unlink(missing_ok=True)
    if r.returncode == 0:
        print(f'Done: {out}')
    return r.returncode


if __name__ == '__main__':
    raise SystemExit(main())
