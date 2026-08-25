#!/usr/bin/env python3
"""
Tableau de bord multifactoriel — marathon build

Croise quatre sources :
  - le plan          (marathon-rome-2027-03-14.json)
  - le réel course   (suivi/semaine-XX-strava.json, écrit par la tâche du lundi depuis le MCP Strava)
  - le bien-être     (garmin-export/wellness-daily.json, produit par extract_garmin.py)
  - le poids         (poids.csv)

Produit : suivi/journal.json (cumulatif) + un tableau de bord console.

Usage :
    python3 dashboard.py            # semaine courante, déduite de la date
    python3 dashboard.py 3          # semaine 3 explicitement
"""

import csv, json, sys
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

BASE = Path(__file__).parent.parent
PLAN = BASE / "build" / "plan.json"
WELLNESS = BASE / "garmin-export" / "wellness-daily.json"
POIDS = BASE / "poids.csv"
SUIVI = BASE / "suivi"
JOURNAL = SUIVI / "journal.json"

PLAN_START = date(2026, 8, 17)
POIDS_DEPART = None   # déduit de la première ligne de poids.csv
POIDS_CIBLE = 80.6

# ---------------------------------------------------------------------------
# Trajectoire de poids : perte concentrée sur Reprise/Base/Développement,
# neutre pendant les fêtes, PUIS STABILISATION à partir de S23.
# Perdre du poids pendant le pic de charge (S25-S27, 57-60 km/sem) dégrade la
# récupération et augmente le risque de blessure : l'objectif doit être atteint AVANT.
# ---------------------------------------------------------------------------
def poids_cible(semaine: int) -> float:
    paliers = [(4, 0.50), (12, 0.55), (18, 0.45), (20, 0.00), (22, 0.45)]
    p, s = POIDS_DEPART, 0
    for fin, taux in paliers:
        n = max(0, min(semaine, fin) - s)
        p -= n * taux
        s = fin
    return round(p, 1)   # au-delà de S22 : stabilisation, la valeur ne bouge plus

