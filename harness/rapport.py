#!/usr/bin/env python3
"""
Génère le support unique de la prépa : marathon.html (onglets Suivi + Programme)

Croise plan + Strava (via suivi/journal.json) + Garmin (wellness-daily.json) + poids.csv.
Page autonome : le programme 30 semaines est embarqué via srcdoc, aucun accès fichier requis.

Usage : python3 rapport.py
"""

import csv, html as _html, json
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean

import sys
sys.path.insert(0, str(Path(__file__).parent))
from dashboard import poids_cible, POIDS_DEPART, POIDS_CIBLE, PLAN_START, semaine_de, lundi_de

BASE = Path(__file__).parent.parent
OUT = BASE / "marathon.html"                              # support unique, deux onglets
PROGRAMME = BASE / "build" / "programme.html"              # source embarquée dans l'onglet Programme
COURSE = date(2027, 3, 14)

# ---------------------------------------------------------------------------
# Données
# ---------------------------------------------------------------------------
plan = json.loads((BASE / "build" / "plan.json").read_text(encoding="utf-8"))
semaines_plan = {w["weekNumber"]: w for w in plan["weeks"]}

journal = {}
f = BASE / "suivi" / "journal.json"
if f.exists():
    journal = {j["semaine"]: j for j in json.loads(f.read_text(encoding="utf-8"))}

wellness = []
f = BASE / "garmin-export" / "wellness-daily.json"
if f.exists():
    wellness = json.loads(f.read_text(encoding="utf-8"))

pesees = []
f = BASE / "poids.csv"
if f.exists():
    with f.open(encoding="utf-8") as fh:
        pesees = [(r["date"], float(r["kg"])) for r in csv.DictReader(fh) if r.get("kg")]

aujourdhui = date.today()
sem_actuelle = semaine_de(aujourdhui)
jours_restants = (COURSE - aujourdhui).days

# ---------------------------------------------------------------------------
# Primitives SVG — un axe, jamais deux ; marques fines ; grille discrète
# ---------------------------------------------------------------------------
W, H = 760, 240
PAD = {"l": 46, "r": 16, "t": 16, "b": 30}

def echelle(vmin, vmax, taille, pad_bas, pad_haut):
    span = (vmax - vmin) or 1
    return lambda v: taille - pad_bas - (v - vmin) / span * (taille - pad_bas - pad_haut)

def axe_y(vmin, vmax, sy, fmt=lambda v: f"{v:g}", n=4):
    out = []
    for i in range(n + 1):
        v = vmin + (vmax - vmin) * i / n
        y = sy(v)
        out.append(f'<line class="grid" x1="{PAD["l"]}" y1="{y:.1f}" x2="{W-PAD["r"]}" y2="{y:.1f}"/>')
        out.append(f'<text class="tick" x="{PAD["l"]-8}" y="{y+4:.1f}" text-anchor="end">{fmt(v)}</text>')
    return "".join(out)

def axe_x_semaines(sx, pas=4):
    out = []
    for s in range(1, 31, pas):
        x = sx(s)
        out.append(f'<text class="tick" x="{x:.1f}" y="{H-PAD["b"]+18:.0f}" text-anchor="middle">S{s}</text>')
    return "".join(out)

