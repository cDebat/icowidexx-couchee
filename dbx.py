"""Accès Dropbox minimal (stdlib uniquement) : envoi des PDF et lecture du listing éleveurs.

Configuration par variables d'environnement (jamais dans le code ni sur GitHub) :
  DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN  -> secrets (fichier réservé à root sur le serveur)
  DROPBOX_BASE  -> dossier Dropbox de l'appli, ex. /Rurale/Primholstein.eu/Idexx
"""
import json, os, time, urllib.error, urllib.parse, urllib.request

_tok = {"v": None, "exp": 0}

def actif():
    return all(os.environ.get(k) for k in ("DROPBOX_APP_KEY", "DROPBOX_APP_SECRET", "DROPBOX_REFRESH_TOKEN"))

def base():
    return "/" + os.environ.get("DROPBOX_BASE", "").strip("/")

def _jeton():
    if _tok["v"] and time.time() < _tok["exp"] - 60:
        return _tok["v"]
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token", "refresh_token": os.environ["DROPBOX_REFRESH_TOKEN"],
        "client_id": os.environ["DROPBOX_APP_KEY"], "client_secret": os.environ["DROPBOX_APP_SECRET"]}).encode()
    r = json.load(urllib.request.urlopen("https://api.dropboxapi.com/oauth2/token", data, timeout=30))
    _tok["v"], _tok["exp"] = r["access_token"], time.time() + int(r.get("expires_in", 14400))
    return _tok["v"]

def _erreur(e):
    try:
        return e.read().decode("utf-8", "replace")[:300]
    except Exception:  # noqa: BLE001
        return str(e)

def _api(url, arg=None, corps=None, ctype=None, header_arg=False):
    h = {"Authorization": "Bearer " + _jeton()}
    if header_arg:
        h["Dropbox-API-Arg"] = json.dumps(arg)          # ASCII échappé : obligatoire côté Dropbox
        h["Content-Type"] = ctype or "application/octet-stream"
        data = corps
    else:
        h["Content-Type"] = "application/json"
        data = json.dumps(arg).encode()
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    try:
        return urllib.request.urlopen(req, timeout=60).read()
    except urllib.error.HTTPError as e:
        raise RuntimeError("Dropbox : " + _erreur(e)) from None

def televerser(chemin_relatif, octets):
    """Envoie un fichier dans DROPBOX_BASE/<chemin_relatif> (écrase s'il existe). Renvoie le chemin Dropbox."""
    chemin = base() + "/" + chemin_relatif.strip("/")
    _api("https://content.dropboxapi.com/2/files/upload",
         {"path": chemin, "mode": "overwrite", "autorename": False, "mute": True},
         octets, header_arg=True)
    return chemin

def lister(sous_dossier=""):
    chemin = base() + ("/" + sous_dossier.strip("/") if sous_dossier else "")
    r = json.loads(_api("https://api.dropboxapi.com/2/files/list_folder", {"path": chemin}))
    return r.get("entries", [])

def telecharger(chemin):
    return _api("https://content.dropboxapi.com/2/files/download", {"path": chemin}, header_arg=True)

def dernier_listing():
    """Chemin Dropbox du listing éleveurs le plus récent (« Listing complet*.xlsx » dans DROPBOX_BASE)."""
    c = [e for e in lister() if e.get(".tag") == "file" and e["name"].lower().startswith("listing complet")
         and e["name"].lower().endswith(".xlsx")]
    if not c:
        return None
    return max(c, key=lambda e: e.get("server_modified", ""))["path_display"]
