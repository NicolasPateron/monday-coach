#!/usr/bin/env python3
"""Zips des séances Garmin. À lancer APRÈS gen-fit.ts, qui n'écrit que les .fit.

Deux archives :
  garmin-fit.zip            — les 87 séances, pour archive
  garmin-fit-a-charger.zip  — les 4 prochaines semaines seulement

La seconde existe parce que déposer 87 fichiers dans GARMIN/NewFiles remplit la
liste Entraînements de la montre de séances de février qu'il ne fera pas avant
six mois. On ne charge que ce qui sert.
"""
import re, sys, zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "garmin-fit"
sem = int(sys.argv[1]) if len(sys.argv) > 1 else 1
FENETRE = 4

fichiers = sorted(SRC.glob("*.fit"))
if not fichiers:
    sys.exit("Aucun .fit — lancer gen-fit.ts d'abord.")

with zipfile.ZipFile(BASE / "garmin-fit.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in fichiers:
        z.write(f, f.name)

def numero(nom):
    m = re.match(r"S(\d+)_", nom)
    return int(m.group(1)) if m else None

proches = [f for f in fichiers
           if (n := numero(f.name)) is not None and sem <= n < sem + FENETRE]
cible = BASE / "garmin-fit-a-charger.zip"
with zipfile.ZipFile(cible, "w", zipfile.ZIP_DEFLATED) as z:
    for f in proches:
        z.write(f, f.name)

print(f"garmin-fit.zip : {len(fichiers)} séances")
print(f"garmin-fit-a-charger.zip : {len(proches)} séances (S{sem} à S{sem + FENETRE - 1})")
for f in proches:
    print(f"   {f.name}")