def chemin(points):
    return " ".join(("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}" for i, (x, y) in enumerate(points))

def graphe_semaines(titre, sous_titre, series, vmin, vmax, fmt=lambda v: f"{v:g}", jalons=True, c="c-run"):
    """series = [(label, [(semaine, valeur)], style)] ; style ∈ {'reference','reel','barre_ref','barre_reel'}
    c = classe de couleur de la série réelle : c-run (orange), c-gold (or), c-blue (bleu)"""
    sx = lambda s: PAD["l"] + (s - 1) / 29 * (W - PAD["l"] - PAD["r"])
    sy = echelle(vmin, vmax, H, PAD["b"], PAD["t"])
    parts = [axe_y(vmin, vmax, sy, fmt), axe_x_semaines(sx)]

    if jalons:
        for s, lbl in [(4, "test"), (12, "retest"), (23, "semi"), (30, "Rome")]:
            x = sx(s)
            parts.append(f'<line class="jalon" x1="{x:.1f}" y1="{PAD["t"]}" x2="{x:.1f}" y2="{H-PAD["b"]}"/>')
            parts.append(f'<text class="jalon-txt" x="{x:.1f}" y="{PAD["t"]-4}" text-anchor="middle">{lbl}</text>')

    largeur_barre = (W - PAD["l"] - PAD["r"]) / 30 * 0.62
    for label, pts, style in series:
        pts = [(s, v) for s, v in pts if v is not None]
        if not pts:
            continue
        if style.startswith("barre"):
            cls = "bar-ref" if style == "barre_ref" else f"bar-reel {c}"
            for s, v in pts:
                x, y = sx(s) - largeur_barre / 2, sy(v)
                h = max(0, (H - PAD["b"]) - y)
                parts.append(f'<rect class="{cls}" x="{x:.1f}" y="{y:.1f}" width="{largeur_barre:.1f}" '
                             f'height="{h:.1f}" rx="2"/>')
        else:
            cls = "line-ref" if style == "reference" else f"line-reel {c}"
            parts.append(f'<path class="{cls}" d="{chemin([(sx(s), sy(v)) for s, v in pts])}"/>')
            if style == "reel":
                for s, v in pts:
                    parts.append(f'<circle class="pt {c}" cx="{sx(s):.1f}" cy="{sy(v):.1f}" r="4">'
                                 f'<title>S{s} — {fmt(v)}</title></circle>')
    legende = "".join(
        f'<span class="lg"><i class="sw {"ref" if st in ("reference","barre_ref") else c}"></i>{lb}</span>'
        for lb, _, st in series)
    return f"""<figure class="card">
  <figcaption><h3>{titre}</h3><p>{sous_titre}</p></figcaption>
  <div class="legend">{legende}</div>
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="{titre}">{''.join(parts)}</svg>
</figure>"""

def graphe_jours(titre, sous_titre, cle, fmt=lambda v: f"{v:g}", bande=None, c="c-blue"):
    pts = [(j["date"], j[cle]) for j in wellness if j.get(cle) is not None
           and not (cle.startswith("sommeil") and j.get("sommeil_fiable") is False)]
    if not pts:
        return f'<figure class="card"><figcaption><h3>{titre}</h3><p>Aucune donnée</p></figcaption></figure>'
    vals = [v for _, v in pts]
    vmin, vmax = min(vals), max(vals)
    marge = (vmax - vmin) * 0.25 or 1
    if bande:
        vmin, vmax = min(vmin, bande[0]), max(vmax, bande[1])
    vmin, vmax = vmin - marge, vmax + marge
    h2 = 170
    sx = lambda i: PAD["l"] + i / max(1, len(pts) - 1) * (W - PAD["l"] - PAD["r"])
    sy = echelle(vmin, vmax, h2, PAD["b"], PAD["t"])
    # Amplitude faible (ex. FC de repos 42-44) : sans ça les graduations se répètent
    n_tick = 4
    if len({fmt(vmin + (vmax - vmin) * i / 4) for i in range(5)}) < 5:
        fmt_orig, fmt = fmt, lambda v: f"{v:.1f}"
        if len({fmt(vmin + (vmax - vmin) * i / 4) for i in range(5)}) < 5:
            n_tick, fmt = 2, fmt_orig
    parts = []
    for i in range(n_tick + 1):
        v = vmin + (vmax - vmin) * i / n_tick
        y = sy(v)
        parts.append(f'<line class="grid" x1="{PAD["l"]}" y1="{y:.1f}" x2="{W-PAD["r"]}" y2="{y:.1f}"/>')
        parts.append(f'<text class="tick" x="{PAD["l"]-8}" y="{y+4:.1f}" text-anchor="end">{fmt(v)}</text>')
    if bande:
        y1, y2 = sy(bande[1]), sy(bande[0])
        parts.insert(0, f'<rect class="bande" x="{PAD["l"]}" y="{y1:.1f}" '
                        f'width="{W-PAD["l"]-PAD["r"]:.1f}" height="{abs(y2-y1):.1f}"/>')
    parts.append(f'<path class="line-reel {c}" d="{chemin([(sx(i), sy(v)) for i, (_, v) in enumerate(pts)])}"/>')
    for i, (d, v) in enumerate(pts):
        parts.append(f'<circle class="pt {c}" cx="{sx(i):.1f}" cy="{sy(v):.1f}" r="3.5"><title>{d} — {fmt(v)}</title></circle>')
    for i in (0, len(pts) - 1):
        j, m = pts[i][0][8:10], pts[i][0][5:7]
        parts.append(f'<text class="tick" x="{sx(i):.1f}" y="{h2-PAD["b"]+18:.0f}" '
                     f'text-anchor="{"start" if i==0 else "end"}">{j}/{m}</text>')
    return f"""<figure class="card small">
  <figcaption><h3>{titre}</h3><p>{sous_titre}</p></figcaption>
  <svg viewBox="0 0 {W} {h2}" role="img" aria-label="{titre}">{''.join(parts)}</svg>
</figure>"""

# ---------------------------------------------------------------------------
# Séries
# ---------------------------------------------------------------------------
poids_pts_cible = [(s, poids_cible(s)) for s in range(1, 31)]
poids_pts_reel = [(semaine_de(date.fromisoformat(d)), kg) for d, kg in pesees]

vol_prevu = [(s, semaines_plan[s]["summary"]["bySport"]["run"]["km"]) for s in sorted(semaines_plan)]
vol_reel = [(s, j.get("km_reel")) for s, j in sorted(journal.items())]

allure = [(s, j["allure_a_145"]) for s, j in sorted(journal.items()) if j.get("allure_a_145")]

# ---------------------------------------------------------------------------
# Tuiles
# ---------------------------------------------------------------------------
def moy_well(cle, n=7):
    src = [j for j in wellness[-n:]
           if not (cle.startswith("sommeil") and j.get("sommeil_fiable") is False)]
    v = [j[cle] for j in src if j.get(cle) is not None]
    return mean(v) if v else None

poids_now = pesees[-1][1] if pesees else None
cible_now = poids_cible(sem_actuelle)
ecart = round(poids_now - cible_now, 1) if poids_now else None
sommeil = moy_well("sommeil_min")
vfc = moy_well("vfc_nuit")
fcr = moy_well("fc_repos")

# ---------------------------------------------------------------------------
# Chaussures : état calculé une fois, servant à la tuile et à la section détaillée
# ---------------------------------------------------------------------------
def etat_chaussures():
    f = BASE / "garmin-export" / "chaussures.json"
    if not f.exists():
        return []
    data = json.loads(f.read_text(encoding="utf-8"))
    arret = data.get("arrete_le")
    # kilomètres courus après l'arrêt du décompte Garmin, attribués à la paire principale
    depuis = round(sum(j.get("km_reel") or 0 for j in journal.values()
                       if j.get("fin", "") > (arret or "")), 1)
    out = []
    for pr in data["paires"]:
        maxi = pr["km_max"]
        if pr.get("km_garmin") is None:                 # kilométrage pas encore confirmé
            out.append({**pr, "km": None, "pct": None, "etat": "inconnu",
                        "libelle": "à renseigner", "icone": "?", "proj": None})
            continue
        km = pr["km_garmin"] + (depuis if pr.get("principale") else 0)
        pct = km / maxi * 100
        if pr.get("principale"):
            etat, libelle, icone = (("crit", "à remplacer", "✕") if pct >= 100
                                    else ("warn", "fin de vie proche", "!") if pct >= 75
                                    else ("ok", "bon état", "✓"))
        else:
            etat, libelle, icone = (("", "au repos — hors limite", "·") if pct >= 100
                                    else ("", "au repos", "·"))
        # semaine du plan où la limite serait atteinte si la paire portait tout le volume
        reste_km, proj, cumul = max(0, round(maxi - km)), None, 0
        for sm in sorted(x for x in semaines_plan if x >= sem_actuelle):
            cumul += semaines_plan[sm]["summary"]["bySport"]["run"]["km"]
            if cumul >= reste_km:
                proj = sm
                break
        out.append({**pr, "km": km, "pct": pct, "etat": etat,
                    "libelle": libelle, "icone": icone, "proj": proj})
    return out

# Titre et bandeau viennent du plan, jamais d'une chaîne en dur.
_race = plan.get("raceStrategy", {}).get("event", {})
EVENT = _race.get("name") or plan.get("meta", {}).get("name") or "Training plan"
_ed = _race.get("date") or ""
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
         "août", "septembre", "octobre", "novembre", "décembre"]
