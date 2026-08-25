#!/usr/bin/env python3
"""
Contrôle de synchronisation de TOUTES les destinations.

Motivation : le 22/08/2026, une séance de renfo a été déplacée dans Google Agenda
sans que le plan, le programme HTML ni le support soient mis à jour. the athlete had to
croiser les sources lui-même pour s'en apercevoir. Une modification touche
plusieurs destinations : les vérifier une par une n'est pas optionnel.

Usage : python3 harness/verifier_sync.py
Code de sortie : 0 si tout concorde, 1 sinon.
"""

import json, subprocess, sys
from datetime import date, datetime, timedelta
from pathlib import Path

BASE = Path(__file__).parent.parent
ecarts, notes = [], []

def mtime(p):
    return datetime.fromtimestamp(p.stat().st_mtime) if p.exists() else None

# ---------------------------------------------------------------------------
# 1. Fraîcheur de la chaîne locale : chaque artefact doit être postérieur à sa source
# ---------------------------------------------------------------------------
chaine = [
    ("harness/generate_plan.py", "build/plan.json"),
    ("build/plan.json",          "build/programme.html"),
    ("build/programme.html",     "dashboard.html"),
]
print("1. FRAÎCHEUR DE LA CHAÎNE")
for src, dst in chaine:
    ps, pd = BASE / src, BASE / dst
    if not ps.exists() or not pd.exists():
        ecarts.append(f"{dst} ou {src} manquant")
        print(f"   ✗ {src:<28} → {dst:<26} fichier manquant")
        continue
    ok = mtime(pd) >= mtime(ps)
    print(f"   {'✓' if ok else '✗'} {src:<28} → {dst:<26}"
          f" {mtime(ps).strftime('%d/%m %H:%M')} → {mtime(dst := pd).strftime('%d/%m %H:%M')}")
    if not ok:
        ecarts.append(f"{dst.name} est plus ancien que {src} : régénérer")

# ---------------------------------------------------------------------------
# 2. Le programme embarqué porte-t-il le même état que le plan ?
# ---------------------------------------------------------------------------
print("\n2. ÉTAT DES SÉANCES FAITES")
import re, html as H
plan = json.loads((BASE / "build" / "plan.json").read_text(encoding="utf-8"))
def faites(p):
    return {x["id"] for w in p["weeks"] for j in w["days"] for x in j["workouts"] if x.get("completed")}
f_plan = faites(plan)
sources = {"build/plan.json": f_plan}
for nom, extracteur in [
    ("build/programme.html", lambda t: json.loads(re.search(r'id="plan-data"[^>]*>(.*?)</script>', t, re.S).group(1))),
    ("dashboard.html", lambda t: json.loads(re.search(r'id="plan-data"[^>]*>(.*?)</script>',
                        H.unescape(re.search(r'<iframe srcdoc="(.*?)" title=', t, re.S).group(1)), re.S).group(1))),
]:
    p = BASE / nom
    if not p.exists():
        continue
    try:
        sources[nom] = faites(extracteur(p.read_text(encoding="utf-8")))
    except Exception as e:
        ecarts.append(f"{nom} : état illisible ({type(e).__name__})")
for nom, s in sources.items():
    ok = s == f_plan
    print(f"   {'✓' if ok else '✗'} {nom:<26} {len(s)} séance(s) marquée(s)")
    if not ok:
        ecarts.append(f"{nom} : {len(s)} séances marquées contre {len(f_plan)} dans le plan")

# ---------------------------------------------------------------------------
# 3. Fichiers .fit de la montre : couvrent-ils le plan courant ?
# ---------------------------------------------------------------------------
print("\n3. FICHIERS GARMIN")
fit = sorted((BASE / "garmin-fit").glob("*.fit")) if (BASE / "garmin-fit").exists() else []
n_course = sum(1 for w in plan["weeks"] for j in w["days"] for x in j["workouts"]
               if x["sport"] == "run")
print(f"   {'✓' if len(fit) >= n_course else '✗'} {len(fit)} fichier(s) .fit pour {n_course} séance(s) de course")
if len(fit) < n_course:
    ecarts.append(f"{n_course - len(fit)} séance(s) sans fichier .fit : relancer gen-fit.ts")
plan_t = mtime(BASE / "build" / "plan.json")
vieux = [f for f in fit if mtime(f) < plan_t]
if vieux:
    print(f"   ✗ {len(vieux)} fichier(s) antérieur(s) au plan")
    ecarts.append(f"{len(vieux)} fichier(s) .fit plus anciens que le plan : régénérer")

# Les ZIPS sont ce que you actually load into the watch — pas le dossier.
# gen-fit.ts n'écrit que les .fit : le 24/08/2026, garmin-fit.zip datait du 17/08
# alors que les séances avaient changé, et ce contrôle passait au vert.
# Un zip périmé fait charger de mauvaises séances : c'est une désynchronisation.
fit_t = max((mtime(f) for f in fit), default=None)
for nom in ("garmin-fit.zip", "garmin-fit-a-charger.zip"):
    z = BASE / nom
    if not z.exists():
        print(f"   ✗ {nom} absent")
        ecarts.append(f"{nom} absent : lancer harness/zip_fit.py")
        continue
    if fit_t and mtime(z) < fit_t:
        age = (fit_t - mtime(z)).days
        print(f"   ✗ {nom} antérieur aux .fit ({mtime(z):%d/%m %H:%M} contre {fit_t:%d/%m %H:%M})")
        ecarts.append(f"{nom} périmé de {age} jour(s) — il contient d'anciennes séances. "
                      f"Lancer `python3 harness/zip_fit.py <semaine>`.")
    else:
        import zipfile as _z
        with _z.ZipFile(z) as zf:
            print(f"   ✓ {nom} à jour ({len(zf.namelist())} séance(s))")

# ---------------------------------------------------------------------------
# 4. Google Agenda — contrôlé par machine depuis le 23/08/2026
# ---------------------------------------------------------------------------
print("\n4. GOOGLE AGENDA")
# L'agenda n'est plus « à croiser à la main » : ses descriptions sont générées par
# harness/agenda.py depuis le plan, puis comparées au relevé réel de list_events.
# Un relevé absent ou périmé est une DÉSYNCHRONISATION, pas une simple note.
sem = max(1, min(30, (date.today() - date(2026, 8, 17)).days // 7 + 1))
res = subprocess.run([sys.executable, str(BASE / "harness" / "agenda.py"), "verifier", str(sem)],
                     capture_output=True, text=True, cwd=str(BASE))
for l in (res.stdout or "").rstrip().split("\n"):
    if l:
        print("   " + l)
if res.returncode != 0:
    ecarts.append(f"Google Agenda semaine {sem} : date, complétion ou contenu divergents. "
                  f"Corriger : `python3 harness/agenda.py generer {sem}`, pousser par MCP, "
                  f"puis réenregistrer suivi/agenda-reel.json depuis list_events.")

# ---------------------------------------------------------------------------
print("\n" + "=" * 74)
if ecarts:
    print("DÉSYNCHRONISATIONS :")
    for e in ecarts:
        print("   ✗ " + e)
else:
    print("Toutes les destinations locales concordent.")
for n in notes:
    print("   ! " + n)
print("=" * 74)
sys.exit(1 if ecarts else 0)
