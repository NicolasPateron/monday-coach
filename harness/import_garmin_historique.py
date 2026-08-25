#!/usr/bin/env python3
"""
Importe l'export Garmin complet (RGPD) et le fusionne avec le journal quotidien.

L'export complet couvre mai 2025 → aujourd'hui : sommeil, FC de repos, pas, stress,
VO2max, prédictions de course, charge d'entraînement. Il ne contient PAS la VFC —
celle-ci n'existe que dans les exports quotidiens (fichiers HRV_STATUS.fit).

Usage : python3 harness/import_garmin_historique.py <dossier_export>
Sortie : garmin-export/wellness-daily.json (fusionné) + garmin-export/performance.json
"""

import json, sys, glob, os
from datetime import datetime, date
from pathlib import Path
from statistics import mean

BASE = Path(__file__).parent.parent
SORTIE = BASE / "garmin-export" / "wellness-daily.json"
PERF = BASE / "garmin-export" / "performance.json"

if len(sys.argv) < 2:
    sys.exit("Usage : python3 harness/import_garmin_historique.py <dossier_export>")
RACINE = Path(sys.argv[1]).expanduser()

def charge(motif):
    """Charge et concatène tous les JSON correspondant au motif."""
    out = []
    for f in sorted(glob.glob(str(RACINE / "**" / motif), recursive=True)):
        try:
            d = json.load(open(f, encoding="utf-8"))
            out.extend(d if isinstance(d, list) else [d])
        except Exception:
            pass
    return out

def jour(v):
    """Normalise une date : ISO, ou epoch ms."""
    if isinstance(v, (int, float)):
        return datetime.utcfromtimestamp(v / 1000).date().isoformat()
    return str(v)[:10]

# ---------------------------------------------------------------------------
# Journal quotidien
# ---------------------------------------------------------------------------
jours = {}

def maj(d, **kv):
    jours.setdefault(d, {"date": d}).update({k: v for k, v in kv.items() if v is not None})

# --- Sommeil ---
for s in charge("*sleepData.json"):
    d = s.get("calendarDate")
    if not d:
        continue
    prof, leg, rem = (s.get("deepSleepSeconds") or 0), (s.get("lightSleepSeconds") or 0), (s.get("remSleepSeconds") or 0)
    # La durée retenue est la FENÊTRE de session (début → fin), la même métrique que
    # celle des zips quotidiens et que le « Durée » affiché par Garmin. Sommer
    # deep+light+rem donnerait le temps ENDORMI — une autre métrique, inférieure de
    # ~7 min en moyenne. Mélanger les deux dans une même série rendrait les récentes
    # semaines artificiellement meilleures.
    deb, fin = s.get("sleepStartTimestampGMT"), s.get("sleepEndTimestampGMT")
    total = None
    if deb and fin:
        d1 = datetime.strptime(deb[:19], "%Y-%m-%dT%H:%M:%S")
        d2 = datetime.strptime(fin[:19], "%Y-%m-%dT%H:%M:%S")
        if d2 > d1:
            total = round((d2 - d1).total_seconds() / 60)
            maj(d, coucher=d1.isoformat()[:16], lever=d2.isoformat()[:16])
    if not total:
        total = (prof + leg + rem) // 60          # repli si les horodatages manquent
    if total <= 0:
        continue
    maj(d, sommeil_min=total, sommeil_h=f"{total//60}h{total%60:02d}",
        phase_deep_min=prof // 60, phase_light_min=leg // 60, phase_rem_min=rem // 60,
        phase_awake_min=(s.get("awakeSleepSeconds") or 0) // 60,
        reveils=s.get("awakeCount"), respiration_moy=s.get("averageRespiration"),
        sommeil_score=(s.get("sleepScores") or {}).get("overallScore")
                      if isinstance(s.get("sleepScores"), dict) else s.get("overallSleepScore"))