EVENT_DATE_FR = (f"{int(_ed[8:10])} {_MOIS[int(_ed[5:7]) - 1]} {_ed[:4]}" if len(_ed) >= 10 else "")
TARGET_TIME = plan.get("meta", {}).get("targetTime") or ""
TARGET_PACE = (plan.get("raceStrategy", {}).get("pacing", {})
               .get("run", {}).get("targetPace") or "")

chaussures = etat_chaussures()

def tuile(valeur, label, detail="", etat=""):
    return f"""<div class="tile {etat}"><div class="v">{valeur}</div>
      <div class="l">{label}</div><div class="d">{detail}</div></div>"""

etat_poids = "good" if ecart is not None and ecart <= 0.5 else "warn" if ecart is not None else ""
etat_sommeil = "good" if sommeil and sommeil >= 420 else "warn" if sommeil else ""
etat_vfc = "good" if vfc and vfc >= 73 else "warn" if vfc else ""

tuiles = "".join([
    tuile(f"J−{jours_restants}", "avant Rome", COURSE.strftime("%d/%m/%Y")),
    tuile(f"{sem_actuelle}<span class='u'>/30</span>", "semaine",
          semaines_plan[sem_actuelle]["phase"] if sem_actuelle in semaines_plan else ""),
    tuile(f"{poids_now:.1f}<span class='u'>kg</span>" if poids_now else "—", "poids",
          f"cible S{sem_actuelle} : {cible_now:.1f} kg" if poids_now else "", etat_poids),
    tuile(f"{int(sommeil//60)}<span class='u'>h</span>{int(sommeil%60):02d}" if sommeil else "—",
          "sommeil / nuit", "moyenne 7 jours", etat_sommeil),
    tuile(f"{vfc:.0f}<span class='u'>ms</span>" if vfc else "—", "VFC",
          "baseline 73–105" if vfc else "", etat_vfc),
    tuile(f"{fcr:.0f}", "FC de repos", "médiane 46 · alerte > 52" if fcr else ""),
])

# ---------------------------------------------------------------------------
# Commentaires automatiques
# ---------------------------------------------------------------------------
obs = []
if poids_now is not None:
    perdu = POIDS_DEPART - poids_now
    if ecart <= 0.5:
        obs.append(("good", "Poids dans la trajectoire",
                    f"{poids_now:.1f} kg pour une cible de {cible_now:.1f} kg à la semaine {sem_actuelle}. "
                    f"{perdu:.1f} kg perdus, il en reste {poids_now - POIDS_CIBLE:.1f} pour atteindre {POIDS_CIBLE} kg. "
                    f"Gain estimé à ce stade : environ {round(perdu*1.4)} min sur le marathon."))
    else:
        obs.append(("warn", f"Poids en retard de {ecart:.1f} kg sur la trajectoire",
                    f"Sans dramatiser : la fenêtre utile court jusqu'à la semaine 22. Au-delà, la charge "
                    f"d'entraînement prime et le déficit devient contre-productif."))
