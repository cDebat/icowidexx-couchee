# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Projet : iCowIdexx_Couchee — bilan sanguin d'une vache couchée (résultats IDEXX → rapport éleveur)

Petite appli locale (une page HTML + un serveur Python minimal) : on charge le compte rendu IDEXX Catalyst One d'une vache couchée (PDF/photo, minimum Ca + P ; CK, PT, ALB facultatifs), l'appli lit les valeurs, retrouve l'éleveur dans le listing, calcule le rapport albumine/globulines (AGR) et produit un rapport PDF de 2 pages pour l'éleveur.

Langue du projet : français (interface, commentaires, textes du rapport). Auteur : Dr Cédric Debattice, SAS Vétérinaires de l'Arguenon (Plancoët).

## Commandes

```bash
# Double-clic macOS : crée .venv au premier lancement, régénère eleveurs.js, lance le serveur et ouvre le navigateur
./Lancer_Bilan.command

# Équivalent manuel
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && playwright install chromium   # une fois
python3 maj_eleveurs.py          # listing Excel -> eleveurs.js (à relancer quand le listing change)
python3 serveur.py               # http://127.0.0.1:8770  (--no-browser pour ne pas ouvrir le navigateur)
```

Il n'y a ni tests automatisés ni linter. Pour vérifier un changement : lancer `serveur.py`, charger `Archives/Gaec La vIlle TANET - Vache 2662.pdf` et contrôler Ca 51 mg/L → 1,27 mmol/L, P 29,24 mg/L → 0,94, CK 6233, PT 84, ALB 31, AGR 0,58, élevage GAEC LA VILLE TANET (EDE 22323097), puis générer le rapport.

## Organisation

