#!/usr/bin/env python3
"""
Renseigne automatiquement la température de chaque séance.

Pourquoi : la chaleur élève la FC à effort constant (~0,65 bpm/°C au-dessus de 15 °C).
Sans correction, l'allure à 145 bpm s'améliorerait mécaniquement d'août à mars —
un artefact saisonnier pris pour un progrès. La montre de Nicolas n'enregistre pas
la température, et la demander à chaque séance est une dépendance manuelle qui
finirait par lâcher. On la récupère donc seule.

Confidentialité : coordonnées arrondies au niveau de la ville (Paris, 48.85/2.35).
Aucune donnée personnelle, aucun identifiant, aucune coordonnée de domicile n'est
transmise. Service Open-Meteo, sans clé d'API.

Usage : python3 harness/meteo.py 1        # complète suivi/semaine-01-strava.json
"""

import json, sys, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent
CACHE = BASE / "suivi" / "meteo-cache.json"
# Coordonnées de repli, utilisées seulement si la séance n'en porte pas.
# Le 25/08/2026, ce repli en dur a donné 28,5 °C (Paris) pour une sortie courue
# à 150 km de là, où il faisait 24,6 : l'indice d'efficience s'en trouvait faussé
# de près de 4 °C, soit 2,5 bpm de correction en trop.
LAT_DEFAUT, LON_DEFAUT = 48.85, 2.35
TZ = "Europe/Paris"

def _lieu(activite):
    """Coordonnées de la séance, arrondies au dixième de degré (~11 km).
    Assez précis pour la météo, trop grossier pour situer un domicile."""
    lat = activite.get("lat")
    lon = activite.get("lon")
    if lat is None or lon is None:
        return LAT_DEFAUT, LON_DEFAUT
    return round(float(lat), 1), round(float(lon), 1)

def _cache():
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

def temperature(debut_local: str, lat=None, lon=None):
    """Température à l'heure ET au lieu de la séance."""
    LAT = LAT_DEFAUT if lat is None else lat
    LON = LON_DEFAUT if lon is None else lon
    heure = debut_local[:13] + ":00"
    cle = f"{heure}@{LAT},{LON}"          # le cache doit distinguer les lieux
    c = _cache()
    if cle in c:
        return c[cle]
    for url in (
        f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}"
        f"&hourly=temperature_2m&past_days=92&forecast_days=1&timezone={TZ}",
        f"https://archive-api.open-meteo.com/v1/archive?latitude={LAT}&longitude={LON}"
        f"&start_date={debut_local[:10]}&end_date={debut_local[:10]}"
        f"&hourly=temperature_2m&timezone={TZ}",
    ):
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                h = json.load(r).get("hourly", {})
            if heure in h.get("time", []):
                t = h["temperature_2m"][h["time"].index(heure)]
                if t is not None:
                    c[cle] = t
                    CACHE.parent.mkdir(exist_ok=True)
                    CACHE.write_text(json.dumps(c, indent=2), encoding="utf-8")
                    return t
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            continue
    return None

def enrichir(semaine: int) -> int:
    f = BASE / "suivi" / f"semaine-{semaine:02d}-strava.json"
    if not f.exists():
        print(f"  {f.name} : absent")
        return 0
    acts = json.loads(f.read_text(encoding="utf-8"))
    n = 0
    for a in acts:
        if a.get("temp_c") is not None:
            continue
        debut = a.get("debut") or (a.get("date", "") + "T12:00")
        lat, lon = _lieu(a)
        t = temperature(debut, lat, lon)
        if t is not None:
            a["temp_c"] = t
            a["temp_lieu"] = f"{lat},{lon}"     # trace : d'où vient la mesure
            n += 1
            print(f"  {debut[:16]}  {a.get('name','')[:34]:<34} {t:>5.1f} °C")
        else:
            print(f"  {debut[:16]}  {a.get('name','')[:34]:<34}     — (indisponible)")
    if n:
        f.write_text(json.dumps(acts, ensure_ascii=False, indent=2), encoding="utf-8")
    return n

if __name__ == "__main__":
    s = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(f"Températures — semaine {s}")
    print(f"  {enrichir(s)} séance(s) complétée(s)")
