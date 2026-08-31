#!/usr/bin/env python3
"""FC le matin contre FC le soir, à effort égal.

Question posée par l'athlète le 23/08/2026 : « en courant le matin, ma FC est plus
basse qu'en courant le soir, à effort identique. Possible ou simple impression ? »

Le piège est immédiat : en été, courir le matin c'est courir 10 °C plus frais, et
la chaleur élève la FC d'environ 0,65 bpm/°C. Sans correction thermique, on
mesurerait la météo en croyant mesurer un rythme circadien.

Ce script sépare les deux. Il compare l'indice d'efficience (vitesse/FC) brut ET
corrigé de la température. L'écart qui SURVIT à la correction est le seul candidat
sérieux à un effet du moment de la journée.

Il se renforce chaque semaine : lancé après chaque `relancer.sh`, il accumule les
sorties et n'affiche une conclusion que lorsque l'échantillon la porte.

    python3 harness/moment_journee.py
"""
import glob, json, sys
from pathlib import Path
from statistics import mean, stdev

BASE = Path(__file__).resolve().parent.parent
TEMP_REF, COEF_TEMP = 15, 0.65

# Bornes en heure locale de début de sortie.
CRENEAUX = [("matin", 4, 12), ("midi", 12, 16), ("soir", 16, 24)]
# En dessous, on ne conclut pas : on affiche et on attend.
MINI_PAR_GROUPE = 5


def fc_corrigee(hr, temp_c):
    if temp_c is None or temp_c <= TEMP_REF:
        return hr
    return hr - COEF_TEMP * (temp_c - TEMP_REF)


def creneau(debut):
    h = int(str(debut)[11:13])
    for nom, lo, hi in CRENEAUX:
        if lo <= h < hi:
            return nom
    return "soir"


def charger():
    """Sorties de course en endurance uniquement (FC 125-158) : comparer un
    fractionné à une sortie facile ne dirait rien du moment de la journée."""
    out = []
    for f in sorted(glob.glob(str(BASE / "suivi" / "semaine-*-strava.json"))):
        for a in json.loads(Path(f).read_text(encoding="utf-8")):
            hr, t, d = a.get("avg_hr"), a.get("moving_time_s"), a.get("distance_km")
            if a.get("type") not in ("Run", "TrailRun") or not (hr and t and d):
                continue
            if not 125 <= hr <= 158 or not a.get("debut"):
                continue
            vitesse = d * 1000 / (t / 60)
            out.append({
                "date": a["date"], "debut": a["debut"], "creneau": creneau(a["debut"]),
                "km": d, "allure_s": t / d, "fc": hr, "temp": a.get("temp_c"),
                "denivele": a.get("denivele_m"),
                "ef_brut": vitesse / hr,
                "ef_corrige": vitesse / fc_corrigee(hr, a.get("temp_c")),
            })
    return out


def allure_a_145(ef):
    return 1000 / (ef * 145) * 60


def fmt(s):
    return f"{int(s)//60}:{int(s) % 60:02d}"


def main():
    runs = charger()
    if not runs:
        sys.exit("Aucune sortie exploitable.")

    print("=" * 78)
    print("  FC MATIN CONTRE FC SOIR — à effort égal, correction thermique appliquée")
    print("=" * 78)
    print(f"\n{'date':11} {'h':>3} {'créneau':8} {'km':>5} {'allure':>7} {'FC':>5} "
          f"{'°C':>5} {'EF brut':>8} {'EF corr':>8}")
    for r in sorted(runs, key=lambda x: x["date"]):
        t = f"{r['temp']:.0f}" if r["temp"] is not None else "—"
        print(f"{r['date']} {r['debut'][11:13]:>3} {r['creneau']:8} {r['km']:5.1f} "
              f"{fmt(r['allure_s']):>7} {r['fc']:5.1f} {t:>5} "
              f"{r['ef_brut']:8.3f} {r['ef_corrige']:8.3f}")

    groupes = {}
    for r in runs:
        groupes.setdefault(r["creneau"], []).append(r)

    print(f"\n{'créneau':8} {'n':>3} {'°C moy':>7} {'EF brut':>9} {'EF corrigé':>11} "
          f"{'allure à 145 bpm':>18}")
    print("-" * 78)
    for nom, _, _ in CRENEAUX:
        g = groupes.get(nom)
        if not g:
            continue
        temps = [r["temp"] for r in g if r["temp"] is not None]
        eb, ec = mean(r["ef_brut"] for r in g), mean(r["ef_corrige"] for r in g)
        print(f"{nom:8} {len(g):3} {mean(temps) if temps else 0:7.1f} {eb:9.3f} "
              f"{ec:11.3f} {fmt(allure_a_145(ec)):>15}/km")

    m, s = groupes.get("matin", []), groupes.get("soir", [])
    print("\n" + "-" * 78)
    if not m or not s:
        print("Pas encore de comparaison possible : il manque un créneau.")
        return
    eb = (mean(r["ef_brut"] for r in m) / mean(r["ef_brut"] for r in s) - 1) * 100
    ec = (mean(r["ef_corrige"] for r in m) / mean(r["ef_corrige"] for r in s) - 1) * 100
    dt = mean([r["temp"] for r in s if r["temp"] is not None] or [0]) - \
         mean([r["temp"] for r in m if r["temp"] is not None] or [0])
    print(f"Écart brut matin vs soir      : {eb:+.1f} %  (le matin est {dt:.1f} °C plus frais)")
    print(f"Part expliquée par la météo   : {eb - ec:+.1f} %")
    print(f"ÉCART RÉSIDUEL                : {ec:+.1f} %  ← le seul candidat à un effet horaire")
    if ec > 0:
        print(f"                                soit environ {ec / 100 * 145:.1f} bpm à 145 bpm")

    n = min(len(m), len(s))
    print()
    if n < MINI_PAR_GROUPE:
        print(f"⚠️  ÉCHANTILLON INSUFFISANT — {len(m)} sortie(s) le matin, {len(s)} le soir.")
        print(f"    Il en faut au moins {MINI_PAR_GROUPE} par créneau avant de conclure quoi que")
        print("    ce soit. Le chiffre ci-dessus est affiché pour être suivi, pas pour décider.")
    else:
        for nom, g in (("matin", m), ("soir", s)):
            if len(g) > 1:
                print(f"    dispersion {nom} : ±{stdev(r['ef_corrige'] for r in g):.3f} (n={len(g)})")
        print("    Comparer l'écart résiduel à la dispersion : s'il est plus petit, c'est du bruit.")


if __name__ == "__main__":
    main()