- `bilan-vache-couchee.html` : toute l'appli (HTML + CSS + JS vanilla, sans build). Bibliothèques par CDN : pdf.js 3.11.174, Tesseract.js 5.1.1 (langue `fra`), SheetJS 0.18.5 → **connexion Internet requise** au chargement.
- `serveur.py` : sert la page et `eleveurs.js` sur 127.0.0.1:8770 ; `POST /sauver` génère le PDF (Playwright/Chromium, A4, `print_background`) dans `Output/<n° EDE>/Bilan_vache_<animal>_<date>.pdf`. `GET /ping` sert à la page pour savoir si le bouton « Enregistrer dans Output » doit apparaître (ouverte en `file://`, seule l'impression navigateur est possible).
- `maj_eleveurs.py` : lit `Listing complet éleveurs - BSE 2026.xlsx` et écrit `eleveurs.js` (`window.ELEVEURS=[{num,nom,commune,tel,mail}]`).
- `Output/<EDE>/` : rapports générés. `Archives/` : comptes rendus IDEXX d'origine. Ces deux dossiers, le listing Excel et `eleveurs.js` (données personnelles) sont **ignorés par git**.

## Listing éleveurs

Colonnes du listing : A n° d'atelier (EDE), B Établissement, C Commune de l'atelier, D Catégorie d'atelier, E Téléphone 1, F Téléphone 2, G Email. Un élevage a parfois plusieurs ateliers (même EDE, lignes multiples) → une seule entrée par EDE. Téléphone retenu : **un portable (06/07) en priorité**, sinon le fixe. Pas d'adresse postale dans le listing (le rapport affiche EDE, commune, téléphone, mail).

**Piège** : le « Client : LA VILLE TANET (38654272) » du compte rendu IDEXX est le n° client IDEXX, **pas** le n° EDE (La Ville Tanet = EDE 22323097). L'élevage est donc retrouvé par le **nom** (mots du libellé IDEXX, hors EARL/GAEC/SCEA…) ; plusieurs correspondances → liste à choisir, aucune → recherche manuelle.

## Architecture de l'appli (JS)

- Lecture : `fileToCanvas` (PDF → canvas via pdf.js ; texte du PDF si présent, sinon OCR) → `prep` (recadrage colonne gauche 6–52 % de la largeur, niveaux de gris + autocontraste 2 %) → Tesseract `fra`, PSM 6 → `parseText` (par code d'analyse PT/TP, CK, PHOS/IP, Ca, ALB, Mg, AST, GGT, GLU, CREA, CHOL, TBIL : **première** valeur + unité après le code ; les intervalles imprimés par IDEXX, calibrés cheval, sont ignorés). Le n° de l'animal est manuscrit : saisie manuelle. L'utilisateur vérifie toujours le tableau des valeurs.
- `PARAMS` : paramètres, unités acceptées et facteurs de conversion vers mmol/L (Ca mg/L ÷ 40,08 ; P mg/L ÷ 30,97 ; etc.).
- `level(k,x,v)` : seuils BoviLab / Rumexperts (aide-mémoire V2) : Ca < 2,15 bas (≤ 1,5 très bas) ; P < 1,3 ; Mg < 0,65 bas / 0,65–0,8 limite ; CK 40–180 U/L ; PT 68–88 ; ALB 30–43 ; globulines 31–47 ; AGR normal 0,84–0,94, < 0,7 bas (inflammation), > 1,2 élevé.
- `gen()` : génère les textes (résumé, interprétation AGR, analyse, actions vétérinaire/élevage, pronostic) ; champs éditables, `state.dirty` empêche d'écraser une modification manuelle, « Régénérer » force.
- `buildReport()` : rapport A4 dans `#paper` (table `thead`/`tfoot` répétés par page ; ordre voulu par l'utilisateur : identité → contexte → **Résultats** (ligne AGR surlignée) → Lecture du rapport A/G (jauge) → Interprétation des indicateurs → **À retenir** → Plan d'action (vétérinaire / élevage) → pronostic ; 2 pages A4). Impression navigateur (`window.print`) ou serveur.
- Base éleveurs : `eleveurs.js` chargé par `<script>` ; à défaut, import manuel d'un .xlsx (SheetJS, colonnes détectées par en-tête, modifiables) mémorisé en `localStorage`.
- Réglages cabinet (nom, vétérinaire, adresse, téléphone de l'en-tête) en `localStorage`.

## Conventions

- Sauvegarde : après chaque modification significative, commiter (message clair, en français) et pousser sur GitHub (`origin` = https://github.com/cDebat/icowidexx-couchee, branche `main`). `./Sauvegarder.command "message"` (ou double-clic) fait `git add -A`, commit et push. Claude Code doit commiter à chaque lot de modifications, puis lancer le push ou rappeler à l'utilisateur de le faire.
- Valeurs de référence : toujours celles du référentiel BoviLab / Rumexperts (jamais les intervalles imprimés par IDEXX).
- Les textes du rapport sont indicatifs et à valider par le vétérinaire ; analyse d'un seul animal, à croiser avec l'examen clinique.

## Déploiement serveur (VPS Hostinger, https://idexx.primholstein.eu)
- `Dockerfile` + `deploy/docker-compose.yml` : conteneur `icowidexx` derrière le Traefik du VPS (HTTPS Let's Encrypt, résolveur `mytlschallenge`), mot de passe commun via basic-auth Traefik (`IDEXX_BASICAUTH` dans `deploy/.env`, jamais sur GitHub).
- Mode serveur : `SERVER_MODE=1`, `HOST`, `PORT`, `DATA_DIR` (volume `/data`), `NO_SANDBOX=1`. Le bouton « Quitter » n'arrête pas l'appli en mode serveur.
- `dbx.py` (stdlib) : envoi des PDF dans `DROPBOX_BASE/Output/<EDE>/` et lecture du listing `Listing complet*.xlsx` dans `DROPBOX_BASE` (synchro au démarrage puis toutes les 6 h ; `GET /maj-eleveurs` pour forcer). Secrets `DROPBOX_APP_KEY/SECRET/REFRESH_TOKEN` : `/opt/apps/secrets/dropbox.env` sur le VPS (root, 600), jamais dans le dépôt.
- Dépôt cloné sur le VPS dans `/opt/apps/icowidexx` (clé de déploiement GitHub en lecture seule). Mise à jour : `cd /opt/apps/icowidexx && git pull && cd deploy && docker compose up -d --build`.
- `maj_eleveurs.convertir(xlsx, dest)` est réutilisé par le serveur ; le script reste utilisable en ligne de commande.