if sommeil:
    if sommeil < 420:
        obs.append(("warn", f"Sommeil sous ta baseline : {int(sommeil//60)}h{int(sommeil%60):02d}",
                    "Ta moyenne sur 443 nuits fiables est de 7h31. Une semaine nettement en dessous mérite "
                    "attention — mais ton sommeil n'est pas un point faible structurel, l'historique le montre."))
    else:
        obs.append(("good", f"Sommeil conforme : {int(sommeil//60)}h{int(sommeil%60):02d} de moyenne",
                    "Dans ta norme (7h31 sur 443 nuits fiables). Ton sommeil est un atout, pas un problème."))
if vfc:
    if vfc >= 73:
        obs.append(("good", f"Récupération nerveuse bonne — VFC {vfc:.0f} ms",
                    "Dans la baseline Garmin (73–105). Aucun signe de surcharge : la charge actuelle est absorbée."))
    else:
        obs.append(("warn", f"VFC sous la baseline — {vfc:.0f} ms",
                    "Sous 73 ms, signal de fatigue accumulée ou d'infection naissante. La semaine à venir "
                    "doit être allégée plutôt que maintenue."))
if fcr and fcr > 47:
    obs.append(("warn", f"FC de repos élevée — {fcr:.0f} bpm",
                "Au-dessus de ta baseline de 43. Croisé avec la VFC, c'est un signal de fatigue à prendre au sérieux."))

sem_faites = [s for s, j in journal.items() if j.get("km_reel")]
if sem_faites:
    tot_prevu = sum(semaines_plan[s]["summary"]["bySport"]["run"]["km"] for s in sem_faites)
    tot_reel = sum(journal[s]["km_reel"] for s in sem_faites)
    taux = tot_reel / tot_prevu * 100 if tot_prevu else 0
    etat = "good" if taux >= 85 else "warn"
    obs.append((etat, f"Assiduité : {taux:.0f} % du volume prévu",
                f"{tot_reel:.0f} km courus sur {tot_prevu:.0f} prévus depuis le début. "
                + ("C'est le chiffre qui décidera de Rome — bien plus que la qualité des séances."
                   if taux >= 85 else
                   "Ton facteur d'échec historique est l'interruption, pas l'entraînement mal fait. "
                   "Ce pourcentage est l'indicateur à surveiller avant tous les autres.")))
else:
    obs.append(("", "Prépa non commencée",
                "Première séance le mardi 18/08. Les indicateurs d'entraînement se rempliront à partir "
                "du premier bilan du lundi."))

if allure:
    a0, a1 = allure[0][1], allure[-1][1]
    if len(allure) > 1:
        d = a0 - a1
        obs.append(("good" if d > 0 else "",
                    f"Allure à 145 bpm : {a1//60}:{a1%60:02d}/km" + (f" ({d:+.0f} s depuis S{allure[0][0]})" if d else ""),
                    "C'est l'indicateur le plus fiable du progrès aérobie : il mesure ce que tu tiens à "
                    "effort cardiaque constant, indépendamment de la météo et de la forme du jour."))

blocs_obs = "".join(
    f'<div class="obs {e}"><h4>{t}</h4><p>{d}</p></div>' for e, t, d in obs)

