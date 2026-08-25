#!/usr/bin/env python3
"""
Marque dans le plan les séances réellement effectuées, d'après Strava.

Pourquoi : le visualiseur enregistre les cases cochées dans le localStorage du
navigateur — isolé et peu fiable sur un fichier file://, et perdu à chaque
régénération. Or l'information existe déjà : si une activité Strava correspond
à une séance prévue le même jour, la séance est faite. On n'a rien à cocher.

À lancer APRÈS generate_plan.py (qui réécrit le plan de zéro) et AVANT le rendu.

Usage : python3 harness/marquer_realise.py
"""

import json, glob
from pathlib import Path

def _exiger(chemin, quoi, remede):
    """A missing file must produce a sentence, not a Python traceback.
    This is often the first thing a new user sees."""
    import sys
    if not Path(chemin).exists():
        sys.exit(f"\n  ✗ {quoi} not found.\n"
                 f"    Expected at: {chemin}\n"
                 f"    → {remede}\n")


BASE = Path(__file__).parent.parent
PLAN = BASE / "build" / "plan.json"

COURSE = ("run", "trailrun", "race")
RENFO = ("weighttraining", "workout", "strengthtraining", "crossfit", "hiit")
VELO = ("ride", "virtualride", "ebikeride")

def famille(t):
    t = (t or "").lower()
    return "run" if t in COURSE else "strength" if t in RENFO else "bike" if t in VELO else None

# --- activités réelles, indexées par (date, famille) ---
reel = {}
for f in sorted(glob.glob(str(BASE / "suivi" / "semaine-*-strava.json"))):
    for a in json.loads(Path(f).read_text(encoding="utf-8")):
        fam = famille(a.get("type"))
        if fam and a.get("date"):
            reel.setdefault((a["date"], fam), []).append(a)

_exiger(PLAN, "The training plan", "run ./harness/relancer.sh --plan 1")

plan = json.loads(PLAN.read_text(encoding="utf-8"))
faites = rendues = 0

# Le renfo est explicitement DÉPLAÇABLE dans la semaine : l'apparier sur la date
# exacte le rendrait invisible dès qu'il bouge d'un jour. On l'apparie donc à la
# semaine. Les courses, elles, sont ancrées à leur jour.
FLEXIBLE = ("strength",)

def semaine_de(d):
    from datetime import date, timedelta
    x = date.fromisoformat(d)
    return (x - timedelta(days=x.weekday())).isoformat()

reel_semaine = {}
for (d, fam), acts in reel.items():
    reel_semaine.setdefault((semaine_de(d), fam), []).extend(acts)
consommees = set()

for semaine in plan["weeks"]:
    for jour in semaine["days"]:
        for w in jour["workouts"]:
            fam = "run" if w["sport"] in ("run", "race") else w["sport"]
            if fam in FLEXIBLE:
                cle = (semaine_de(jour["date"]), fam)
                dispo = [a for a in reel_semaine.get(cle, [])
                         if id(a) not in consommees]
                candidates = dispo[:1]
                if candidates:
                    consommees.add(id(candidates[0]))
            else:
                candidates = reel.get((jour["date"], fam), [])
            deja = w.get("completed")
            if candidates and not deja:
                a = candidates[0]
                w["completed"] = True
                w["completedAt"] = a.get("debut") or jour["date"]
                if a.get("distance_km"):
                    w["actualDistance"] = round(a["distance_km"] * 1000)
                if a.get("moving_time_s"):
                    w["actualDuration"] = round(a["moving_time_s"] / 60)
                ecart = ""
                if a.get("distance_km") and w.get("distanceMeters"):
                    d = a["distance_km"] * 1000 - w["distanceMeters"]
                    ecart = f"  ({d/1000:+.1f} km vs prévu)"
                decale = ""
                if a.get("date") and a["date"] != jour["date"]:
                    decale = f"  [fait le {a['date']}, prévu le {jour['date']}]"
                print(f"  ✓ {jour['date']}  {w['name'][:40]:<40}{ecart}{decale}")
                rendues += 1
            if w.get("completed"):
                faites += 1

PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

total = sum(1 for s in plan["weeks"] for j in s["days"] for w in j["workouts"]
            if w["sport"] not in ("rest",))
print(f"\n  {rendues} séance(s) nouvellement marquée(s) · {faites}/{total} faites au total "
      f"({faites/total*100:.0f} %)")
