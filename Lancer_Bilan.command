#!/bin/bash
# Double-clic (macOS) : prépare l'environnement Python (première fois), met à jour la liste des éleveurs puis lance l'appli.
cd "$(dirname "$0")" || exit 1

# Python récent (>= 3.9) : le Python de conda « base » est trop ancien pour Playwright.
trouve_python() {
  for p in /opt/anaconda3/envs/notebooklm/bin/python3.12 /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3 python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
    command -v "$p" >/dev/null 2>&1 || continue
    "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)' 2>/dev/null && { command -v "$p"; return 0; }
  done
  return 1
}

# .venv inutilisable (créé avec un Python trop ancien) : on le refait
if [ -d .venv ] && ! .venv/bin/python -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)' 2>/dev/null; then
  rm -rf .venv
fi
if [ ! -d .venv ]; then
  PY="$(trouve_python)" || { echo "Aucun Python >= 3.9 trouvé. Installer Python 3.12 (python.org ou Homebrew)."; read -n 1 -s -r -p "Touche pour fermer…"; exit 1; }
  echo "Création de l'environnement avec $PY"
  "$PY" -m venv .venv || exit 1
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt || { echo "Installation échouée."; read -n 1 -s -r -p "Touche pour fermer…"; exit 1; }
  .venv/bin/python -m playwright install chromium
fi

.venv/bin/python maj_eleveurs.py || echo "(Liste des éleveurs non mise à jour : eleveurs.js existant conservé)"
# libère le port si une ancienne instance tourne encore
lsof -ti tcp:8770 | xargs kill 2>/dev/null; sleep 1
exec .venv/bin/python serveur.py
