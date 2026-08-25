#!/usr/bin/env python3
"""Descriptions Google Agenda dérivées du plan — jamais rédigées à la main.

Le plan (`build/plan.json`) est la source unique. Ce script en déduit la charge
utile exacte de chaque événement, puis relit l'agenda réel pour vérifier que le
titre, la date ET le texte correspondent au caractère près.

    python3 harness/agenda.py generer 1
        → affiche les événements à créer/mettre à jour + écrit suivi/agenda-attendu.json

    python3 harness/agenda.py verifier 1 --reel suivi/agenda-reel.json
        → compare l'agenda réel à l'attendu, code 1 si un écart subsiste

`suivi/agenda-reel.json` est le vidage brut de `list_events` (MCP Google Agenda)
sur la semaine. La comparaison porte sur ce qui est réellement dans l'agenda,
pas sur ce que je crois y avoir mis : c'est la seule vérification qui vaut.
"""
import argparse, hashlib, json, sys, unicodedata
from datetime import datetime, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PLAN = RACINE / "build" / "plan.json"
ATTENDU = RACINE / "suivi" / "agenda-attendu.json"
# Seule façon sanctionnée de déplacer l'heure d'une séance sans toucher au plan :
# {"id_seance": "HH:MM"}. Retoucher l'heure directement dans Google Agenda la ferait
# rediverger au prochain contrôle. Sert aux contraintes personnelles (autre rendez-vous
# ce soir-là) qui ne relèvent pas de l'entraînement.
HORAIRES = RACINE / "suivi" / "agenda-horaires.json"

# Heures canoniques. Toute autre heure dans l'agenda est un écart, pas une variante.
HEURES = {"run": "19:00", "race": "09:30", "strength": "18:30"}
COULEURS = {"run": "9", "race": "11", "strength": "10"}   # bleu · rouge · vert
COULEUR_FAITE = "8"                                       # gris : séance déjà réalisée
JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def exceptions():
    if not HORAIRES.exists():
        return {}
    return {k: v for k, v in json.loads(HORAIRES.read_text(encoding="utf-8")).items()
            if not k.startswith("_")}


def heure_seance(w, date, forcees=None):
    if w["sport"] in ("rest", "bike"):
        return None
    if forcees and w["id"] in forcees:
        return forcees[w["id"]]
    if date.weekday() == 6:                                  # sortie longue
        return "09:00" if (w.get("distanceMeters", 0) / 1000) >= 25 else "09:30"
    return HEURES.get(w["sport"], "19:00")


def titre(numero_semaine, w):
    icone = {"run": "🏃", "race": "🏁", "strength": "💪"}.get(w["sport"], "•")
    detail = ""
    if "km" in w["name"] or "min" in w["name"]:
        detail = ""                                          # le nom porte déjà la mesure
    elif w.get("distanceMeters"):
        detail = f" — {w['distanceMeters'] / 1000:g} km"
    elif w.get("durationMinutes"):
        detail = f" — {w['durationMinutes']} min"
    # La complétion se lit dans le titre : l'agenda affiche le même état que le HTML.
    fait = "✅ " if w.get("completed") else ""
    return f"{fait}{icone} S{numero_semaine} — {w['name']}{detail}"


def description(w, sem, total_semaines):
    """Le corps EST le humanReadable du plan. Seul s'y ajoute un en-tête calculé
    depuis le plan lui-même — l'agenda n'affiche pas le contexte de semaine que
    le HTML montre dans son interface. Rien n'est rédigé à la main."""
    km = sem.get("summary", {}).get("bySport", {}).get("run", {}).get("km")
    volume = f" · {km:g} km" if km else ""
    recup = " · SEMAINE DE RÉCUPÉRATION" if sem.get("isRecoveryWeek") else ""
    entete = f"SEMAINE {sem['weekNumber']}/{total_semaines} — {sem['phase']}{volume}{recup}"
    return f"{entete}\n\n{w['humanReadable']}"


def empreinte(txt):
    """Insensible aux espaces et à la forme Unicode : Google renormalise parfois le texte."""
    plat = unicodedata.normalize("NFC", txt).replace("\r\n", "\n")
    plat = "\n".join(ligne.strip() for ligne in plat.split("\n"))
    plat = "\n".join(l for l in plat.split("\n") if l)
    return hashlib.sha256(plat.encode()).hexdigest()[:16]


def evenements(plan, numero_semaine):
    sem = next((s for s in plan["weeks"] if s["weekNumber"] == numero_semaine), None)
    if sem is None:
        sys.exit(f"Semaine {numero_semaine} absente du plan.")
    total_semaines = len(plan["weeks"])
    forcees = exceptions()
    out = []
    for jour in sem["days"]:
        date = datetime.strptime(jour["date"], "%Y-%m-%d")
        for w in jour["workouts"]:
            h = heure_seance(w, date, forcees)
            if h is None:
                continue
            # Séance faite → l'agenda porte la date RÉELLE (Strava), pas la date
            # prescrite : un renfo déplacé dans la semaine reste légitime, et un
            # agenda qui ment sur le passé ne sert à rien. Séance à venir → date du plan.
            jour_effectif, heure_effective = jour["date"], h
            if w.get("completed") and w.get("completedAt"):
                jour_effectif = str(w["completedAt"])[:10]
                if len(str(w["completedAt"])) >= 16:
                    heure_effective = str(w["completedAt"])[11:16]
            debut = datetime.strptime(f"{jour_effectif} {heure_effective}", "%Y-%m-%d %H:%M")
            duree = (w.get("actualDuration") if w.get("completed") else None) \
                    or w.get("durationMinutes") or 30
            texte = description(w, sem, total_semaines)
            out.append({
                "id_seance": w["id"],
                "semaine": numero_semaine,
                "jour_fr": JOURS_FR[debut.weekday()],
                "jour_prescrit": jour["date"],
                "deplacee": jour_effectif != jour["date"],
                "titre": titre(numero_semaine, w),
                "debut": debut.isoformat(),
                "fin": (debut + timedelta(minutes=duree)).isoformat(),
                "couleur": COULEUR_FAITE if w.get("completed") else COULEURS.get(w["sport"], "8"),
                "description": texte,
                "empreinte": empreinte(texte),
                "realise": bool(w.get("completed")),
            })
    return out


