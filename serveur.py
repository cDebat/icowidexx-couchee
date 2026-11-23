#!/usr/bin/env python3
"""Serveur de l'appli « Bilan vache couchée ».

Deux modes :
- local (défaut) : http://127.0.0.1:8770, rapports dans Output/<n° EDE>/ (Lancer_Bilan.command) ;
- serveur (SERVER_MODE=1, Docker) : écoute sur HOST:PORT, données dans DATA_DIR, et si les variables
  DROPBOX_* sont définies : PDF envoyés dans Dropbox (<DROPBOX_BASE>/Output/<n° EDE>/) et listing
  éleveurs lu depuis Dropbox (<DROPBOX_BASE>/Listing complet*.xlsx).
- sert bilan-vache-couchee.html et eleveurs.js ;
- POST /sauver : génère le PDF du rapport (Chromium via Playwright).
Usage : python3 serveur.py   (ou double-clic sur Lancer_Bilan.command)
"""
import json, os, re, sys, tempfile, threading, time, webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ICI = Path(__file__).resolve().parent
DATA = Path(os.environ.get("DATA_DIR", ICI))
OUTPUT = DATA / "Output"
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8770"))
SERVEUR = os.environ.get("SERVER_MODE") == "1"
FICHIERS = {"/": ICI / "bilan-vache-couchee.html", "/eleveurs.js": DATA / "eleveurs.js"}
TYPES = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8"}

def dbx_actif():
    import dbx
    return dbx.actif()

def sur(txt, defaut):
    t = re.sub(r"[^A-Za-z0-9_-]+", "_", str(txt or "")).strip("_")
    return t or defaut

def pdf(html, chemin):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch(args=["--no-sandbox"] if os.environ.get("NO_SANDBOX") == "1" else [])
        page = nav.new_page()
        page.set_content(html, wait_until="load")
        page.emulate_media(media="print")
        chemin.parent.mkdir(parents=True, exist_ok=True)
        page.pdf(path=str(chemin), format="A4", print_background=True,
                 margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        nav.close()

def synchro_listing():
    """Récupère le listing éleveurs dans Dropbox et régénère eleveurs.js. Renvoie un message."""
    import dbx, maj_eleveurs
    chemin = dbx.dernier_listing()
    if not chemin:
        return "Aucun fichier « Listing complet*.xlsx » trouvé dans " + dbx.base()
    with tempfile.TemporaryDirectory() as t:
        xlsx = Path(t) / "listing.xlsx"
        xlsx.write_bytes(dbx.telecharger(chemin))
        DATA.mkdir(parents=True, exist_ok=True)
        n, tel, mail = maj_eleveurs.convertir(xlsx, DATA / "eleveurs.js")
    return f"{n} élevages chargés depuis {chemin} ({tel} avec téléphone, {mail} avec e-mail)"

def boucle_listing():
    while True:
        try:
            print("Listing :", synchro_listing(), flush=True)
        except Exception as e:  # noqa: BLE001
            print("Listing : échec de la synchro Dropbox :", e, flush=True)
        time.sleep(6 * 3600)

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        chemin = self.path.split("?")[0]
        if chemin == "/ping":
            return self._send(200, b"bilan-ok", "text/plain")
        if chemin == "/maj-eleveurs":   # relit le listing dans Dropbox sans attendre la synchro automatique
            try:
                rep = {"ok": True, "message": synchro_listing()}
            except Exception as e:  # noqa: BLE001
                rep = {"ok": False, "error": str(e)}
            return self._send(200, json.dumps(rep, ensure_ascii=False).encode(), "application/json")
        if chemin.startswith("/pdf/"):
            from urllib.parse import unquote
            f = (OUTPUT / unquote(chemin[5:])).resolve()
            if OUTPUT.resolve() not in f.parents or f.suffix != ".pdf" or not f.exists():
                return self._send(404, b"", "text/plain")
            return self._send(200, f.read_bytes(), "application/pdf")
        f = FICHIERS.get(chemin)
        if not f or not f.exists():
            return self._send(404, b"", "text/plain")
        self._send(200, f.read_bytes(), TYPES[f.suffix])

    def do_POST(self):
        if self.path == "/quitter":
            self._send(200, json.dumps({"ok": True, "server": SERVEUR}).encode(), "application/json")
            if not SERVEUR:   # en mode serveur, l'appli reste active pour les autres utilisateurs
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        if self.path != "/sauver":
            return self._send(404, b"", "text/plain")
        try:
            d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            ede = sur(d.get("ede"), "sans_EDE")
            nom = f"Bilan_vache_{sur(d.get('animal'), 'sans_numero')}_{sur(d.get('date'), date.today().isoformat())}.pdf"
            cible = OUTPUT / ede / nom
            pdf(d["html"], cible)
            rep = {"ok": True, "path": f"Output/{ede}/{nom}"}
            if dbx_actif():
                import dbx
                try:
                    rep["dropbox"] = dbx.televerser(f"Output/{ede}/{nom}", cible.read_bytes())
                    rep["label"] = f"Dropbox : {rep['dropbox'].lstrip('/')}"
                except Exception as e:  # noqa: BLE001
                    rep["dropbox_error"] = str(e)
                    rep["label"] = f"{rep['path']} (sur le serveur ; envoi Dropbox impossible : {e})"
        except Exception as e:  # noqa: BLE001
            rep = {"ok": False, "error": str(e)}
        self._send(200, json.dumps(rep, ensure_ascii=False).encode(), "application/json")

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    try:
        srv = ThreadingHTTPServer((HOST, PORT), H)
    except OSError:  # port déjà pris : une instance de l'appli tourne peut-être déjà
        import urllib.request
        try:
            ok = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/ping", timeout=2).read() == b"bilan-ok"
        except Exception:  # noqa: BLE001
            ok = False
        if ok:
            print("L'appli tourne déjà : ouverture du navigateur.")
            webbrowser.open(f"http://127.0.0.1:{PORT}/")
            sys.exit(0)
        sys.exit(f"Le port {PORT} est occupé par un autre programme.")
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Appli : {url}   (Ctrl+C pour arrêter)", flush=True)
    if SERVEUR and dbx_actif():
        threading.Thread(target=boucle_listing, daemon=True).start()
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