def semaine_de(d: date) -> int:
    return max(1, min(30, (d - PLAN_START).days // 7 + 1))

def lundi_de(semaine: int) -> date:
    return PLAN_START + timedelta(weeks=semaine - 1)

# ---------------------------------------------------------------------------
# Chargement des sources
# ---------------------------------------------------------------------------
def charge_plan(semaine):
    if not PLAN.exists():
        return None
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    w = next((x for x in plan["weeks"] if x["weekNumber"] == semaine), None)
    if not w:
        return None
    return {
        "phase": w["phase"], "focus": w["focus"], "recup": w["isRecoveryWeek"],
        "km_prevu": w["summary"]["bySport"]["run"]["km"],
        "seances_prevues": w["summary"]["bySport"]["run"]["sessions"],
    }

def charge_strava(semaine):
    f = SUIVI / f"semaine-{semaine:02d}-strava.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []

def charge_wellness(debut: date, fin: date):
    if not WELLNESS.exists():
        return []
    return [j for j in json.loads(WELLNESS.read_text(encoding="utf-8"))
            if debut.isoformat() <= j["date"] <= fin.isoformat()]

def charge_poids():
    if not POIDS.exists():
        return []
    with POIDS.open(encoding="utf-8") as f:
        return [(r["date"], float(r["kg"])) for r in csv.DictReader(f) if r.get("kg")]

# ---------------------------------------------------------------------------
# Indicateurs calculés
# ---------------------------------------------------------------------------
# La chaleur élève la FC à effort constant : sans correction, l'indice d'efficience
# s'améliorerait mécaniquement de l'été à l'hiver, ce qui serait un artefact saisonnier
# et non un progrès. Coefficient retenu : 0,65 bpm par °C au-dessus de 15 °C
# (milieu de la fourchette usuelle 0,5-0,8). C'est une ESTIMATION, pas une loi.
TEMP_REF = 15
COEF_TEMP = 0.65

def fc_corrigee(hr, temp_c):
    """FC ramenée à des conditions tempérées. Sans température connue, valeur brute."""
    if temp_c is None or temp_c <= TEMP_REF:
        return hr
    return hr - COEF_TEMP * (temp_c - TEMP_REF)

def indice_efficience(acts, corriger=True):
    """EF = vitesse (m/min) / FC moyenne, sur les sorties en endurance (FC 125-158).
    Il monte quand le moteur aérobie se construit."""
    vals = []
    for a in acts:
        hr, t, d = a.get("avg_hr"), a.get("moving_time_s"), a.get("distance_km")
        if hr and t and d and 125 <= hr <= 158:
            h = fc_corrigee(hr, a.get("temp_c")) if corriger else hr
            vals.append(round((d * 1000 / (t / 60)) / h, 3))
    return round(mean(vals), 3) if vals else None

def allure_a_fc(acts, fc_ref=145, corriger=True):
    """Allure extrapolée à FC constante (145 bpm), en s/km — comparable d'une semaine à l'autre."""
    ef = indice_efficience(acts, corriger)
    if not ef:
        return None
    return round(1000 / (ef * fc_ref) * 60)

def fmt_allure(sec):
    return f"{int(sec)//60}:{int(sec)%60:02d}/km" if sec else "—"

# ---------------------------------------------------------------------------
# Assemblage
# ---------------------------------------------------------------------------
semaine = int(sys.argv[1]) if len(sys.argv) > 1 else semaine_de(date.today())
debut, fin = lundi_de(semaine), lundi_de(semaine) + timedelta(days=6)

plan = charge_plan(semaine)
acts = charge_strava(semaine)
well = charge_wellness(debut, fin)
poids_log = charge_poids()

runs = [a for a in acts if a.get("type", "").lower() in ("run", "trailrun", "race")]
RENFO = ("weighttraining", "workout", "strengthtraining", "crossfit", "hiit")
renfo = [a for a in acts if a.get("type", "").lower() in RENFO]
km_reel = round(sum(a.get("distance_km", 0) for a in runs), 1)
ef = indice_efficience(runs)
fc_ef = [a["avg_hr"] for a in runs if a.get("avg_hr") and 125 <= a["avg_hr"] <= 158]

def moy(cle):
    # les nuits marquées non fiables (détection avortée, sieste fusionnée)
    # faussent les moyennes : on les écarte du calcul, sans les effacer
    src = [j for j in well if not (cle.startswith("sommeil") and j.get("sommeil_fiable") is False)]
    v = [j[cle] for j in src if j.get(cle) is not None]
    return round(mean(v), 1) if v else None

cible = poids_cible(semaine)
poids_actuel = poids_log[-1][1] if poids_log else None
ecart = round(poids_actuel - cible, 1) if poids_actuel else None

ligne = {
    "semaine": semaine, "debut": debut.isoformat(), "fin": fin.isoformat(),
    "phase": plan["phase"] if plan else None,
    "km_prevu": plan["km_prevu"] if plan else None, "km_reel": km_reel,
    "seances_prevues": plan["seances_prevues"] if plan else None, "seances_reelles": len(runs),
    "renfo_seances": len(renfo), "renfo_min": round(sum((a.get("moving_time_s") or 0) for a in renfo) / 60),
    "efficience": ef, "allure_a_145": allure_a_fc(runs),
    "efficience_brute": indice_efficience(runs, corriger=False),
    "allure_a_145_brute": allure_a_fc(runs, corriger=False),
    "temp_moy": round(mean([a["temp_c"] for a in runs if a.get("temp_c") is not None]), 1)
                if any(a.get("temp_c") is not None for a in runs) else None,
    "fc_moy_endurance": round(mean(fc_ef)) if fc_ef else None,
    "sommeil_min": moy("sommeil_min"), "sommeil_score": moy("sommeil_score"),
    "vfc": moy("vfc_nuit"), "fc_repos": moy("fc_repos"), "stress": moy("stress_moy"),
    "poids": poids_actuel, "poids_cible": cible, "ecart_poids": ecart,
}

SUIVI.mkdir(exist_ok=True)
hist = {j["semaine"]: j for j in (json.loads(JOURNAL.read_text(encoding="utf-8")) if JOURNAL.exists() else [])}
hist[semaine] = ligne
JOURNAL.write_text(json.dumps([hist[k] for k in sorted(hist)], ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------------------------------------------------------------------
# Affichage
# ---------------------------------------------------------------------------
prec = hist.get(semaine - 1)
def delta(cle, unite="", inv=False):
    if not prec or prec.get(cle) is None or ligne.get(cle) is None:
        return ""
    d = ligne[cle] - prec[cle]
    if abs(d) < 0.05:
        return "  ="
    fleche = "▲" if d > 0 else "▼"
    return f"  {fleche}{abs(d):.1f}{unite}"

print(f"\n{'='*70}")
print(f"  SEMAINE {semaine}/30 — {debut.strftime('%d/%m')} au {fin.strftime('%d/%m/%Y')}"
      + (f"  ·  {plan['phase']}" if plan else ""))
if plan:
    print(f"  {plan['focus']}")
print("=" * 70)

print("\nENTRAÎNEMENT")
if plan:
    taux = km_reel / plan["km_prevu"] * 100 if plan["km_prevu"] else 0
    print(f"  Volume            {km_reel:5.1f} km  /  {plan['km_prevu']:5.1f} prévu   ({taux:3.0f} %)")
    print(f"  Séances           {len(runs)} / {plan['seances_prevues']}")
else:
    print(f"  Volume            {km_reel:5.1f} km")
r = ligne["renfo_seances"]
print(f"  Renfo             {r} / 2 prévu" + (f"   ({ligne['renfo_min']} min)" if r else "")
      + ("   ⚠ aucune séance loguée" if r == 0 else ""))
print(f"  FC moy. endurance {ligne['fc_moy_endurance'] or '—'}{delta('fc_moy_endurance')}"
      + ("   ⚠ au-dessus de 150" if (ligne["fc_moy_endurance"] or 0) > 150 else ""))
t = ligne.get("temp_moy")
print(f"  Allure à 145 bpm  {fmt_allure(ligne['allure_a_145'])}{delta('allure_a_145',' s')}"
      "        ← indicateur clé du progrès aérobie")
if t is not None and t > 15:
    print(f"     dont brut      {fmt_allure(ligne['allure_a_145_brute'])}"
          f"   (corrigé de {t:.0f} °C : sans ça, l'été pénalise et l'hiver flatte)")
elif t is None:
    print("     ⚠ température inconnue — valeur non corrigée, comparaison saisonnière biaisée")
print(f"  Indice efficience {ligne['efficience'] or '—'}{delta('efficience')}")

print("\nRÉCUPÉRATION")
s = ligne["sommeil_min"]
print(f"  Sommeil           {int(s//60)}h{int(s%60):02d}" if s else "  Sommeil           —", end="")
print(f"{delta('sommeil_min',' min')}" + ("   ⚠ sous sa baseline de 7h31" if s and s < 420 else ""))
print(f"  Score sommeil     {ligne['sommeil_score'] or '—'}{delta('sommeil_score')}")
print(f"  VFC               {ligne['vfc'] or '—'} ms{delta('vfc',' ms')}"
      + ("   ⚠ sous la baseline (73)" if (ligne["vfc"] or 99) < 73 else ""))
print(f"  FC de repos       {ligne['fc_repos'] or '—'}{delta('fc_repos')}"
      + ("   ⚠ au-dessus de 52 (6 % des jours)" if (ligne["fc_repos"] or 0) > 52 else ""))

print("\nPOIDS")
if poids_actuel:
    perdu = round(POIDS_DEPART - poids_actuel, 1)
    reste = round(poids_actuel - POIDS_CIBLE, 1)
    etat = "dans les temps" if ecart <= 0.5 else f"en retard de {ecart:.1f} kg"
    print(f"  Actuel            {poids_actuel:.1f} kg{delta('poids',' kg')}   (cible S{semaine} : {cible:.1f} kg → {etat})")
    print(f"  Parcouru          −{perdu:.1f} kg  ·  reste {reste:.1f} kg jusqu'à {POIDS_CIBLE:.1f} kg")
    gain = round(perdu * 1.4)
    if gain:
        print(f"  Gain estimé       ≈ {gain} min sur marathon (~1,4 min/kg)")
else:
    print("  Aucune pesée enregistrée — ajoute une ligne dans poids.csv")
if semaine >= 23:
    print("  ⚠ PHASE DE STABILISATION : plus de déficit, la charge d'entraînement prime")

print(f"\n{'='*70}")
print(f"Journal : {JOURNAL.relative_to(BASE)}  ({len(hist)} semaine(s) enregistrée(s))\n")