def cmd_generer(args):
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    evs = evenements(plan, args.semaine)
    ATTENDU.parent.mkdir(exist_ok=True)
    tout = json.loads(ATTENDU.read_text(encoding="utf-8")) if ATTENDU.exists() else {}
    precedent = tout.get(str(args.semaine), {})
    inchange = precedent.get("evenements") == evs
    tout[str(args.semaine)] = {
        "modifie_le": precedent["modifie_le"] if inchange and precedent.get("modifie_le")
                      else datetime.now().isoformat(timespec="seconds"),
        "evenements": evs}
    ATTENDU.write_text(json.dumps(tout, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evs, ensure_ascii=False, indent=2))
    print(f"\n→ {len(evs)} événements attendus, écrits dans {ATTENDU.relative_to(RACINE)}",
          file=sys.stderr)


def cmd_verifier(args):
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    attendus = {e["empreinte"]: e for e in evenements(plan, args.semaine)}
    attendus_liste = list(attendus.values())

    chemin = Path(args.reel)
    if not chemin.is_absolute():
        chemin = RACINE / chemin
    if not chemin.exists():
        print(f"✗ Aucun relevé d'agenda ({chemin.relative_to(RACINE)}).")
        print("  Lance list_events sur la semaine et enregistre la réponse dans ce fichier.")
        return 1
    # Périmé = relu AVANT le dernier changement réel de contenu. Une simple
    # régénération à l'identique ne périme rien.
    if ATTENDU.exists():
        hist = json.loads(ATTENDU.read_text(encoding="utf-8")).get(str(args.semaine), {})
        modifie = hist.get("modifie_le")
        if modifie and datetime.fromisoformat(modifie).timestamp() > chemin.stat().st_mtime:
            print(f"✗ Relevé d'agenda périmé : les séances de la semaine {args.semaine} ont "
                  f"changé le {modifie[:16].replace('T', ' à ')}, le relevé est antérieur.")
            print("  Pousse les charges utiles à jour, puis relis l'agenda (list_events).")
            return 1

    reels = json.loads(chemin.read_text(encoding="utf-8"))
    if isinstance(reels, dict):
        reels = reels.get("events", reels.get("items", []))

    ecarts, apparies = [], set()
    for att in attendus_liste:
        jour = att["debut"][:10]
        # Appariement par titre d'abord (le jour peut avoir été déplacé à tort)
        cands = [r for r in reels if r.get("summary", "").strip() == att["titre"]]
        if not cands:
            cands = [r for r in reels
                     if str(r.get("start", {}).get("dateTime", ""))[:10] == jour
                     and att["titre"].split("—")[-1].strip()[:12] in r.get("summary", "")]
        if not cands:
            ecarts.append((att["titre"], "ABSENT de l'agenda"))
            continue
        reel = cands[0]
        apparies.add(id(reel))
        debut_reel = str(reel.get("start", {}).get("dateTime", ""))[:16]
        if debut_reel[:10] != jour:
            ecarts.append((att["titre"], f"date agenda {debut_reel[:10]} ≠ plan {jour}"))
        elif debut_reel[11:16] != att["debut"][11:16]:
            ecarts.append((att["titre"], f"heure agenda {debut_reel[11:16]} ≠ plan {att['debut'][11:16]}"))
        emp_reel = empreinte(reel.get("description", "") or "")
        if emp_reel != att["empreinte"]:
            ecarts.append((att["titre"], f"CONTENU divergent (agenda {emp_reel} ≠ plan {att['empreinte']})"))

    for r in reels:
        s = r.get("summary", "")
        if id(r) not in apparies and ("S%d —" % args.semaine) in s:
            ecarts.append((s, "présent dans l'agenda mais absent du plan — à supprimer"))

    if ecarts:
        print(f"✗ Agenda semaine {args.semaine} : {len(ecarts)} écart(s)")
        for t, m in ecarts:
            print(f"   • {t}\n     {m}")
        return 1
    print(f"✓ Agenda semaine {args.semaine} : {len(attendus_liste)} événements alignés "
          f"(date, heure et contenu identiques au plan)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generer"); g.add_argument("semaine", type=int)
    v = sub.add_parser("verifier"); v.add_argument("semaine", type=int)
    v.add_argument("--reel", default="suivi/agenda-reel.json")
    a = ap.parse_args()
    sys.exit(cmd_generer(a) or 0 if a.cmd == "generer" else cmd_verifier(a))