# ---------------------------------------------------------------------------
# Chaussures : jauge d'usure + projection sur le reste de la prépa
# ---------------------------------------------------------------------------
def bloc_chaussures():
    if not chaussures:
        return ""
    # kilomètres restant à courir dans le plan
    reste_plan = round(sum(semaines_plan[s]["summary"]["bySport"]["run"]["km"]
                           for s in semaines_plan if s >= sem_actuelle), 0)

    cartes = []
    for p in chaussures:
        usage = f'<span class="use {p.get("usage","")}">{p.get("usage","")}</span>' if p.get("usage") else ""
        if p["pct"] is None:
            cartes.append(f"""<div class="shoe inconnu">
      <div class="shoe-head"><span class="shoe-name">{p['nom']}{usage}</span>
        <span class="shoe-tag"><i>?</i>à renseigner</span></div>
      <div class="gauge"><div class="gauge-fill" style="width:0%"></div></div>
      <div class="shoe-foot"><span>— / {p['km_max']} km</span><span>—</span></div>
      <p class="shoe-note">Kilométrage à relever dans Garmin Connect &gt; Équipement,
        les sorties ayant été réattribuées.</p>
    </div>""")
            continue
        km, maxi, pct = p["km"], p["km_max"], p["pct"]
        etat, libelle, icone, proj = p["etat"], p["libelle"], p["icone"], p["proj"]
        if pct >= 100 and not p.get("principale"):
            note = (f"Dépassement de {round(km - maxi)} km, mais cette paire n'accumule plus de "
                    f"kilomètres : rien à faire. La paire en service est celle marquée « principale ».")
        elif pct >= 100:
            note = (f"Dépassement de {round(km - maxi)} km sur la paire en service. "
                    f"À remplacer <strong>maintenant</strong> — l'amorti est perdu bien avant la semelle.")
        elif p.get("usage") == "trail":
            note = (f"Chaussure de trail : hors du volume route du plan. "
                    f"Encore {round(maxi - km)} km avant remplacement.")
        elif proj:
            note = (f"Limite atteinte vers la <strong>semaine {proj}</strong> si elle porte "
                    f"tout le volume route du plan.")
        else:
            note = f"Couvre les {reste_plan:.0f} km restants du plan."
        largeur = min(pct, 100)
        cartes.append(f"""<div class="shoe {etat}">
      <div class="shoe-head"><span class="shoe-name">{p['nom']}{usage}</span>
        <span class="shoe-tag"><i>{icone}</i>{libelle}</span></div>
      <div class="gauge"><div class="gauge-fill" style="width:{largeur:.1f}%"></div>
        {'<div class="gauge-over"></div>' if pct > 100 else ''}</div>
      <div class="shoe-foot"><span><strong>{km:.0f}</strong> / {maxi} km</span>
        <span>{pct:.0f} %</span></div>
      <p class="shoe-note">{note}</p>
      <p class="shoe-meta">{"En service depuis le " + p['depuis'][8:10] + "/" + p['depuis'][5:7] + "/" + p['depuis'][:4] if p.get('depuis') else "Mise en service inconnue"}{" · " + str(p['activites']) + " sorties" if p.get('activites') else ""}{" · dernière le " + p['derniere_sortie'][8:10] + "/" + p['derniere_sortie'][5:7] if p.get('derniere_sortie') else ""}</p>
    </div>""")
    data = json.loads((BASE / "garmin-export" / "chaussures.json").read_text(encoding="utf-8"))
    prov = ('<span class="prov">relevé provisoire du '
            f'{data.get("releve_le","")[8:10]}/{data.get("releve_le","")[5:7]} — '
            'attribution des sorties en cours de correction</span>' if data.get("provisoire") else "")
    return ('<h2>Chaussures</h2>\n<div class="shoes">' + "".join(cartes) + "</div>\n"
            f'<p class="shoes-note">Seuils réglés dans Garmin. Il reste '
            f'<strong>{reste_plan:.0f} km</strong> de course à pied dans le plan jusqu\'à Rome. {prov}</p>')

bloc_chaussures_html = bloc_chaussures()

# Le programme est embarqué via srcdoc plutôt que par un src relatif : Safari bloque
# les iframes file:// vers un fichier voisin, ce qui donnerait un panneau vide.
if PROGRAMME.exists():
    # GARDE-FOU : si le programme a été rendu AVANT la dernière écriture du plan, il
    # ne porte pas les séances marquées faites — l'onglet Programme afficherait 0 %.
    # C'est arrivé le 21/08/2026 : rendu lancé avant marquer_realise.py.
    plan_json = BASE / "build" / "plan.json"
    if PROGRAMME.stat().st_mtime < plan_json.stat().st_mtime:
        import sys as _sys
        print("ERREUR : build/programme.html est plus ancien que build/plan.json.")
        print("  Le programme embarqué ne porterait pas l'état des séances faites.")
        print("  Relance dans cet ordre :")
        print("    1. python3 harness/marquer_realise.py")
        print("    2. npx tsx src/cli.ts render build/plan.json "
              "--output ../build/programme.html")
        print("    3. python3 harness/rapport.py")
        _sys.exit(1)
    programme_srcdoc = _html.escape(PROGRAMME.read_text(encoding="utf-8"), quote=True)
else:
    programme_srcdoc = _html.escape(
        "<!doctype html><meta charset='utf-8'>"
        "<body style='background:#0a0a0b;color:#a1a1aa;font:15px system-ui;padding:40px'>"
        "Programme introuvable — relance <code>generate_plan.py</code> puis le rendu.</body>", quote=True)

# Graphe d'allure : vide tant qu'aucune semaine n'est enregistrée
if allure:
    bloc_allure = graphe_semaines(
        "Allure à 145 bpm",
        "Allure tenue à fréquence cardiaque constante — l'indicateur le plus fiable du progrès "
        "aérobie. Une courbe qui descend signifie que le moteur se construit.",
        [("Allure", allure, "reel")], 300, 440,
        lambda v: f"{int(v)//60}:{int(v)%60:02d}", c="c-run")
else:
    bloc_allure = ('<figure class="card"><figcaption><h3>Allure à 145 bpm</h3>'
                   "<p>Se remplira dès la première semaine d'entraînement. C'est l'indicateur le plus "
                   "fiable du progrès aérobie : l'allure tenue à effort cardiaque constant, "
                   "indépendamment de la météo et de la forme du jour.</p></figcaption></figure>")

# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
html = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{EVENT}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Playfair+Display:wght@500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {{
  color-scheme: dark;
  --bg-primary:#0a0a0b; --bg-secondary:#141416; --bg-tertiary:#1c1c1f; --bg-elevated:#232327;
  --text-primary:#fafafa; --text-secondary:#a1a1aa; --text-muted:#71717a;
  --border-subtle:rgba(255,255,255,.06); --border-medium:rgba(255,255,255,.1);
  --run:#f97316; --run-glow:rgba(249,115,22,.15);
  --bike:#22c55e; --strength:#a855f7; --rest:#52525b;
  --accent:#eab308; --accent-glow:rgba(234,179,8,.2);
  --blue:#3b82f6; --teal:#14b8a6;
  --good:#22c55e; --warn:#eab308;
  --st-good:#0ca30c; --st-warn:#fab219; --st-crit:#d03b3b;
  --ref:#71717a;
  --sans:'Outfit',-apple-system,sans-serif;
  --serif:'Playfair Display',serif;
  --mono:'JetBrains Mono',monospace;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg-primary); color:var(--text-primary);
  font:400 15px/1.6 var(--sans); -webkit-font-smoothing:antialiased; }}
.wrap {{ max-width:880px; margin:0 auto; padding:32px 20px 72px; }}
a {{ color:var(--accent); }}

header h1 {{ font-family:var(--serif); font-size:34px; font-weight:600; margin:0 0 6px;
  letter-spacing:-.01em; }}
header p {{ margin:0 0 28px; color:var(--accent); font-family:var(--mono);
  font-size:12.5px; letter-spacing:.02em; }}

.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(132px,1fr)); gap:12px; margin-bottom:34px; }}
.tile {{ background:var(--bg-secondary); border:1px solid var(--border-subtle);
  border-radius:12px; padding:16px 16px 14px; transition:border-color var(--t,.25s); }}
.tile:hover {{ border-color:var(--border-medium); }}
.tile .v {{ font-size:28px; font-weight:600; letter-spacing:-.02em; line-height:1.15; }}
.tile .v .u {{ font-size:14px; font-weight:400; color:var(--text-secondary); margin-left:2px; }}
.tile .l {{ font-family:var(--mono); font-size:10.5px; text-transform:uppercase;
  letter-spacing:.09em; color:var(--text-secondary); margin-top:6px; }}
.tile .d {{ font-size:11.5px; color:var(--text-muted); margin-top:3px; min-height:15px; }}
.tile.good {{ box-shadow:inset 3px 0 0 var(--good); }}
.tile.warn {{ box-shadow:inset 3px 0 0 var(--warn); }}
.tile.ok   {{ box-shadow:inset 3px 0 0 var(--st-good); }}
.tile.crit {{ box-shadow:inset 3px 0 0 var(--st-crit); }}
.tile-gauge {{ margin:9px 0 7px; height:6px; }}
.tile.ok   .gauge-fill {{ background:var(--st-good); }}
.tile.warn .gauge-fill {{ background:var(--st-warn); }}
.tile.crit .gauge-fill {{ background:var(--st-crit); }}

h2 {{ font-family:var(--mono); font-size:11px; text-transform:uppercase; letter-spacing:.14em;
  color:var(--text-muted); margin:40px 0 14px; font-weight:500; }}

.card {{ background:var(--bg-secondary); border:1px solid var(--border-subtle);
  border-radius:12px; margin:0 0 16px; padding:20px 20px 10px; overflow-x:auto; }}
.card figcaption h3 {{ margin:0; font-family:var(--serif); font-size:19px; font-weight:600; }}
.card figcaption p {{ margin:5px 0 12px; font-size:13px; color:var(--text-secondary); max-width:64ch; }}
.card svg {{ display:block; width:100%; height:auto; min-width:520px; }}
.legend {{ display:flex; gap:18px; margin:0 0 8px; font-family:var(--mono);
  font-size:10.5px; text-transform:uppercase; letter-spacing:.07em; color:var(--text-secondary); }}
.lg {{ display:inline-flex; align-items:center; gap:7px; }}
.sw {{ width:15px; height:3px; border-radius:2px; display:inline-block; }}
.sw.ref {{ background:var(--ref); }}
.sw.c-run {{ background:var(--run); }}
.sw.c-gold {{ background:var(--accent); }}
.sw.c-blue {{ background:var(--blue); }}

.grid {{ stroke:var(--border-subtle); stroke-width:1; }}
.tick {{ fill:var(--text-muted); font-family:var(--mono); font-size:10px; }}
.jalon {{ stroke:var(--border-medium); stroke-width:1; stroke-dasharray:2 4; }}
.jalon-txt {{ fill:var(--text-muted); font-family:var(--mono); font-size:9px;
  text-transform:uppercase; letter-spacing:.08em; }}
.line-reel {{ fill:none; stroke-width:2.5; stroke-linejoin:round; stroke-linecap:round; }}
.line-ref {{ fill:none; stroke:var(--ref); stroke-width:2; stroke-dasharray:5 4; }}
.bar-ref {{ fill:var(--rest); opacity:.5; }}
.bar-reel {{ stroke:var(--bg-secondary); stroke-width:2; }}
.pt {{ stroke:var(--bg-secondary); stroke-width:2; }}
.c-run.line-reel {{ stroke:var(--run); }}  .c-run.pt, .c-run.bar-reel {{ fill:var(--run); }}
.c-gold.line-reel {{ stroke:var(--accent); }} .c-gold.pt, .c-gold.bar-reel {{ fill:var(--accent); }}
.c-blue.line-reel {{ stroke:var(--blue); }} .c-blue.pt, .c-blue.bar-reel {{ fill:var(--blue); }}
.bande {{ fill:var(--good); opacity:.08; }}

