#!/bin/bash
# Double-clic (macOS) : met à jour la liste des éleveurs puis lance l'appli.
cd "$(dirname "$0")" || exit 1
if [ ! -d .venv ]; then
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt && playwright install chromium
else
  source .venv/bin/activate
fi
python3 maj_eleveurs.py
python3 serveur.py