# --- Résumés quotidiens : FC de repos, pas, stress, body battery ---
for u in charge("UDSFile*.json"):
    d = u.get("calendarDate")
    if not d:
        continue
    stress = None
    ads = u.get("allDayStress") or {}
    for a in (ads.get("aggregatorList") or []):
        if a.get("type") == "TOTAL":
            stress = a.get("averageStressLevel")
    bb = None
    for b in ((u.get("bodyBattery") or {}).get("bodyBatteryStatList") or []):
        if b.get("bodyBatteryStatType") == "HIGHEST":
            bb = b.get("statsValue")
    # `restingHeartRate` est une RÉFÉRENCE GLISSANTE (43-44 en permanence), pas la
    # mesure du jour. C'est `currentDayRestingHeartRate` qui correspond à l'app —
    # vérifié : 41 le 15/08, 44 le 17/08. Utiliser le premier a faussé 447 jours.
    maj(d, fc_repos=u.get("currentDayRestingHeartRate") or u.get("restingHeartRate"),
        pas=u.get("totalSteps"),
        stress_moy=stress if (stress is not None and stress >= 0) else None,
        body_battery_max=bb,
        minutes_intensite=(u.get("moderateIntensityMinutes") or 0) + 2 * (u.get("vigorousIntensityMinutes") or 0))

# --- Le dernier jour couvert est partiel : l'export s'arrête à l'heure de sa
# génération. Garder ses valeurs écraserait une journée complète par un fragment.
if jours:
    dernier = max(jours)
    jours[dernier]["partiel"] = True
    for cle in ("pas", "stress_moy", "minutes_intensite", "body_battery_max"):
        jours[dernier].pop(cle, None)
    print(f"  dernier jour ({dernier}) marqué partiel : compteurs de journée écartés")

