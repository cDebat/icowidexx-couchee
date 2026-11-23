#!/usr/bin/env python3
"""Serveur local de l'appli « Bilan vache couchée » : http://127.0.0.1:8770

- sert bilan-vache-couchee.html et eleveurs.js ;
- POST /sauver : génère le PDF du rapport (Chromium via Playwright) dans Output/<n° EDE>/.
Usage : python3 serveur.py   (ou double-clic sur Lancer_Bilan.command)
"""
import json, re, sys, threading, webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ICI = Path(__file__).resolve().parent
OUTPUT = ICI / "Output"
PORT = 8770
FICHIERS = {"/": "bilan-vache-couchee.html", "/eleveurs.js": "eleveurs.js"}
TYPES = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8"}

def sur(txt, defaut):
    t = re.sub(r"[^A-Za-z0-9_-]+", "_", str(txt or "")).strip("_")
    return t or defaut

def pdf(html, chemin):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        page = nav.new_page()
        page.set_content(html, wait_until="load")
        page.emulate_media(media="print")
        chemin.parent.mkdir(parents=True, exist_ok=True)
        page.pdf(path=str(chemin), format="A4", print_background=True,
                 margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        nav.close()

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        chemin = self.path.split("?")[0]
        if chemin == "/ping":
            return self._send(200, b"bilan-ok", "text/plain")
        nom = FICHIERS.get(chemin)
        f = ICI / nom if nom else None
        if not f or not f.exists():
            return self._send(404, b"", "text/plain")
        self._send(200, f.read_bytes(), TYPES[f.suffix])

    def do_POST(self):
        if self.path != "/sauver":
            return self._send(404, b"", "text/plain")
        try:
            d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            ede = sur(d.get("ede"), "sans_EDE")
            nom = f"Bilan_vache_{sur(d.get('animal'), 'sans_numero')}_{sur(d.get('date'), date.today().isoformat())}.pdf"
            cible = OUTPUT / ede / nom
            pdf(d["html"], cible)
            rep = {"ok": True, "path": f"Output/{ede}/{nom}"}
        except Exception as e:  # noqa: BLE001
            rep = {"ok": False, "error": str(e)}
        self._send(200, json.dumps(rep, ensure_ascii=False).encode(), "application/json")

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Appli : {url}   (Ctrl+C pour arrêter)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
