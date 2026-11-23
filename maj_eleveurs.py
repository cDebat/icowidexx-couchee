#!/usr/bin/env python3
"""Convertit « Listing complet éleveurs - BSE 2026.xlsx » en eleveurs.js (lu par l'appli).

Colonnes du listing : A n° atelier (EDE) · B Établissement · C Commune · D Catégorie · E Téléphone 1 · F Téléphone 2 · G Email.
Un élevage peut avoir plusieurs ateliers (même EDE) : une seule entrée par EDE.
Téléphone retenu : un portable (06/07) s'il y en a un, sinon le fixe.
Usage : python3 maj_eleveurs.py [chemin_du_listing.xlsx]
"""
import json, re, sys
from pathlib import Path
import openpyxl

ICI = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else next(ICI.glob("Listing complet*.xlsx"), None)
if not SRC or not SRC.exists():
    sys.exit("Listing introuvable : placer « Listing complet éleveurs - BSE 2026.xlsx » dans le dossier.")

def texte(v):
    return "" if v is None else str(v).strip()

def portable(t):
    return bool(re.match(r"^0[67]", re.sub(r"[\s.\-]", "", re.sub(r"^(\+33|0033)", "0", t))))

def choisir_tel(a, b):
    return next((t for t in (a, b) if t and portable(t)), a or b or "")

ws = openpyxl.load_workbook(SRC, data_only=True).active
par_ede = {}
for r in ws.iter_rows(min_row=2, values_only=True):
    ede = texte(r[0])
    if not ede:
        continue
    o = {"num": ede, "nom": texte(r[1]), "commune": texte(r[2]),
         "tel": choisir_tel(texte(r[4]), texte(r[5])), "mail": texte(r[6])}
    e = par_ede.get(ede)
    if not e:
        par_ede[ede] = o
    else:  # même EDE, autre atelier : compléter les champs vides, préférer un portable
        if o["tel"] and (not e["tel"] or (not portable(e["tel"]) and portable(o["tel"]))):
            e["tel"] = o["tel"]
        e["mail"] = e["mail"] or o["mail"]

liste = sorted(par_ede.values(), key=lambda o: o["nom"].upper())
(ICI / "eleveurs.js").write_text("window.ELEVEURS=" + json.dumps(liste, ensure_ascii=False) + ";\n", encoding="utf-8")
print(f"{len(liste)} élevages écrits dans eleveurs.js ({sum(1 for o in liste if o['tel'])} avec téléphone, {sum(1 for o in liste if o['mail'])} avec e-mail)")
