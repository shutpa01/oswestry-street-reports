"""Local stand-in for the Cloudflare relay, so the page can be tested end-to-end.

Mirrors worker.js: only proxies fixmystreet.com/around, adds CORS headers.
Run: py relay/local_relay.py   (listens on http://localhost:8138/around)
"""
import re
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

ALLOWED = ["bbox", "status", "show_old_reports", "p", "ajax"]
BBOX_RE = re.compile(r"^-?\d+(\.\d+)?(,-?\d+(\.\d+)?){3}$")


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        params = {"ajax": "1"}
        for k in ALLOWED:
            if k in q:
                params[k] = q[k][0]
        bbox = params.get("bbox", "")
        if not BBOX_RE.match(bbox):
            self.send_response(400); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"bad bbox"}'); return
        url = "https://www.fixmystreet.com/around?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AreaReportRelay/1.0 (local test)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
            self.send_response(200); self._cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers(); self.wfile.write(body)
        except Exception as e:
            self.send_response(502); self._cors(); self.end_headers()
            self.wfile.write(('{"error":"%s"}' % str(e)[:120]).encode())

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("Local relay on http://localhost:8138/around  (Ctrl+C to stop)")
    HTTPServer(("localhost", 8138), Handler).serve_forever()
