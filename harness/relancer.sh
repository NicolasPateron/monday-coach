#!/bin/bash
# Chaîne complète, dans le SEUL ordre valide. Voir docs/architecture.md.
#
# Le rendu du viewer doit venir APRÈS marquer_realise.py : generate_plan.py
# réécrit le plan de zéro et efface l'état `completed`. L'inversion a déjà fait
# retomber six semaines de progression visible à 0 %.
set -e
cd "$(dirname "$0")/.."          # racine du dépôt

echo "1/8  plan"
[ "$1" = "--plan" ] && python3 harness/generate_plan.py > /dev/null

echo "2/8  températures"
python3 harness/meteo.py "${2:-1}" > /dev/null

echo "3/8  validation des données"
python3 harness/valider.py > /dev/null || { echo "   ✗ ANOMALIE — arrêt"; exit 1; }

echo "4/8  tableau de bord"
python3 harness/dashboard.py "${2:-1}" > /dev/null
# Effet du moment de la journée sur la FC : le fichier s'enrichit chaque semaine,
# et le script refuse de conclure avant 5 sorties par créneau.
python3 harness/moment_journee.py > suivi/moment-journee.txt 2>&1 || true

echo "5/8  marquage des séances faites  →  rendu du viewer"
python3 harness/marquer_realise.py > /dev/null
npx tsx src/cli.ts render build/plan.json --output build/programme.html > /dev/null

echo "6/8  fichiers Garmin"
npx tsx gen-fit.ts > /dev/null
# gen-fit.ts écrit les .fit mais PAS les zips — un zip périmé fait charger
# d'anciennes séances dans la montre, sans qu'aucun contrôle ne le voie.
python3 harness/zip_fit.py "${2:-1}" > /dev/null

echo "7/8  support unique"
python3 harness/rapport.py | tail -1

echo "8/8  contrôle de synchronisation"
python3 harness/verifier_sync.py | tail -20
