#!/usr/bin/env python3
"""
Contrôle de fiabilité des extractions — à lancer après toute ingestion de données.

Motivation : trois conclusions fausses ont été tirées de données mal extraites
(sommeil sous-estimé de 4 h, FC de repos lue sur un champ de référence figé). Ces
erreurs n'ont été vues que parce que the athlete compared them to his own app. Ce script
remplace cette vérification manuelle.

Trois familles de tests :
  A. VARIANCE NULLE — un champ identique tous les jours est presque toujours le
     mauvais champ. C'est la signature exacte du bug `restingHeartRate` = 44 partout.
  B. COHÉRENCE INTERNE — bornes physiologiques, somme des phases ≤ durée, etc.
  C. RECOUPEMENT DE SOURCES — sur les jours couverts à la fois par l'export RGPD et
     par les zips quotidiens, les deux extractions doivent concorder.

Usage : python3 harness/valider.py
Code de sortie : 0 si tout passe, 1 s'il reste une anomalie bloquante.
"""

import json, sys
from pathlib import Path
from statistics import mean, median, pstdev

BASE = Path(__file__).parent.parent
SERIE = BASE / "garmin-export" / "wellness-daily.json"

d = json.loads(SERIE.read_text(encoding="utf-8"))
anomalies, avertissements = [], []

def vals(cle, sous_ensemble=None):
    src = sous_ensemble if sous_ensemble is not None else d
    return [x[cle] for x in src if x.get(cle) is not None]

# ---------------------------------------------------------------------------
# A. Variance nulle — détecte un champ de référence pris pour une mesure du jour
# ---------------------------------------------------------------------------
print("A. VARIANCE DES CHAMPS")
print("   champ                 n     min    méd    max   écart-type   verdict")
print("   " + "-" * 72)
attendu_variable = {
    "sommeil_min": 30, "fc_repos": 1.5, "vfc_nuit": 4,
    "pas": 800, "stress_moy": 3, "sommeil_score": 4,
}
for cle, seuil in attendu_variable.items():
    v = vals(cle)
    if len(v) < 10:
        print(f"   {cle:<20} {len(v):>3}   — trop peu de points pour juger")
        continue
    sd = pstdev(v)
    ok = sd >= seuil
    verdict = "ok" if ok else f"SUSPECT (attendu ≥ {seuil})"
    print(f"   {cle:<20} {len(v):>3}  {min(v):>6.0f} {median(v):>6.0f} {max(v):>6.0f}"
          f"   {sd:>8.1f}   {verdict}")
    if not ok:
        anomalies.append(f"{cle} : écart-type {sd:.1f} trop faible — champ probablement figé")

# ---------------------------------------------------------------------------
# B. Cohérence interne
# ---------------------------------------------------------------------------
print("\nB. COHÉRENCE INTERNE")
bornes = {"sommeil_min": (240, 720), "fc_repos": (35, 70), "vfc_nuit": (20, 200),
          "pas": (0, 55000), "stress_moy": (0, 100), "sommeil_score": (1, 100)}
for cle, (lo, hi) in bornes.items():
    hors = [(x["date"], x[cle]) for x in d
            if x.get(cle) is not None and not (lo <= x[cle] <= hi)]
    # Une valeur hors bornes DÉJÀ marquée non fiable est traitée, pas une anomalie :
    # ce sont de vrais artefacts de mesure (montre retirée, sieste fusionnée), pas
    # des erreurs d'extraction. Elles sont exclues des moyennes et des graphiques.
    non_traitees = [x for x in hors
                    if not (cle.startswith("sommeil")
                            and next((y.get("sommeil_fiable") for y in d if y["date"] == x[0]), None) is False)]
    marque = len(hors) - len(non_traitees)
    print(f"   {cle:<20} hors bornes [{lo}-{hi}] : {len(hors)}"
          + (f" (dont {marque} déjà marquée(s) non fiable(s))" if marque else "")
          + (f"   ex. {non_traitees[:3]}" if non_traitees else ""))
    if non_traitees:
        anomalies.append(f"{cle} : {len(non_traitees)} valeur(s) hors bornes NON traitée(s)")