.obs {{ background:var(--bg-secondary); border:1px solid var(--border-subtle);
  border-radius:12px; padding:16px 18px; margin-bottom:11px; }}
.obs h4 {{ margin:0 0 5px; font-size:15px; font-weight:600; }}
.obs p {{ margin:0; font-size:13.5px; color:var(--text-secondary); max-width:74ch; }}
.obs.good {{ box-shadow:inset 3px 0 0 var(--good); }}
.obs.good h4 {{ color:var(--good); }}
.obs.warn {{ box-shadow:inset 3px 0 0 var(--warn); }}
.obs.warn h4 {{ color:var(--warn); }}

footer {{ margin-top:44px; padding-top:18px; border-top:1px solid var(--border-subtle);
  font-family:var(--mono); font-size:10.5px; line-height:1.9; color:var(--text-muted); }}

/* Chaussures */
.shoes {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:14px; }}
.shoe {{ background:var(--bg-secondary); border:1px solid var(--border-subtle);
  border-radius:12px; padding:18px 20px 16px; }}
.shoe-head {{ display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:12px; }}
.shoe-name {{ font-family:var(--serif); font-size:17px; font-weight:600; }}
.use {{ display:inline-block; margin-left:9px; padding:3px 8px; border-radius:4px;
  font-family:var(--mono); font-size:9px; text-transform:uppercase; letter-spacing:.1em;
  vertical-align:middle; border:1px solid var(--border-medium); color:var(--text-secondary); }}
.use.route {{ color:var(--run); border-color:rgba(249,115,22,.4); }}
.use.trail {{ color:var(--bike); border-color:rgba(34,197,94,.4); }}
.shoe.inconnu .shoe-tag {{ color:var(--text-muted); background:var(--bg-elevated); }}
.shoe.inconnu .gauge-fill {{ background:var(--text-muted); }}
.shoe-tag {{ display:inline-flex; align-items:center; gap:6px; font-family:var(--mono);
  font-size:9.5px; text-transform:uppercase; letter-spacing:.09em; white-space:nowrap;
  padding:4px 9px; border-radius:20px; }}
.shoe-tag i {{ font-style:normal; font-size:11px; line-height:1; }}
.shoe.ok   .shoe-tag {{ color:var(--st-good); background:rgba(12,163,12,.12); }}
.shoe.warn .shoe-tag {{ color:var(--st-warn); background:rgba(250,178,25,.12); }}
.shoe.crit .shoe-tag {{ color:var(--st-crit); background:rgba(208,59,59,.14); }}
.gauge {{ position:relative; height:10px; border-radius:6px; background:var(--bg-elevated); overflow:hidden; }}
.gauge-fill {{ height:100%; border-radius:6px; transition:width .4s; }}
.shoe.ok   .gauge-fill {{ background:var(--st-good); }}
.shoe.warn .gauge-fill {{ background:var(--st-warn); }}
.shoe.crit .gauge-fill {{ background:var(--st-crit); }}
.gauge-over {{ position:absolute; inset:0; border-radius:6px;
  background:repeating-linear-gradient(135deg,transparent 0 5px,rgba(10,10,11,.34) 5px 10px); }}
.shoe-foot {{ display:flex; justify-content:space-between; margin-top:9px;
  font-family:var(--mono); font-size:12px; color:var(--text-secondary); }}
.shoe-foot strong {{ color:var(--text-primary); font-size:14px; }}
.shoe-note {{ margin:12px 0 0; font-size:13px; color:var(--text-secondary); }}
.shoe-meta {{ margin:7px 0 0; font-family:var(--mono); font-size:10px; color:var(--text-muted); }}
.shoes-note {{ margin:14px 0 0; font-size:12.5px; color:var(--text-muted); }}
.prov {{ display:inline-block; margin-left:8px; padding:2px 8px; border-radius:4px;
  background:var(--bg-elevated); font-family:var(--mono); font-size:9.5px;
  text-transform:uppercase; letter-spacing:.08em; color:var(--text-secondary); }}

/* Onglets */
.topbar {{ position:sticky; top:0; z-index:10; background:rgba(10,10,11,.92);
  backdrop-filter:blur(12px); border-bottom:1px solid var(--border-subtle); }}
.topbar .inner {{ max-width:880px; margin:0 auto; padding:14px 20px 0;
  display:flex; flex-wrap:wrap; align-items:baseline; gap:6px 24px; }}
.topbar .brand {{ font-family:var(--serif); font-size:16px; font-weight:600; margin-right:auto; }}
.topbar .brand span {{ font-family:var(--mono); font-size:10.5px; color:var(--accent);
  letter-spacing:.04em; margin-left:8px; }}