# --- Référence RGPD isolée, pour le recoupement de valider.py ---
# Écrite AVANT toute fusion : c'est la sortie brute de cette source, indépendante
# des zips quotidiens. Sans elle, aucun recoupement n'est possible.
if "--reference" in sys.argv:
    ref = BASE / "garmin-export" / "_rgpd-reference.json"
    ref.write_text(json.dumps([jours[k] for k in sorted(jours)], ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"  référence RGPD figée : {len(jours)} jours → {ref.name}")

# --- Fusion avec l'existant (exports quotidiens : la VFC vient de là) ---
existant = {}
if SORTIE.exists():
    existant = {j["date"]: j for j in json.loads(SORTIE.read_text(encoding="utf-8"))}
for d, j in jours.items():
    existant.setdefault(d, {"date": d})
    for k, v in j.items():
        existant[d].setdefault(k, v)          # les exports quotidiens font foi
serie = [existant[k] for k in sorted(existant)]
SORTIE.parent.mkdir(parents=True, exist_ok=True)
SORTIE.write_text(json.dumps(serie, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------------------------------------------------------------------
# Performance : VO2max, prédictions, charge
# ---------------------------------------------------------------------------
vo2 = sorted(({"date": jour(v["calendarDate"]), "vo2max": v["vo2MaxValue"]}
              for v in charge("MetricsMaxMetData*.json")
              if v.get("vo2MaxValue") and v.get("sport") == "RUNNING"),
             key=lambda x: x["date"])
pred = sorted(({"date": jour(p["calendarDate"]), "10k": p.get("raceTime10K"),
                "semi": p.get("raceTimeHalf"), "marathon": p.get("raceTimeMarathon")}
               for p in charge("RunRacePredictions*.json") if p.get("raceTimeMarathon")),
              key=lambda x: x["date"])
charge_ent = sorted(({"date": jour(c["calendarDate"]), "aigue": c.get("dailyTrainingLoadAcute"),
                      "chronique": c.get("dailyTrainingLoadChronic"), "statut": c.get("acwrStatus")}
                     for c in charge("MetricsAcuteTrainingLoad*.json")),
                    key=lambda x: x["date"])
PERF.write_text(json.dumps({"vo2max": vo2, "predictions": pred, "charge": charge_ent},
                           ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------------------------------------------------------------------
# Chaussures : kilométrage cumulé et seuil de remplacement
# ---------------------------------------------------------------------------
CHAUSSURES = BASE / "garmin-export" / "chaussures.json"
gear_files = glob.glob(str(RACINE / "**" / "*_gear.json"), recursive=True)
if CHAUSSURES.exists():
    # Ce fichier est édité à la main (you reassign runs in Garmin, et
    # l'export RGPD est figé à sa date). L'écraser ferait perdre les corrections.
    print(f"  chaussures.json existe déjà — conservé (édition manuelle)")
    gear_files = []
if gear_files:
    g = json.load(open(gear_files[0], encoding="utf-8"))
    if isinstance(g, list):
        g = g[0]
    acts = []
    for f in glob.glob(str(RACINE / "**" / "*summarizedActivities.json"), recursive=True):
        a = json.load(open(f, encoding="utf-8"))
        if isinstance(a, list) and a and "summarizedActivitiesExport" in a[0]:
            a = a[0]["summarizedActivitiesExport"]
        acts.extend(a)
    par_id = {x["activityId"]: x for x in acts}

    paires = []
    for gd in g.get("gearDTOS", []):
        pk = str(gd["gearPk"])
        liees = [par_id[x["activityId"]] for x in g.get("gearActivityDTOs", {}).get(pk, [])
                 if x["activityId"] in par_id]
        km = sum((x.get("distance") or 0) for x in liees) / 100000      # centimètres → km
        derniere = max((datetime.utcfromtimestamp(x["startTimeLocal"] / 1000).date().isoformat()
                        for x in liees), default=None)
        paires.append({
            "nom": gd.get("customMakeModel", "Chaussure"),
            "type": gd.get("gearTypeName"),
            "statut": gd.get("gearStatusName"),
            "depuis": gd.get("dateBegin"),
            "km_garmin": round(km, 1),
            "km_max": round(gd["maximumMeters"] / 1000),
            "derniere_sortie": derniere,
            "activites": len(liees),
        })
    # La paire « principale » reçoit les kilomètres courus après l'export.
    # Choix : la chaussure de route la plus utilisée (le SpeedGoat est un modèle de trail).
    if paires:
        principale = max(paires, key=lambda p: p["activites"])
        for p in paires:
            p["principale"] = (p is principale)
    CHAUSSURES.write_text(json.dumps(
        {"arrete_le": max((p["derniere_sortie"] or "") for p in paires) or None, "paires": paires},
        ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------------------------------------------------------------------
# Restitution
# ---------------------------------------------------------------------------
def hms(s):
    s = int(s); return f"{s//3600}h{(s%3600)//60:02d}"

print(f"Journal fusionné : {len(serie)} jours ({serie[0]['date']} → {serie[-1]['date']})")
print(f"  dont avec sommeil : {sum(1 for j in serie if j.get('sommeil_min'))}"
      f" · FC repos : {sum(1 for j in serie if j.get('fc_repos'))}"
      f" · VFC : {sum(1 for j in serie if j.get('vfc_nuit'))}")
print(f"Performance : {len(vo2)} points VO2max · {len(pred)} prédictions · {len(charge_ent)} jours de charge\n")

# Synthèse mensuelle
print("Mois      Sommeil  FC rep  Stress    Pas   VO2max   Prédiction marathon")
print("-" * 74)
mois = {}
for j in serie:
    mois.setdefault(j["date"][:7], []).append(j)
vo2_m, pred_m = {}, {}
for v in vo2:
    vo2_m.setdefault(v["date"][:7], []).append(v["vo2max"])
for p in pred:
    pred_m.setdefault(p["date"][:7], []).append(p["marathon"])
for m in sorted(mois):
    js = mois[m]
    def moy(k):
        v = [x[k] for x in js if x.get(k) is not None]
        return mean(v) if v else None
    s, fc, st, pa = moy("sommeil_min"), moy("fc_repos"), moy("stress_moy"), moy("pas")
    v = mean(vo2_m[m]) if m in vo2_m else None
    pm = mean(pred_m[m]) if m in pred_m else None
    print(f"{m}   {f'{int(s//60)}h{int(s%60):02d}' if s else '   — ':>6}"
          f"  {f'{fc:.0f}' if fc else '—':>5}"
          f"  {f'{st:.0f}' if st else '—':>5}"
          f"  {f'{pa:.0f}' if pa else '—':>6}"
          f"  {f'{v:.1f}' if v else '—':>6}"
          f"   {hms(pm) if pm else '—':>8}")
