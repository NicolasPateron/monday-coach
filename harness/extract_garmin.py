#!/usr/bin/env python3
"""
Extrait les données de bien-être des exports quotidiens Garmin (.zip de fichiers .fit)
et produit un journal quotidien exploitable pour le suivi de la prépa marathon.

Usage :
    python3 extract_garmin.py ~/Downloads/2026-08-*.zip
    python3 extract_garmin.py            # relit tout ce qui est déjà dans garmin-export/raw/

Sortie : garmin-export/wellness-daily.json  +  récapitulatif console
"""

import json, re, subprocess, sys, zipfile
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")

BASE = Path(__file__).parent.parent
RAW = BASE / "garmin-export" / "raw"
OUT = BASE / "garmin-export" / "wellness-daily.json"
DECODER = BASE / "decode_fit.mjs"

# ---------------------------------------------------------------------------
# 1. Décompression des zips passés en argument
# ---------------------------------------------------------------------------
RAW.mkdir(parents=True, exist_ok=True)
for arg in sys.argv[1:]:
    p = Path(arg).expanduser()
    if not p.exists():
        print(f"  ! introuvable, ignoré : {p}")
        continue
    # Le nom peut porter un suffixe de retéléchargement ("2026-08-17-2.zip") :
    # on extrait la date, sinon le dossier créé corromprait l'entrée du journal.
    m = re.search(r"(\d{4}-\d{2}-\d{2})", p.stem)
    if not m:
        print(f"  ! nom de fichier sans date, ignoré : {p.name}")
        continue
    day = m.group(1)
    dest = RAW / day
    dest.mkdir(exist_ok=True)
    with zipfile.ZipFile(p) as z:
        z.extractall(dest)
    print(f"  + {day} ({len(list(dest.glob('*.fit')))} fichiers)")

# ---------------------------------------------------------------------------
# 2. Décodage FIT -> JSON via le SDK Garmin (Node)
# ---------------------------------------------------------------------------
DECODER.write_text("""
import { Decoder, Stream } from "@garmin/fitsdk";
import { readFileSync, readdirSync } from "node:fs";
const dir = process.argv[2];
const out = { sleepEvents: [], sleepLevels: [], hrData: [], monitoring: [], stress: [],
              respiration: [], hrvSummary: [], sleepAssessment: [] };
const iso = (t) => (t instanceof Date ? t.toISOString() : String(t));
for (const f of readdirSync(dir).filter((x) => x.endsWith(".fit"))) {
  try {
    const d = new Decoder(Stream.fromByteArray(new Uint8Array(readFileSync(dir + "/" + f))));
    const { messages } = d.read();
    const estSommeil = f.includes("SLEEP");
    // Les événements de session n'ont de sens que dans le fichier de sommeil :
    // les fichiers WELLNESS en contiennent d'autres, sans rapport.
    if (estSommeil)
      for (const e of messages.eventMesgs || [])
        out.sleepEvents.push({ t: iso(e.timestamp), type: e.eventType });
    for (const x of messages.sleepLevelMesgs || [])
      out.sleepLevels.push({ t: iso(x.timestamp), level: x.sleepLevel });
    for (const x of messages.sleepAssessmentMesgs || []) out.sleepAssessment.push(x);
    for (const x of messages.monitoringHrDataMesgs || [])
      out.hrData.push({ t: iso(x.timestamp), repos: x.restingHeartRate,
                        jour: x.currentDayRestingHeartRate });
    for (const x of messages.monitoringMesgs || [])
      out.monitoring.push({ t: iso(x.timestamp), steps: x.steps, activityType: x.activityType });
    for (const x of messages.stressLevelMesgs || []) out.stress.push(x.stressLevelValue);
    for (const x of messages.respirationRateMesgs || []) out.respiration.push(x.respirationRate);
    for (const x of messages.hrvStatusSummaryMesgs || []) out.hrvSummary.push(x);
  } catch (e) { /* fichier illisible : ignoré */ }
}
process.stdout.write(JSON.stringify(out));
""", encoding="utf-8")

