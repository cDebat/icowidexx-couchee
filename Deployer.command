#!/bin/bash
# Double-clic (macOS) : sauvegarde sur GitHub PUIS met à jour le serveur Hostinger (https://idexx.primholstein.eu).
# Usage en ligne de commande : ./Deployer.command "message de commit clair"
cd "$(dirname "$0")" || exit 1
CLE="$HOME/.ssh/id_ed25519_primholstein"
SERVEUR="root@77.37.120.95"
URL="https://idexx.primholstein.eu/"
fin() { read -n 1 -s -r -p "Appuyez sur une touche pour fermer…"; exit "${1:-0}"; }

# 0) Première utilisation : création de la clé SSH (une seule fois)
if [ ! -f "$CLE" ]; then
  mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
  ssh-keygen -t ed25519 -N "" -C "mac-cedric-deploiement" -f "$CLE" >/dev/null
  echo "Clé SSH créée. Voici la clé PUBLIQUE à transmettre à Claude (sans danger à partager) :"
  echo; cat "$CLE.pub"; echo
  echo "→ Copiez la ligne ci-dessus dans la conversation, puis relancez ce script quand Claude confirme."
  fin 0
fi

# 1) Sauvegarde GitHub
rm -f .git/stale-* 2>/dev/null
if [ -z "$(git status --porcelain)" ]; then
  echo "Rien de nouveau à commiter."
else
  MSG="${1:-Mise à jour $(date '+%d/%m/%Y %H:%M')}"
  git add -A && git commit -m "$MSG" || fin 1
fi
git push -u origin "$(git branch --show-current)" || { echo "✘ Push GitHub impossible : serveur non mis à jour."; fin 1; }
echo "✔ Sauvegardé sur GitHub."

# 2) Mise à jour du serveur
echo "→ Mise à jour du serveur : reconstruction en cours, comptez 1 à 3 minutes (rien ne s'affiche pendant ce temps, c'est normal)…"
ssh -i "$CLE" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o BatchMode=yes -o ConnectTimeout=15 "$SERVEUR" \
  'cd /opt/apps/icowidexx && git pull --ff-only && cd deploy && docker compose up -d --build 2>&1 | tail -5 && docker ps --format "{{.Names}} {{.Status}}" | grep icowidexx' \
  || { echo "✘ Mise à jour du serveur impossible (clé SSH non autorisée ? serveur injoignable ?)."; fin 1; }

# 3) Vérification
sleep 5
CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$URL")
if [ "$CODE" = "401" ] || [ "$CODE" = "200" ]; then echo "✔ Site en ligne ($URL, code $CODE)."; else echo "⚠ Le site répond avec le code $CODE : à vérifier."; fi
fin 0
