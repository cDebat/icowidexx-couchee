#!/bin/bash
# Double-clic (macOS) : commit de toutes les modifications puis push sur GitHub.
# Usage en ligne de commande : ./Sauvegarder.command "message de commit clair"
cd "$(dirname "$0")" || exit 1
rm -f .git/stale-* 2>/dev/null
if [ -z "$(git status --porcelain)" ]; then
  echo "Rien à sauvegarder : tout est déjà commité."
else
  MSG="${1:-Mise à jour $(date '+%d/%m/%Y %H:%M')}"
  git add -A && git commit -m "$MSG" || exit 1
fi
git push -u origin "$(git branch --show-current)" && echo "✔ Sauvegardé sur GitHub." || echo "✘ Push impossible : vérifier la connexion / l'accès GitHub."
read -n 1 -s -r -p "Appuyez sur une touche pour fermer…"