# somme des phases ≤ durée totale (marge de 5 min pour les arrondis)
mauvais = []
for x in d:
    tot = x.get("sommeil_min")
    ph = [x.get(f"phase_{k}_min") for k in ("deep", "light", "rem")]
    if tot and all(p is not None for p in ph) and sum(ph) > tot + 5:
        mauvais.append((x["date"], sum(ph), tot))
print(f"   phases > durée totale : {len(mauvais)}" + (f"   ex. {mauvais[:3]}" if mauvais else ""))
if mauvais:
    anomalies.append(f"somme des phases > durée sur {len(mauvais)} jour(s)")

# Compteur de pas tronqué : `steps` est cumulé sur la journée et l'export s'arrête à
# l'heure du téléchargement. Un jour sans relevé de clôture de minuit ne porte donc
# qu'un compte partiel — 893 pas le 20/08/2026, jour d'une sortie de 6,7 km. Ce n'est
# pas une erreur d'extraction mais une limite de la source : on le signale sans
# bloquer, parce que les pas sont le signal d'alerte précoce le plus fiable et qu'un
# faux effondrement y coûte plus cher qu'une donnée manquante.
tronq = [x for x in d if x.get("pas_partiel")]
print(f"   pas tronqués (export du jour) : {len(tronq)}"
      + (f"   ex. {[(x['date'], x['pas'], x['pas_arret']) for x in tronq[-3:]]}" if tronq else ""))

# ---------------------------------------------------------------------------
# C. Recoupement des deux sources sur les jours communs
# ---------------------------------------------------------------------------
print("\nC. RECOUPEMENT DES DEUX SOURCES (jours couverts par les deux)")
# Ce test est le plus important : il compare, sur les mêmes jours, ce que donne
# l'export RGPD et ce que donnent les zips quotidiens. C'est lui qui aurait détecté
# seul les deux bugs de sommeil et de FC de repos.
import subprocess, tempfile

raw = BASE / "garmin-export" / "raw"
jours_zip = sorted(p.name for p in raw.iterdir() if p.is_dir()) if raw.exists() else []
rgpd = BASE / "garmin-export" / "_rgpd-reference.json"

if not rgpd.exists():
    avertissements.append(
        "pas de référence RGPD figée (_rgpd-reference.json) : recoupement impossible. "
        "La créer une fois avec import_garmin_historique.py --reference")
    print("   référence RGPD absente — test non exécuté")
elif not jours_zip:
    print("   aucun zip quotidien — test non exécuté")
else:
    ref = {x["date"]: x for x in json.loads(rgpd.read_text(encoding="utf-8"))}
    communs = [j for j in jours_zip if j in ref]
    print(f"   jours comparables : {len(communs)}")
    print("   jour         champ           RGPD      zip     écart")
    print("   " + "-" * 56)
    tolerances = {"sommeil_min": 15, "fc_repos": 1, "pas": 300, "stress_moy": 3}
    serie = {x["date"]: x for x in d}
    divergences = 0
    for jr in communs:
        for cle, tol in tolerances.items():
            a, b = ref[jr].get(cle), serie.get(jr, {}).get(cle)
            if a is None or b is None:
                continue
            if abs(a - b) > tol:
                divergences += 1
                print(f"   {jr}   {cle:<14} {a:>7.0f}  {b:>7.0f}   {b-a:+7.0f}  ✗")
    if divergences:
        anomalies.append(f"{divergences} divergence(s) entre les deux sources — une extraction est fausse")
    else:
        print("   aucune divergence au-delà des tolérances")

# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
if anomalies:
    print("ANOMALIES BLOQUANTES :")
    for a in anomalies:
        print("   ✗ " + a)
if avertissements:
    print("AVERTISSEMENTS :")
    for a in avertissements:
        print("   ! " + a)
if not anomalies and not avertissements:
    print("Tous les contrôles passent.")
print("=" * 78)
sys.exit(1 if anomalies else 0)
