#!/bin/bash
# First-run setup. Creates the working directories and files the harness expects,
# none of which are committed because they hold personal data.
#
#   ./harness/init.sh
#
# Safe to re-run: nothing existing is overwritten.
set -e
cd "$(dirname "$0")/.."

created=0
note() { printf '  %s %s\n' "$1" "$2"; }

echo "Monday Coach — first-run setup"
echo

for d in build suivi garmin-export garmin-export/raw garmin-fit; do
  if [ -d "$d" ]; then note "·" "$d already there"
  else mkdir -p "$d"; note "+" "$d"; created=$((created+1)); fi
done

if [ -f harness/athlete.json ]; then
  note "·" "harness/athlete.json already there"
else
  cp harness/athlete.example.json harness/athlete.json
  note "+" "harness/athlete.json  ← EDIT THIS ONE"
  created=$((created+1))
fi

if [ -f poids.csv ]; then
  note "·" "poids.csv already there"
else
  printf 'date,kg,note\n' > poids.csv
  note "+" "poids.csv (date,kg,note — one line per weigh-in)"
  created=$((created+1))
fi

if [ -f garmin-export/chaussures.json ]; then
  note "·" "garmin-export/chaussures.json already there"
else
  cat > garmin-export/chaussures.json <<'JSON'
{
  "_note": "Hand-edited. One entry per pair. `km_max` is the replacement threshold you set in Garmin; `principale: true` marks the pair currently accruing kilometres. Claude fills this in from your Garmin export at setup step 5 — these are placeholders.",
  "releve_le": "2026-01-01",
  "arrete_le": "2026-01-01",
  "paires": [
    { "nom": "Your road shoes", "usage": "route", "statut": "active",
      "depuis": "2026-01-01", "km_garmin": 0, "km_max": 800,
      "derniere_sortie": null, "activites": 0, "principale": true }
  ]
}
JSON
  note "+" "garmin-export/chaussures.json (placeholder)"
  created=$((created+1))
fi

echo
if [ "$created" -eq 0 ]; then
  echo "Nothing to do — already set up."
else
  echo "Next:"
  echo "  1. Edit harness/athlete.json — your race, target and measured values."
  echo "  2. npm install                — the viewer and the FIT exporter need it."
  echo "  3. ./harness/relancer.sh --plan 1"
  echo
  echo "  Full walkthrough: README.md → Setup"
fi