.tabs {{ display:flex; gap:4px; margin-left:-12px; }}
.tab {{ appearance:none; background:none; border:0; cursor:pointer;
  font-family:var(--mono); font-size:10.5px; text-transform:uppercase; letter-spacing:.1em;
  color:var(--text-muted); padding:10px 12px 12px; border-bottom:2px solid transparent; }}
.tab:hover {{ color:var(--text-primary); }}
.tab[aria-selected="true"] {{ color:var(--text-primary); border-bottom-color:var(--accent); }}
.tab:focus-visible {{ outline:2px solid var(--accent); outline-offset:-2px; border-radius:4px; }}
[role="tabpanel"][hidden] {{ display:none; }}
#panel-programme {{ height:calc(100vh - 56px); }}
#panel-programme iframe {{ width:100%; height:100%; border:0; display:block; background:var(--bg-primary); }}
.fallback {{ max-width:880px; margin:0 auto; padding:28px 20px; font-size:14px; color:var(--text-secondary); }}
</style>
</head>
<body>

<div class="topbar"><div class="inner">
  <div class="brand">{EVENT} <span>· {EVENT_DATE_FR} · objectif {TARGET_TIME}</span></div>
  <div class="tabs" role="tablist" aria-label="Sections">
    <button class="tab" role="tab" id="tab-suivi" aria-controls="panel-suivi" aria-selected="true">Suivi</button>
    <button class="tab" role="tab" id="tab-programme" aria-controls="panel-programme" aria-selected="false">Programme 30 semaines</button>
  </div>
</div></div>

<section role="tabpanel" id="panel-suivi" aria-labelledby="tab-suivi">
<div class="wrap">
<header>
  <h1>Suivi de préparation</h1>
  <p>Objectif {TARGET_TIME} · allure {TARGET_PACE} · mis à jour le {aujourdhui.strftime('%d/%m/%Y')}</p>
</header>

<div class="tiles">{tuiles}</div>

{bloc_chaussures_html}

<h2>Lecture de la semaine</h2>
{blocs_obs}

<h2>Trajectoires</h2>
{graphe_semaines("Poids", f"Trajectoire cible {POIDS_DEPART} → {POIDS_CIBLE} kg. L'objectif est atteint en S22 : au-delà, la charge d'entraînement prime et le déficit devient contre-productif.", [("Cible", poids_pts_cible, "reference"), ("Pesées", poids_pts_reel, "reel")], 78, 92, lambda v: f"{v:.0f}", c="c-gold")}
{graphe_semaines("Volume hebdomadaire", "Kilomètres de course prévus (barres claires) et réalisés (barres pleines). L'assiduité compte plus que la perfection de chaque séance.", [("Prévu", vol_prevu, "barre_ref"), ("Réalisé", vol_reel, "barre_reel")], 0, 62, lambda v: f"{v:.0f}", c="c-run")}
{bloc_allure}

<h2>Récupération</h2>
{graphe_jours("Sommeil", "Durée par nuit. Zone verte : ta baseline sur 440 nuits (7h00-8h00, moyenne 7h21).", "sommeil_min", lambda v: f"{int(v)//60}h{int(v)%60:02d}", bande=(420, 480))}
{graphe_jours("Variabilité cardiaque (VFC)", "Zone verte : ta baseline Garmin (73–105 ms). En sortir par le bas signale une fatigue accumulée.", "vfc_nuit", lambda v: f"{v:.0f}", bande=(73, 105))}
{graphe_jours("Fréquence cardiaque de repos", "Médiane 46 sur 447 jours (plage 38-62). Une hausse durable au-dessus de 52 — atteint 6 % des jours — est un signal de fatigue ou d'infection.", "fc_repos", lambda v: f"{v:.0f}")}

<footer>
  Généré par <code>rapport.py</code> · sources : plan, MCP Strava, exports Garmin, poids.csv<br>
  Données personnelles — ce fichier reste en local sur ta machine.
</footer>
</div>
</section>

<section role="tabpanel" id="panel-programme" aria-labelledby="tab-programme" hidden>
  <iframe srcdoc="{programme_srcdoc}" title="Programme d'entraînement sur 30 semaines"></iframe>
</section>

<script>
(function () {{
  var tabs = [].slice.call(document.querySelectorAll('[role="tab"]'));
  function activer(id) {{
    tabs.forEach(function (t) {{
      var actif = t.id === id;
      t.setAttribute('aria-selected', actif);
      document.getElementById(t.getAttribute('aria-controls')).hidden = !actif;
    }});
    history.replaceState(null, '', '#' + id.replace('tab-', ''));
  }}
  tabs.forEach(function (t) {{
    t.addEventListener('click', function () {{ activer(t.id); }});
    t.addEventListener('keydown', function (e) {{
      var i = tabs.indexOf(t);
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {{
        e.preventDefault();
        var n = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
        n.focus(); activer(n.id);
      }}
    }});
  }});
  if (location.hash === '#programme') activer('tab-programme');
}})();
</script>
</body>
</html>
"""

OUT.write_text(html, encoding="utf-8")
print(f"Rapport écrit : {OUT}")
print(f"  semaine {sem_actuelle}/30 · J−{jours_restants} · {len(wellness)} jours Garmin · "
      f"{len(pesees)} pesée(s) · {len(journal)} semaine(s) de suivi")
