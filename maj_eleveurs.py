#!/usr/bin/env python3
"""Convertit « Listing complet éleveurs - BSE 2026.xlsx » en eleveurs.js (lu par l'appli).

Les colonnes sont repérées par leur TITRE (ordre libre, colonnes en plus acceptées, ex. « Adresse ») :
n° atelier (EDE) · Établissement · Adresse (facultative) · Commune · Catégorie · Téléphone 1 · Téléphone 2 · Email.
Si les titres ne sont pas reconnus, ancien ordre fixe : A EDE · B Établissement · C Commune · D Catégorie · E Tél 1 · F Tél 2 · G Email.
Un élevage peut avoir plusieurs ateliers (même EDE) : une seule entrée par EDE.
Téléphone retenu : un portable (06/07) s'il y en a un, sinon le fixe.
Usage : python3 maj_eleveurs.py [chemin_du_listing.xlsx]
"""
import json, re, sys, unicodedata
from pathlib import Path
import openpyxl

ICI = Path(__file__).resolve().parent

def texte(v):
    return "" if v is None else str(v).strip()

def portable(t):
    return bool(re.match(r"^0[67]", re.sub(r"[\s.\-]", "", re.sub(r"^(\+33|0033)", "0", t))))

def choisir_tel(a, b):
    return next((t for t in (a, b) if t and portable(t)), a or b or "")

def _norm(v):
    t = unicodedata.normalize("NFD", texte(v).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")

def _colonnes(entetes):
    """Repère les colonnes par leur titre. Renvoie un dict champ -> index (ou None)."""
    H = [_norm(h) for h in entetes]
    def premier(motif, exclure=()):
        return next((i for i, h in enumerate(H) if i not in exclure and re.search(motif, h)), None)
    c = {}
    c["ede"] = premier(r"(\bede\b|numero)")
    c["nom"] = premier(r"(etablissement|raison|libelle)")
    c["adresse"] = premier(r"adresse")
    c["commune"] = premier(r"commune")
    c["mail"] = premier(r"mail")
    tels = [i for i, h in enumerate(H) if re.match(r"(tel|mobile|phone)", h)]
    c["tel1"] = tels[0] if len(tels) > 0 else None
    c["tel2"] = tels[1] if len(tels) > 1 else None
    return c

def convertir(src, dest):
    """Lit le listing Excel `src` et écrit `dest` (eleveurs.js). Renvoie (nb élevages, nb avec tél., nb avec mail)."""
    ws = openpyxl.load_workbook(src, data_only=True).active
    lignes = list(ws.iter_rows(values_only=True))
    c = _colonnes(lignes[0]) if lignes else {}
    if c.get("ede") is None or c.get("nom") is None:  # titres non reconnus : ancien ordre fixe
        c = {"ede": 0, "nom": 1, "adresse": None, "commune": 2, "tel1": 4, "tel2": 5, "mail": 6}
    def val(r, k):
        i = c.get(k)
        return texte(r[i]) if i is not None and i < len(r) else ""
    par_ede = {}
    for r in lignes[1:]:
        ede = val(r, "ede")
        if not ede:
            continue
        o = {"num": ede, "nom": val(r, "nom"), "commune": val(r, "commune"), "adresse": val(r, "adresse"),
             "tel": choisir_tel(val(r, "tel1"), val(r, "tel2")), "mail": val(r, "mail")}
        e = par_ede.get(ede)
        if not e:
            par_ede[ede] = o
        else:  # même EDE, autre atelier : compléter les champs vides, préférer un portable
            if o["tel"] and (not e["tel"] or (not portable(e["tel"]) and portable(o["tel"]))):
                e["tel"] = o["tel"]
            e["mail"] = e["mail"] or o["mail"]
            e["adresse"] = e["adresse"] or o["adresse"]
    liste = sorted(par_ede.values(), key=lambda o: o["nom"].upper())
    Path(dest).write_text("window.ELEVEURS=" + json.dumps(liste, ensure_ascii=False) + ";\n", encoding="utf-8")
    return len(liste), sum(1 for o in liste if o["tel"]), sum(1 for o in liste if o["mail"])

if __name__ == "__main__":
    SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else next(ICI.glob("Listing complet*.xlsx"), None)
    if not SRC or not SRC.exists():
        sys.exit("Listing introuvable : placer « Listing complet éleveurs - BSE 2026.xlsx » dans le dossier.")
    n, t, m = convertir(SRC, ICI / "eleveurs.js")
    print(f"{n} élevages écrits dans eleveurs.js ({t} avec téléphone, {m} avec e-mail)")