def decode_day(d: Path):
    r = subprocess.run(["node", DECODER.name, str(d.resolve())],
                       cwd=DECODER.parent, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ! décodage échoué pour {d.name} : {r.stderr.strip()[:120]}")
        return None
    return json.loads(r.stdout)

def ts(x):
    return datetime.fromisoformat(x.replace("Z", "+00:00")) if x else None

# ---------------------------------------------------------------------------
# 3. Agrégation par jour
# ---------------------------------------------------------------------------
def summarize(day: str, m: dict) -> dict:
    o = {"date": day}

    # --- Sommeil : la durée vient des ÉVÉNEMENTS de session, pas des marqueurs de phase.
    # Sommer les intervalles entre marqueurs sous-estimait gravement (jusqu'à 4 h d'écart) :
    # quand les transitions sont espacées, des pans entiers de nuit disparaissent.
    ev = m.get("sleepEvents") or []
    debut = next((ts(x["t"]) for x in ev if x.get("type") == "start"), None)
    fin = next((ts(x["t"]) for x in ev if x.get("type") == "stop"), None)
    if debut and fin and fin > debut:
        total = round((fin - debut).total_seconds() / 60)
        o["sommeil_min"] = total
        o["sommeil_h"] = f"{total // 60}h{total % 60:02d}"
        o["coucher"] = debut.isoformat()[:16]
        o["lever"] = fin.isoformat()[:16]

    # --- Phases : intervalles entre marqueurs, la dernière fermée par la fin de session ---
    lv = sorted(m.get("sleepLevels") or [], key=lambda x: x["t"])
    if lv:
        bornes = [(ts(x["t"]), x.get("level", "?")) for x in lv]
        if fin:
            bornes.append((fin, None))
        mins = {}
        for (t1, niv), (t2, _) in zip(bornes, bornes[1:]):
            if niv:
                mins[niv] = mins.get(niv, 0) + (t2 - t1).total_seconds() / 60
        for k in ("deep", "light", "rem", "awake"):
            if k in mins:
                o[f"phase_{k}_min"] = round(mins[k])

    sa = (m.get("sleepAssessment") or [{}])[0]
    if sa:
        o["sommeil_score"] = sa.get("overallSleepScore")
        o["sommeil_qualite"] = sa.get("sleepQualityScore")
        o["reveils"] = sa.get("awakeningsCount")
        o["stress_pendant_sommeil"] = sa.get("averageStressDuringSleep")

    # --- VFC ---
    hv = (m.get("hrvSummary") or [{}])[0]
    if hv:
        o["vfc_nuit"] = hv.get("lastNightAverage")
        o["vfc_moy_7j"] = hv.get("weeklyAverage")
        o["vfc_statut"] = hv.get("status")
        o["vfc_baseline_bas"] = hv.get("baselineBalancedLower")
        o["vfc_baseline_haut"] = hv.get("baselineBalancedUpper")

    # --- FC de repos : c'est `currentDayRestingHeartRate` qui correspond à l'app.
    # `restingHeartRate` est une référence glissante, identique tous les jours (44) —
    # l'utiliser masquait complètement les variations réelles (41 à 49).
    duJour = [x for x in (m.get("hrData") or [])
              if x.get("jour") and x["t"][:10] == day]
    if duJour:
        o["fc_repos"] = duJour[-1]["jour"]          # valeur consolidée en fin de journée
    ref = [x["repos"] for x in (m.get("hrData") or []) if x.get("repos")]
    if ref:
        o["fc_repos_reference"] = min(ref)

    # --- Pas : cumul par type d'activité, on somme les maxima ---
    # NE PAS filtrer sur la date : l'agrégation brute sur le dossier est la seule qui
    # reproduise la référence RGPD (7 jours comparables, écart nul). Un filtrage par
    # date locale, essayé le 24/08/2026, s'en écartait de 469 à 1824 pas — le
    # recoupement de sources prime sur le raisonnement.
    par_type = {}
    for x in (m.get("monitoring") or []):
        if x.get("steps") is not None:
            t = x.get("activityType", "?")
            par_type[t] = max(par_type.get(t, 0), x["steps"])
    if par_type:
        o["pas"] = sum(par_type.values())

    # --- Troncature du compteur de pas -----------------------------------------
    # `steps` est un compteur CUMULÉ remis à zéro à minuit local (vérifié le
    # 24/08/2026 : 4502 pas à 22h00 UTC le 19/08, puis 74 à 23h56 — la remise à zéro
    # tombe à 22h00 UTC, soit minuit à Paris en été). Et l'export quotidien s'arrête
    # à l'heure EXACTE du téléchargement : un export du matin ne livre qu'une
    # demi-matinée. Le 20/08/2026, 893 pas relevés à 10h58 un jour où il a couru
    # 6,7 km le soir — lu brut, cela signe un effondrement de l'activité, or c'est
    # justement son signal d'alerte précoce le plus fiable. On note donc l'heure du
    # dernier relevé : sans elle, impossible de distinguer une journée creuse d'un
    # export matinal. Le faux positif coûte ici plus cher que l'absence de donnée.
    # Un relevé de CLÔTURE à minuit local (22h00 UTC en été) porte le total définitif
    # de la journée : c'est exactement sur ces jours-là que les deux sources concordent
    # (7 jours comparables, écart nul). Sans lui, le chiffre s'arrête à l'heure du
    # téléchargement et n'est qu'un compte partiel. `pas_arret` == "00:00" vaut donc
    # journée close, et non journée tronquée à minuit.
    horod = [ts(x["t"]).astimezone(PARIS) for x in (m.get("monitoring") or [])
             if x.get("steps") is not None and x.get("t")]
    if horod:
        dernier = max(horod)
        o["pas_arret"] = dernier.strftime("%H:%M")
        clos = dernier.hour >= 23 or (dernier.hour == 0 and dernier.minute <= 5)
        o["pas_partiel"] = not clos

    # --- Stress & respiration ---
    st = [v for v in (m.get("stress") or []) if isinstance(v, (int, float)) and v >= 0]
    if st:
        o["stress_moy"] = round(sum(st) / len(st), 1)
    rr = [v for v in (m.get("respiration") or []) if isinstance(v, (int, float)) and v > 0]
    if rr:
        o["respiration_moy"] = round(sum(rr) / len(rr), 1)

    return o

jours = []
for d in sorted(RAW.iterdir()):
    if not d.is_dir():
        continue
    msgs = decode_day(d)
    if msgs:
        jours.append(summarize(d.name, msgs))

# ---------------------------------------------------------------------------
# 4. Fusion avec l'historique déjà connu (pour ne rien perdre d'une semaine à l'autre)
# ---------------------------------------------------------------------------
existant = {}
if OUT.exists():
    existant = {j["date"]: j for j in json.loads(OUT.read_text(encoding="utf-8"))}
for j in jours:
    fusion = {**existant.get(j["date"], {}), **j}
    existant[j["date"]] = fusion
jours = [existant[k] for k in sorted(existant)]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(jours, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------------------------------------------------------------------
# 5. Récapitulatif
# ---------------------------------------------------------------------------
def moy(k):
    v = [j[k] for j in jours if j.get(k) is not None]
    return sum(v) / len(v) if v else None

print(f"\n{len(jours)} jours dans {OUT.relative_to(BASE)}\n")
print("Date         Sommeil  Score  Profond  Réveils   VFC  Statut     FC repos   Pas   Stress")
print("-" * 88)
for j in jours:
    print(f"{j['date']}  {j.get('sommeil_h','—'):>7}  {str(j.get('sommeil_score','—')):>5}"
          f"  {str(j.get('phase_deep_min','—'))+' min':>8}  {str(j.get('reveils','—')):>7}"
          f"  {str(j.get('vfc_nuit','—')):>4}  {str(j.get('vfc_statut','—')):<10}"
          f" {str(j.get('fc_repos','—')):>7}  {str(j.get('pas','—')):>6}  {str(j.get('stress_moy','—')):>5}")

print("-" * 88)
print(f"{'MOYENNES':12}  {int(moy('sommeil_min')//60)}h{int(moy('sommeil_min')%60):02d}"
      f"  {moy('sommeil_score'):5.0f}  {moy('phase_deep_min'):4.0f} min"
      f"  {moy('reveils'):9.1f}  {moy('vfc_nuit'):4.0f}"
      f"             {moy('fc_repos'):5.1f}  {moy('pas'):6.0f}  {moy('stress_moy'):5.1f}")

hv = [j for j in jours if j.get("vfc_baseline_bas")][-1:]
if hv:
    print(f"\nBaseline VFC calculée par Garmin : {hv[0]['vfc_baseline_bas']}–{hv[0]['vfc_baseline_haut']} ms "
          f"(moyenne 7 j : {hv[0].get('vfc_moy_7j')} ms)")
