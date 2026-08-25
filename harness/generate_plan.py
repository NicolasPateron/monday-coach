#!/usr/bin/env python3
"""
Plan generator — writes build/plan.json in the claude-coach schema, plus .ics files.

⚠️ This script is ONE athlete's hand-tuned marathon build, generalised only as far
as its configuration file. The week table, the paces per phase and the session text
below encode specific choices for a specific runner.

**For most people, claude-coach's `/coach` skill is the right tool** — it interviews
you and builds a plan calibrated on your own Strava history. Use this only if you
want to hand-write your own progression and have the rest of the harness consume it.

Configuration lives in `harness/athlete.json` (copy `athlete.example.json`).
That file is gitignored: it holds your race, your target and your measured values.
"""

import json
from datetime import date, timedelta, datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CONFIG = BASE / "harness" / "athlete.json"
if not CONFIG.exists():
    raise SystemExit(
        "harness/athlete.json is missing.\n"
        "Copy harness/athlete.example.json to harness/athlete.json and fill it in."
    )
_cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

def _d(k):
    return date(*map(int, _cfg[k].split("-")))

# ----------------------------------------------------------------------------
# Athlete parameters — all from harness/athlete.json
# ----------------------------------------------------------------------------
ATHLETE = _cfg["athlete"]
EVENT = _cfg["event"]
EVENT_DATE = _d("event_date")
PLAN_START = _d("plan_start")            # a Monday
TOTAL_WEEKS = _cfg["total_weeks"]
TARGET_TIME = _cfg["target_time"]
TARGET_PACE = _cfg["target_pace"]

FC_MAX = _cfg["hr_max"]                  # estimate; NOT used for the zones
LTHR = _cfg["lthr"]                      # measured lactate-threshold heart rate
SEUIL_PACE = _cfg["threshold_pace"]      # measured pace at that threshold
FC_REPOS = _cfg["resting_hr"]
POIDS = _cfg["weight_kg"]

JOURS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
JOURS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

# ----------------------------------------------------------------------------
# Structure : volume hebdo, sortie longue, phase
# (semaine, volume_km, sortie_longue_km, phase, recup, focus)
# ----------------------------------------------------------------------------
WEEKS = [
    (1,  24, 10,  "Reprise",      False, "Reprendre au niveau que tu tenais déjà — rien d'héroïque, rien d'insultant"),
    (2,  27, 12,  "Reprise",      False, "Allonger la sortie longue, zéro intensité"),
    (3,  30, 13,  "Reprise",      False, "Retour à ton volume d'automne 2025 + lignes droites"),
    (4,  24, 11,  "Reprise",      True,  "Semaine allégée + TEST SEUIL 30' (calibrage des zones)"),

    (5,  33, 14,  "Base",         False, "Dépassement de ton volume d'automne 2025"),
    (6,  36, 16,  "Base",         False, "Introduction des côtes courtes"),
    (7,  39, 18,  "Base",         False, "Retour à ton pic historique (34 km/sem, été 2025)"),
    (8,  29, 13,  "Base",         True,  "Récupération — assimilation"),
    (9,  41, 19,  "Base",         False, "Territoire inédit : au-delà de tout ce que tu as fait"),
    (10, 44, 21,  "Base",         False, "Volume + tempo continu"),
    (11, 47, 23,  "Base",         False, "Pic du bloc base"),
    (12, 34, 16,  "Base",         True,  "Récupération + retest seuil"),

    (13, 48, 24,  "Développement",False, "Entrée dans le travail au seuil"),
    (14, 51, 26,  "Développement",False, "Seuil fractionné"),
    (15, 54, 28,  "Développement",False, "Sortie longue à 28 km — au-delà du semi"),
    (16, 38, 19,  "Développement",True,  "Récupération"),
    (17, 50, 25,  "Développement",False, "Découverte de l'allure marathon"),
    (18, 54, 28,  "Développement",False, "Gros volume — dernier bloc avant les fêtes"),
    (19, 42, 21,  "Développement",True,  "Semaine de Noël — volontairement allégée"),
    (20, 36, 17,  "Développement",True,  "Nouvel An — maintien, aucune culpabilité"),

    (21, 50, 24,  "Spécifique",   False, "Relance : retour à l'allure marathon"),
    (22, 54, 27,  "Spécifique",   False, "Dernier gros bloc avant le semi"),
    (23, 42, 21.1,"Spécifique",   False, "SEMI DE TEST — point de décision sur l'objectif"),
    (24, 56, 30,  "Spécifique",   False, "Sortie longue à 30 km avec blocs à allure marathon"),
    (25, 58, 32,  "Spécifique",   False, "32 km — au-delà du mur des 30"),
    (26, 58, 34,  "Spécifique",   False, "RÉPÉTITION GÉNÉRALE — 34 km en 3h21, soit 92 % de la durée de course"),
    (27, 44, 22,  "Spécifique",   True,  "Récupération avant affûtage"),

    (28, 42, 22,  "Affûtage",     True,  "Début de l'affûtage — volume -30 % par rapport au pic"),
    (29, 30, 14,  "Affûtage",     True,  "Affûtage — on garde l'intensité, on coupe le volume"),
    (30, 16, 42.195,"Affûtage",   True,  "SEMAINE DE COURSE — course objectif"),
]

# Allures par phase : (EF_low, EF_high, AM, seuil, vma)  en sec/km
PACES = {
    "Reprise":       (400, 420, 330, 315, 285),   # 6:40-7:00 / 5:30 / 5:15 / 4:45
    "Base":          (383, 405, 325, 308, 275),   # 6:23-6:45 / 5:25 / 5:08 / 4:35
    "Développement": (368, 395, 320, 298, 268),   # 6:08-6:35 / 5:20 / 4:58 / 4:28
    "Spécifique":    (360, 390, 309, 290, 262),   # 6:00-6:30 / 5:09 / 4:50 / 4:22
    "Affûtage":      (360, 390, 309, 290, 262),
}

# Trajets domicile-bureau à vélo, d'après ses données Strava d'avril 2026 :
# aller ≈ 8,7 km / 27 min, retour ≈ 8,7 km / 23 min → 17,4 km et 50 min par jour.
# Intégrés à partir de S5 (mi-septembre), une fois la canicule passée.
VELO_JOURS = {
    0: ("Vélo bureau — récupération active", "Zone 1",
        "Lendemain de sortie longue : les deux trajets en souplesse totale, sans jamais appuyer. "
        "Le vélo draine mieux les jambes que le repos complet — c'est le seul jour où il a une vraie fonction de récupération."),
    1: ("Vélo bureau — souple", "Zone 1-2",
        "Séance qualitative ce soir. Aller et retour tranquilles : tu ne dois pas arriver à ta séance avec les jambes déjà entamées."),
    2: ("Vélo bureau — libre", "Zone 2",
        "Journée sans course. C'est le jour où tu peux mettre un peu de tonus au retour si l'envie est là."),
    3: ("Vélo bureau — souple", "Zone 1-2",
        "Séance qualitative ce soir : reste souple sur les deux trajets."),
    4: ("Vélo bureau — libre", "Zone 2",
        "Veille de week-end. Allure libre, mais pas de sprint : la sortie longue de dimanche est la priorité."),
}

# Répartition du volume hebdo entre les 3 sorties (le reste = sortie longue)
COEF_MAR = {"Reprise": 0.30, "Base": 0.26, "Développement": 0.24, "Spécifique": 0.20, "Affûtage": 0.28}
COEF_JEU = {"Reprise": 0.28, "Base": 0.26, "Développement": 0.26, "Spécifique": 0.24, "Affûtage": 0.26}

def duree_dimanche(wn, phase, sl):
    """Durée réelle de la sortie longue, en tenant compte des blocs à allure marathon.
    Le calcul à l'allure EF seule surestimait fortement (jusqu'à +20 min)."""
    ef_lo, ef_hi, am, seuil, vma = PACES[phase]
    if wn == 30:
        return 217                      # target marathon pace, from TARGET_PACE
    if wn == 23:
        return round(21.0975 * 292 / 60)  # semi à 4:52/km
    if phase in ("Reprise", "Base"):
        return round(sl * (ef_lo + ef_hi) / 2 / 60)
    if phase == "Développement":
        bloc = 10 if sl >= 20 else 6
        return round(((sl - bloc) * ef_hi + bloc * am) / 60)
    if phase == "Spécifique":
        if sl >= 30:                    # 10 km EF + 3x(5 km AM + 1 km trot) + reste EF
            return round((10 * ef_hi + 15 * am + 3 * ef_hi + (sl - 28) * ef_hi) / 60)
        return round(((sl - 12) * ef_hi + 12 * am) / 60)
    return round(((sl - 4) * ef_hi + 4 * am) / 60)

def fmt_pace(sec):
    return f"{sec // 60}:{sec % 60:02d}/km"

def hhmm(total_min):
    h, m = divmod(int(round(total_min)), 60)
    return f"{h}h{m:02d}" if h else f"{m} min"

def texte_renfo(nser, duree, note_charge):
    """Déroulé complet du renfo. UNE SEULE définition : le plan, le programme HTML et
    les descriptions d'agenda en découlent tous, sinon les contenus divergent."""
    return (
        f"{duree} min au poids du corps. DANS CET ORDRE — il n'est pas arbitraire :\n\n"
        f"1. Pont fessier         {nser} × 15\n"
        f"   Réveille les fessiers AVANT fentes et squats. Sans ça, les quadriceps font tout.\n"
        f"2. Fentes               {nser} × 12 / jambe\n"
        f"   Le plus exigeant en équilibre : à faire frais.\n"
        f"3. Squats               {nser} × 15\n"
        f"4. Montées sur pointes  {nser} × 20\n"
        f"5. Gainage ventral      {nser} × 45 s\n"
        f"6. Gainage latéral      {nser} × 30 s / côté\n\n"
        "LE GAINAGE EN DERNIER, jamais en premier : un tronc épuisé au départ te fait perdre "
        "ta stabilité pendant les fentes et les squats — c'est là que les blessures arrivent.\n\n"
        "REPOS\n"
        "• 45-60 s entre deux séries du même exercice\n"
        "• 60-90 s entre deux exercices\n"
        "• 30-45 s entre les séries de gainage\n\n"
        f"Tu enchaînes les {nser} séries d'un exercice avant de passer au suivant, pas en circuit.\n\n"
        f"{note_charge}\n\n"
        "INTENSITÉ : à la dernière répétition tu dois pouvoir en faire 2-3 de plus. Jamais l'échec. "
        "Si la forme se dégrade, arrête la série avant la fin — on construit de la résistance, "
        "pas de la masse.\n\n"
        "Lance Strava dessus (profil « Musculation ») pour que je le voie dans le suivi.")

# ----------------------------------------------------------------------------
# Générateurs de séances
# ----------------------------------------------------------------------------
def seance_mardi(w, phase, vol, recup):
    ef_lo, ef_hi, am, seuil, vma = PACES[phase]
    if phase == "Reprise":
        if w <= 2:
            km = round(vol * COEF_MAR[phase], 1)
            return ("endurance", "Endurance fondamentale",
                    f"{km} km en aisance totale. Tu dois pouvoir tenir une conversation.",
                    km, ef_lo, ef_hi, "Zone 2",
                    f"Échauffement inclus dans l'allure.\n{km} km à {fmt_pace(ef_lo)}–{fmt_pace(ef_hi)}\nFC cible : 137–150 bpm.\n\nRègle absolue : si tu dépasses 150 bpm, tu ralentis. Même si ça te paraît ridiculement lent.")
        km = round(vol * COEF_MAR[phase], 1)
        return ("endurance", "Endurance + lignes droites",
                f"{km} km en EF, puis 6 lignes droites de 100 m.",
                km, ef_lo, ef_hi, "Zone 2",
                f"{km} km à {fmt_pace(ef_lo)}–{fmt_pace(ef_hi)} (FC 137–150)\nPuis 6 × 100 m en accélération progressive, récup 100 m marche.\n\nLes lignes droites réveillent la foulée sans fatiguer. Ce n'est pas une séance dure.")
    if phase == "Base":
        if w in (6, 7):
            km = round(vol * COEF_MAR[phase], 1)
            return ("hills", "Côtes courtes",
                    "Développement de la force spécifique et de l'économie de course.",
                    km, ef_lo, ef_hi, "Zone 4",
                    f"Échauffement 20 min à {fmt_pace(ef_hi)}\n8 × 45 s en côte (pente 4–6 %), effort soutenu mais contrôlé\nRécup : retour en trottinant\nRetour au calme 10 min\n\nTotal ≈ {km} km. Les côtes construisent la force sans le stress d'une piste.")
        km = round(vol * COEF_MAR[phase], 1)
        return ("intervals", "Fractionné court 30/30",
                "Réveil de la VMA, format court et digeste.",
                km, ef_lo, ef_hi, "Zone 5",
                f"Échauffement 20 min à {fmt_pace(ef_hi)}\n2 × (8 × 30 s à {fmt_pace(vma)} / 30 s trot), 3 min entre les blocs\nRetour au calme 10 min\n\nTotal ≈ {km} km. Sur les 30 s : rapide mais jamais en sprint.")
    if phase == "Développement":
        km = round(vol * COEF_MAR[phase], 1)
        if w in (13, 14, 17):
            return ("intervals", "VMA — 5 × 3 min",
                    "Développement de la VO2max.",
                    km, ef_lo, ef_hi, "Zone 5",
                    f"Échauffement 20 min à {fmt_pace(ef_hi)}\n5 × 3 min à {fmt_pace(vma)} / récup 2 min trot\nRetour au calme 10 min\n\nTotal ≈ {km} km. Tu dois finir la 5e répétition à la même allure que la 1re.")
        return ("intervals", "VMA — 6 × 1000 m",
                "Séance de référence, mesurable d'un cycle à l'autre.",
                km, ef_lo, ef_hi, "Zone 5",
                f"Échauffement 20 min à {fmt_pace(ef_hi)}\n6 × 1000 m à {fmt_pace(seuil - 8)} / récup 2 min trot\nRetour au calme 10 min\n\nTotal ≈ {km} km. Note tes temps : c'est ton indicateur de progression n°1.")
    if phase == "Spécifique":
        km = round(vol * COEF_MAR[phase], 1)
        if w == 23:
            return ("endurance", "Déverrouillage avant semi",
                    "Séance courte de réveil musculaire avant la course de dimanche.",
                    km, ef_lo, ef_hi, "Zone 2",
                    f"{km} km à {fmt_pace(ef_lo)}–{fmt_pace(ef_hi)}\nPuis 4 × 30 s à allure semi, récup 1 min\n\nObjectif : rester frais. On ne cherche rien ici.")
        return ("intervals", "Seuil — 3 × 8 min",
                "Extension du seuil lactique, le déterminant n°1 de la perf marathon.",
                km, ef_lo, ef_hi, "Zone 4",
                f"Échauffement 20 min à {fmt_pace(ef_hi)}\n3 × 8 min à {fmt_pace(seuil)} / récup 3 min trot\nRetour au calme 10 min\n\nTotal ≈ {km} km. FC cible sur les blocs : 159–170.")
    # Affûtage
    km = round(vol * COEF_MAR[phase], 1)
    if w == 30:
        return ("recovery", "Déverrouillage",
                "Dernière sortie active avant le marathon.",
                km, ef_lo, ef_hi, "Zone 2",
                f"{km} km très facile à {fmt_pace(ef_hi)}\nPuis 4 × 100 m à allure marathon.\n\nJambes légères. Rien de plus.")
    return ("tempo", "Rappels à allure marathon",
            "Maintien des sensations d'allure sans fatigue.",
            km, ef_lo, ef_hi, "Zone 3",
            f"Échauffement 15 min\n4 × 4 min à {fmt_pace(am)} / récup 2 min trot\nRetour au calme 10 min\n\nTotal ≈ {km} km. Ça doit te sembler facile — c'est le but de l'affûtage.")

def seance_jeudi(w, phase, vol, recup):
    ef_lo, ef_hi, am, seuil, vma = PACES[phase]
    km = round(vol * COEF_JEU[phase], 1)
    if w == 4:
        return ("threshold", "⚑ TEST SEUIL 30 MINUTES",
                "Validation terrain du seuil lactique estimé par Garmin (169 bpm / 5:13 km).",
                km, ef_lo, ef_hi, "Zone 4-5",
                f"Échauffement 15 min facile\n30 MIN à l'allure la plus rapide que tu peux tenir sans exploser (comme une course de 30 min)\nRetour au calme 10 min\n\nRÉFÉRENCE À BATTRE OU CONFIRMER : 169 bpm à 5:13/km (estimation Garmin)\n\nÀ RELEVER ET À ME DONNER :\n• FC moyenne des 20 dernières minutes → ton LTHR réel\n• Allure moyenne sur les 30 min → ton allure seuil réelle\n\nPourquoi ce test alors que Garmin donne déjà une valeur : l'estimation Garmin est algorithmique et repose sur tes courses de juin-juillet, à volume très faible. Après 4 semaines de reprise régulière, un test réel donne une base fiable — et servira de point de comparaison au retest de la semaine 12.\n\nTerrain plat, pars prudemment : la plupart des gens partent trop vite et s'écroulent à 20 min.")
    if w == 12:
        return ("threshold", "⚑ RETEST SEUIL 30 MINUTES",
                "Deuxième test : on mesure les gains de 8 semaines et on recale les allures.",
                km, ef_lo, ef_hi, "Zone 4-5",
                f"Même protocole qu'en semaine 4.\nÉchauffement 15 min / 30 min à fond contrôlé / 10 min retour au calme\n\nDonne-moi FC moyenne + allure : je réajuste tout le reste du plan.")
    if phase == "Reprise":
        return ("endurance", "Endurance fondamentale",
                f"{km} km faciles.", km, ef_lo, ef_hi, "Zone 2",
                f"{km} km à {fmt_pace(ef_lo)}–{fmt_pace(ef_hi)}\nFC 137–150 bpm.\n\nSi tu es fatigué, raccourcis mais sors. L'habitude compte plus que la distance.")
    if phase == "Base":
        if w >= 9:
            return ("tempo", "Tempo continu",
                    "Travail d'endurance active, la base du futur travail seuil.",
                    km, ef_lo, ef_hi, "Zone 3",
                    f"Échauffement 15 min à {fmt_pace(ef_hi)}\n20 min à {fmt_pace(am)} (FC 151–158)\nRetour au calme 10 min\n\nTotal ≈ {km} km. Allure « confortablement soutenue » : tu peux dire une phrase, pas tenir une conversation.")
        return ("endurance", "Endurance fondamentale",
                f"{km} km en zone 2.", km, ef_lo, ef_hi, "Zone 2",
                f"{km} km à {fmt_pace(ef_lo)}–{fmt_pace(ef_hi)}\nFC 137–150 bpm.")
    if phase == "Développement":
        if w in (15, 18):
            return ("threshold", "Seuil — 2 × 15 min",
                    "Le format le plus rentable pour un marathonien.",
                    km, ef_lo, ef_hi, "Zone 4",
                    f"Échauffement 20 min à {fmt_pace(ef_hi)}\n2 × 15 min à {fmt_pace(seuil)} / récup 4 min trot\nRetour au calme 10 min\n\nTotal ≈ {km} km. FC 159–170.")
        return ("tempo", "Tempo progressif",
                "Endurance active avec finish plus rapide.",
                km, ef_lo, ef_hi, "Zone 3",
                f"Échauffement 15 min\n25 min à {fmt_pace(am)}, puis 8 min à {fmt_pace(seuil)}\nRetour au calme 10 min\n\nTotal ≈ {km} km.")
    if phase == "Spécifique":
        if w == 23:
            return ("recovery", "Footing de décharge",
                    "Repos actif avant le semi de dimanche.", round(vol*0.18,1), ef_lo, ef_hi, "Zone 1-2",
                    f"{round(vol*0.18,1)} km très facile à {fmt_pace(ef_hi)}.\nAucune intensité. Tu prépares dimanche.")
        return ("tempo", "Allure marathon — 2 × 20 min",
                "Séance clé : ancrer l'allure cible dans les jambes.",
                km, ef_lo, ef_hi, "Zone 3",
                f"Échauffement 15 min à {fmt_pace(ef_hi)}\n2 × 20 min à {fmt_pace(am)} / récup 5 min trot\nRetour au calme 10 min\n\nTotal ≈ {km} km. C'est TON allure de course : {fmt_pace(am)}. Apprends à la reconnaître sans regarder la montre.")
    # Affûtage
    if w == 30:
        return ("rest", "Repos", "Repos complet avant le voyage.", 0, 0, 0, "—",
                "Repos. Prépare ton sac, tes ravitaillements, tes chaussures.")
    return ("tempo", "Allure marathon — 15 min",
            "Entretien de l'allure.", km, ef_lo, ef_hi, "Zone 3",
            f"Échauffement 15 min\n15 min à {fmt_pace(am)}\nRetour au calme 10 min\n\nTotal ≈ {km} km.")

def seance_dimanche(w, phase, sl, recup):
    ef_lo, ef_hi, am, seuil, vma = PACES[phase]
    if w == 30:
        return ("race", "🏁 {EVENT.upper()}", "Jour J.", 42.195, 309, 309, "Allure course",
                f"{EVENT.upper()} — objectif {TARGET_TIME}\n\nPlan d'allure :\n• km 1–5 : {fmt_pace(315)} — pars VOLONTAIREMENT trop lentement\n• km 5–32 : {fmt_pace(309)} — allure de croisière, FC < 160\n• km 32–42 : {fmt_pace(309)} ou mieux si les sensations sont là\n\nRavitaillement : 60 g de glucides/heure dès le km 8, puis toutes les 35–40 min. Bois à chaque poste.\n\nLa course commence au km 30. Tout ce qui précède n'est qu'une mise en place.")
    if w == 23:
        return ("race", "🏁 SEMI-MARATHON DE TEST", "Course-test : point de décision sur l'objectif.", 21.1, 292, 292, "Allure semi",
                f"SEMI-MARATHON — objectif 1h42–1h44 ({fmt_pace(292)})\n\nC'est le juge de paix de ta prépa :\n• 1h42–1h44 → objectif confirmé, on continue tel quel\n• 1h45–1h47 → 3h40–3h45, on ajuste légèrement\n• 1h48+ → on recale honnêtement sur 3h45–3h50\n\nPars sur {fmt_pace(295)} les 5 premiers km, puis accélère progressivement. Ne pars jamais avec les premiers.")
    if phase in ("Reprise", "Base"):
        corps = (f"{sl} km à {fmt_pace(ef_lo)}–{fmt_pace(ef_hi)}\n"
                 "FC 137–150 bpm — ne dépasse JAMAIS 150.\n\n")
        if sl < 16:
            corps += (f"Tu as déjà couru 21,1 km deux fois : {sl} km n'est pas un défi pour toi et "
                      "je ne prétends pas le contraire. C'est le créneau du dimanche — le plus long "
                      "des trois de la semaine, celui qui deviendra 34 km en février.\n\n"
                      "Le chiffre est plafonné par le volume hebdomadaire, pas par ta capacité. "
                      f"Si {sl} km t'agace, ajoute 2 km : ça reste dans la marge.\n\n"
                      "CE QUI COMPTE ICI : l'allure, pas la distance. Ta sortie de 16 km du 28/06 "
                      "était courue à 99,8 % de ton seuil — c'est cette habitude qu'on corrige. "
                      f"{sl + 2} km à {fmt_pace(ef_hi)} valent mieux que {sl} à {fmt_pace(370)}.")
        else:
            corps += ("C'est la séance la plus importante de ta semaine. Elle doit être facile de "
                      "bout en bout. Si tu finis épuisé, tu es allé trop vite.")
        return ("long", f"Sortie longue — {sl} km", "Développement de l'endurance de base.",
                sl, ef_lo, ef_hi, "Zone 2", corps)
    if phase == "Développement":
        bloc = 10 if sl >= 20 else 6
        return ("long", f"Sortie longue — {sl} km", "Endurance + premier travail d'allure en fin de sortie.",
                sl, ef_lo, ef_hi, "Zone 2-3",
                f"{sl - bloc} km à {fmt_pace(ef_lo)}–{fmt_pace(ef_hi)} (FC 137–150)\nPuis {bloc} km à {fmt_pace(am)}\n\nTotal {sl} km. Finir une sortie longue à allure marathon apprend à ton corps à puiser dans les graisses puis à tenir l'allure fatigué. C'est exactement la contrainte du km 32.")
    if phase == "Spécifique":
        if sl >= 30:
            return ("long", f"Sortie longue — {sl} km", "Sortie clé du plan : simulation des contraintes du marathon.",
                    sl, ef_lo, ef_hi, "Zone 2-3",
                    f"10 km à {fmt_pace(ef_hi)}\n3 × 5 km à {fmt_pace(am)} / récup 1 km trot\nFin à {fmt_pace(ef_hi)} jusqu'à {sl} km\n\nTeste ta nutrition de course : 60 g de glucides/heure, exactement ce que tu prendras le jour J. Rien de nouveau le jour J.")
        bloc = 12
        return ("long", f"Sortie longue — {sl} km", "Endurance spécifique avec gros bloc à allure marathon.",
                sl, ef_lo, ef_hi, "Zone 2-3",
                f"{sl - bloc} km à {fmt_pace(ef_hi)} (FC 137–150)\nPuis {bloc} km à {fmt_pace(am)}\n\nTotal {sl} km. Ravitaillement toutes les 40 min à l'entraînement aussi.")
    # Affûtage
    return ("long", f"Sortie longue allégée — {sl} km", "Maintien de l'endurance, volume réduit.",
            sl, ef_lo, ef_hi, "Zone 2",
            f"{sl - 4} km à {fmt_pace(ef_hi)}\nPuis 4 km à {fmt_pace(am)}\n\nTotal {sl} km. Tu vas te sentir plein d'énergie et vouloir en faire plus. Ne le fais pas.")

# ----------------------------------------------------------------------------
# Structures exportables vers Garmin (.fit)
#
# Contrainte du convertisseur claude-coach (src/viewer/lib/export/fit.ts) :
# seules les unités d'intensité "hr_zone" / "percent_lthr" produisent une cible
# dans le fichier .fit. "pace_zone" retombe sur targetType="open".
# → on encode donc les cibles en FC, et on met l'allure dans le NOM de l'étape,
#   qui s'affiche sur la montre.
# ----------------------------------------------------------------------------
Z1, Z2, Z3, Z4, Z5 = (120, 137), (137, 150), (151, 158), (159, 170), (172, 186)

def _st(stype, unit, value, hr, name):
    """Étape avec cible de FC."""
    return {"type": stype, "name": name[:24],
            "duration": {"unit": unit, "value": value},
            "intensity": {"unit": "hr_zone", "value": 2,
                          "valueLow": hr[0], "valueHigh": hr[1], "description": name}}

def _open(stype, unit, value, name):
    """Étape sans cible imposée (test maximal, course)."""
    return {"type": stype, "name": name[:24],
            "duration": {"unit": unit, "value": value},
            "intensity": {"unit": "rpe", "value": 9, "description": name}}

def _rep(n, steps, name):
    return {"type": "interval_set", "name": name[:24], "repeats": n, "steps": steps}

def build_structure(t, wn, phase, slot, km, sl=None):
    ef_lo, ef_hi, am, seuil, vma = PACES[phase]
    EF   = f"EF {fmt_pace(ef_hi)}"
    AM   = f"All. mara {fmt_pace(am)}"
    SEUIL= f"Seuil {fmt_pace(seuil)}"
    VMA  = f"VMA {fmt_pace(vma)}"
    wu20 = [_st("warmup", "minutes", 20, Z2, f"Échauff. {fmt_pace(ef_hi)}")]
    wu15 = [_st("warmup", "minutes", 15, Z2, f"Échauff. {fmt_pace(ef_hi)}")]
    cd10 = [_st("cooldown", "minutes", 10, Z1, "Retour au calme")]

    # ---- MARDI ----
    if slot == "mar":
        if phase == "Reprise":
            main = [_st("work", "kilometers", km, Z2, EF)]
            if wn >= 3:
                main.append(_rep(6, [_st("work", "meters", 100, Z5, "Ligne droite"),
                                     _st("recovery", "meters", 100, Z1, "Marche")], "6 x 100 m"))
            return {"warmup": [], "main": main, "cooldown": []}
        if phase == "Base":
            if wn in (6, 7):
                return {"warmup": wu20, "cooldown": cd10, "main": [
                    _rep(8, [_st("work", "seconds", 45, Z4, "Côte 45 s"),
                             _st("recovery", "seconds", 90, Z1, "Retour trot")], "8 x 45 s côte")]}
            return {"warmup": wu20, "cooldown": cd10, "main": [
                _rep(16, [_st("work", "seconds", 30, Z5, VMA),
                          _st("recovery", "seconds", 30, Z1, "Trot")], "16 x 30/30")]}
        if phase == "Développement":
            if wn in (13, 14, 17):
                return {"warmup": wu20, "cooldown": cd10, "main": [
                    _rep(5, [_st("work", "minutes", 3, Z5, VMA),
                             _st("recovery", "minutes", 2, Z1, "Trot")], "5 x 3 min")]}
            return {"warmup": wu20, "cooldown": cd10, "main": [
                _rep(6, [_st("work", "meters", 1000, Z5, f"1000 m {fmt_pace(seuil - 8)}"),
                         _st("recovery", "minutes", 2, Z1, "Trot")], "6 x 1000 m")]}
        if phase == "Spécifique":
            if wn == 23:
                return {"warmup": [], "cooldown": [], "main": [
                    _st("work", "kilometers", km, Z2, EF),
                    _rep(4, [_st("work", "seconds", 30, Z4, "All. semi"),
                             _st("recovery", "minutes", 1, Z1, "Trot")], "4 x 30 s")]}
            return {"warmup": wu20, "cooldown": cd10, "main": [
                _rep(3, [_st("work", "minutes", 8, Z4, SEUIL),
                         _st("recovery", "minutes", 3, Z1, "Trot")], "3 x 8 min seuil")]}
        if wn == 30:
            return {"warmup": [], "cooldown": [], "main": [
                _st("work", "kilometers", km, Z2, EF),
                _rep(4, [_st("work", "meters", 100, Z3, AM),
                         _st("recovery", "meters", 100, Z1, "Marche")], "4 x 100 m")]}
        return {"warmup": wu15, "cooldown": cd10, "main": [
            _rep(4, [_st("work", "minutes", 4, Z3, AM),
                     _st("recovery", "minutes", 2, Z1, "Trot")], "4 x 4 min all. mara")]}

    # ---- JEUDI ----
    if slot == "jeu":
        if wn in (4, 12):
            return {"warmup": wu15, "cooldown": cd10, "main": [
                _open("work", "minutes", 30, "TEST 30 min a fond")]}
        if phase == "Reprise" or (phase == "Base" and wn < 9):
            return {"warmup": [], "cooldown": [], "main": [_st("work", "kilometers", km, Z2, EF)]}
        if phase == "Base":
            return {"warmup": wu15, "cooldown": cd10, "main": [
                _st("work", "minutes", 20, Z3, AM)]}
        if phase == "Développement":
            if wn in (15, 18):
                return {"warmup": wu20, "cooldown": cd10, "main": [
                    _rep(2, [_st("work", "minutes", 15, Z4, SEUIL),
                             _st("recovery", "minutes", 4, Z1, "Trot")], "2 x 15 min seuil")]}
            return {"warmup": wu15, "cooldown": cd10, "main": [
                _st("work", "minutes", 25, Z3, AM),
                _st("work", "minutes", 8, Z4, SEUIL)]}
        if phase == "Spécifique":
            if wn == 23:
                return {"warmup": [], "cooldown": [], "main": [
                    _st("work", "kilometers", km, Z1, "Décharge très facile")]}
            return {"warmup": wu15, "cooldown": cd10, "main": [
                _rep(2, [_st("work", "minutes", 20, Z3, AM),
                         _st("recovery", "minutes", 5, Z1, "Trot")], "2 x 20 min all. mara")]}
        return {"warmup": wu15, "cooldown": cd10, "main": [_st("work", "minutes", 15, Z3, AM)]}

    # ---- DIMANCHE ----
    if wn == 30:
        return {"warmup": [], "cooldown": [], "main": [
            _open("work", "kilometers", 42.195, "MARATHON 5:09/km")]}
    if wn == 23:
        return {"warmup": [], "cooldown": [], "main": [
            _open("work", "kilometers", 21.1, "SEMI 4:52/km")]}
    if phase in ("Reprise", "Base"):
        return {"warmup": [], "cooldown": [], "main": [_st("work", "kilometers", sl, Z2, EF)]}
    if phase == "Développement":
        bloc = 10 if sl >= 20 else 6
        return {"warmup": [], "cooldown": [], "main": [
            _st("work", "kilometers", round(sl - bloc, 1), Z2, EF),
            _st("work", "kilometers", bloc, Z3, AM)]}
    if phase == "Spécifique":
        if sl >= 30:
            return {"warmup": [], "cooldown": [], "main": [
                _st("work", "kilometers", 10, Z2, EF),
                _rep(3, [_st("work", "kilometers", 5, Z3, AM),
                         _st("recovery", "kilometers", 1, Z1, "Trot")], "3 x 5 km all. mara"),
                _st("work", "kilometers", round(sl - 28, 1), Z2, EF)]}
        return {"warmup": [], "cooldown": [], "main": [
            _st("work", "kilometers", round(sl - 12, 1), Z2, EF),
            _st("work", "kilometers", 12, Z3, AM)]}
    return {"warmup": [], "cooldown": [], "main": [
        _st("work", "kilometers", round(sl - 4, 1), Z2, EF),
        _st("work", "kilometers", 4, Z3, AM)]}

# ----------------------------------------------------------------------------
# Construction du plan
# ----------------------------------------------------------------------------
weeks_json = []
ics_events = []   # (date, heure_debut, duree_min, titre, description)

for (wn, vol, sl, phase, recup, focus) in WEEKS:
    wstart = PLAN_START + timedelta(weeks=wn - 1)
    wend = wstart + timedelta(days=6)
    ef_lo, ef_hi, am, seuil, vma = PACES[phase]

    days = []
    total_km = 0.0
    total_min = 0.0
    n_runs = 0
    velo_km = 0.0
    n_velo = 0

    for di in range(7):
        d = wstart + timedelta(days=di)
        workouts = []

        if di == 0:   # Lundi — repos
            workouts.append({
                "id": f"w{wn}-lun-repos", "sport": "rest", "type": "rest",
                "name": "Repos", "description": "Récupération complète après la sortie longue.",
                "completed": False,
                "humanReadable": "Repos complet. La progression se construit pendant le repos, pas pendant l'effort."
            })

        elif di == 1:  # Mardi — qualité
            t, name, desc, km, plo, phi, zone, hr = seance_mardi(wn, phase, vol, recup)
            dur = round(km * ((plo + phi) / 2) / 60) if km else 0
            workouts.append({
                "id": f"w{wn}-mar-run", "sport": "run", "type": t, "name": name,
                "description": desc, "durationMinutes": dur,
                "distanceMeters": int(km * 1000), "primaryZone": zone,
                "targetPace": {"low": fmt_pace(plo), "high": fmt_pace(phi)},
                "structure": build_structure(t, wn, phase, "mar", km),
                "humanReadable": hr, "completed": False
            })
            total_km += km; total_min += dur; n_runs += 1
            ics_events.append((d, "19:00", dur, f"🏃 S{wn} — {name}", hr))

        elif di == 2:  # Mercredi — renfo optionnel
            nser = 2 if wn <= 3 else 3          # montée en charge : 2 séries avant S4
            duree_renfo = 20 if nser == 2 else 30
            note_charge = (
                "MONTÉE EN CHARGE : 2 séries seulement jusqu'à la semaine 3, puis 3. "
                "Les courbatures de la première séance viennent des 24 séries d'emblée — "
                "le corps s'adapte vite, la même séance en produira bien moins dans 15 jours."
                if nser == 2 else "Volume complet : 3 séries.")
            workouts.append({
                "id": f"w{wn}-mer-renfo", "sport": "strength", "type": "technique",
                "name": "Renforcement (flexible)", "description": "À caler quand tu as le temps — mercredi est une suggestion.",
                "durationMinutes": duree_renfo, "primaryZone": "—", "completed": False,
                "humanReadable": texte_renfo(nser, duree_renfo, note_charge) +
                "\n\nÀ déplacer librement dans la semaine. Deux séances valent mieux qu'une, une vaut mieux que zéro."
            })
            total_min += 25

        elif di == 3:  # Jeudi
            t, name, desc, km, plo, phi, zone, hr = seance_jeudi(wn, phase, vol, recup)
            if t == "rest":
                workouts.append({
                    "id": f"w{wn}-jeu-repos", "sport": "rest", "type": "rest",
                    "name": name, "description": desc, "completed": False, "humanReadable": hr})
            else:
                dur = round(km * ((plo + phi) / 2) / 60) if km else 0
                if wn in (4, 12):        # séances de test : 15' échauffement + 30' test + 10' retour au calme
                    km, dur = 9.0, 55
                workouts.append({
                    "id": f"w{wn}-jeu-run", "sport": "run", "type": t, "name": name,
                    "description": desc, "durationMinutes": dur,
                    "distanceMeters": int(km * 1000), "primaryZone": zone,
                    "targetPace": {"low": fmt_pace(plo), "high": fmt_pace(phi)},
                    "structure": build_structure(t, wn, phase, "jeu", km),
                    "humanReadable": hr, "completed": False})
                total_km += km; total_min += dur; n_runs += 1
                ics_events.append((d, "19:00", dur, f"🏃 S{wn} — {name}", hr))

        elif di == 4:  # Vendredi — renfo n°2 (créneau le plus éloigné d'une course)
            workouts.append({
                "id": f"w{wn}-ven-renfo", "sport": "strength", "type": "technique",
                "name": "Renforcement #2 (flexible)",
                "description": "Deuxième séance de renfo si tu as le temps.",
                "durationMinutes": duree_renfo, "primaryZone": "—", "completed": False,
                "humanReadable": texte_renfo(nser, duree_renfo, note_charge) +
                "\n\nVENDREDI plutôt que samedi : avec des courses mardi, jeudi et dimanche, c'est le "
                "créneau le plus éloigné d'une séance de course — deux jours avant la sortie longue. "
                "En faire le samedi reviendrait à arriver dimanche sur des jambes entamées.\n\n"
                "Si tu ne dois en faire qu'une dans la semaine, garde celle du mercredi : elle est "
                "encadrée par deux sorties faciles."})

        elif di == 5:  # Samedi — repos, veille de sortie longue
            workouts.append({
                "id": f"w{wn}-sam-repos", "sport": "rest", "type": "rest",
                "name": "Repos", "description": "Veille de sortie longue : jambes fraîches.",
                "completed": False,
                "humanReadable": "Repos. Marche ou vélo très facile si tu en as envie, rien de plus.\n\n"
                "Pas de renforcement aujourd'hui : c'est la veille de ta séance la plus importante "
                "de la semaine."})

        else:  # Dimanche — sortie longue
            t, name, desc, km, plo, phi, zone, hr = seance_dimanche(wn, phase, sl, recup)
            dur = duree_dimanche(wn, phase, sl)
            workouts.append({
                "id": f"w{wn}-dim-run", "sport": "run" if t != "race" else "race",
                "type": t, "name": name, "description": desc, "durationMinutes": dur,
                "distanceMeters": int(km * 1000), "primaryZone": zone,
                "targetPace": {"low": fmt_pace(plo), "high": fmt_pace(phi)},
                "structure": build_structure(t, wn, phase, "dim", km, sl),
                "humanReadable": hr, "completed": False})
            total_km += km; total_min += dur; n_runs += 1
            heure = "09:00" if km >= 25 else "09:30"
            ics_events.append((d, heure, dur, f"🏃 S{wn} — {name}", hr))

        # Trajets domicile-bureau à vélo (lun-ven), à partir de S5 (fin de canicule)
        if di <= 4 and wn >= 5:
            vname, vzone, vtxt = VELO_JOURS[di]
            workouts.append({
                "id": f"w{wn}-{di}-velo", "sport": "bike", "type": "recovery",
                "name": vname, "description": "Aller-retour bureau : 2 × 8,7 km, ~50 min au total.",
                "durationMinutes": 50, "distanceMeters": 17400, "primaryZone": vzone,
                "completed": False,
                "humanReadable": f"Aller ≈ 8,7 km / 27 min · Retour ≈ 8,7 km / 23 min\n\n{vtxt}\n\nCe n'est pas une séance en plus : c'est ton trajet habituel, simplement piloté. Lance Strava dessus."})
            total_min += 50
            velo_km += 17.4
            n_velo += 1

        days.append({"date": d.isoformat(), "dayOfWeek": JOURS[di], "workouts": workouts})

    weeks_json.append({
        "weekNumber": wn,
        "startDate": wstart.isoformat(),
        "endDate": wend.isoformat(),
        "phase": phase,
        "focus": focus,
        "targetHours": round(total_min / 60, 1),
        "isRecoveryWeek": recup,
        "days": days,
        "summary": {
            "totalHours": round(total_min / 60, 1),
            "bySport": {
                "run": {"sessions": n_runs, "hours": round((total_min - n_velo * 50 - 50) / 60, 1), "km": round(total_km, 1)},
                "bike": {"sessions": n_velo, "hours": round(n_velo * 50 / 60, 1), "km": round(velo_km, 1)},
                "strength": {"sessions": 2, "hours": 0.83},
            }
        }
    })

plan = {
    "version": "1.0",
    "meta": {
        "id": "marathon-build",
        "athlete": ATHLETE,
        "event": EVENT,
        "eventDate": EVENT_DATE.isoformat(),
        "planStartDate": PLAN_START.isoformat(),
        "planEndDate": EVENT_DATE.isoformat(),
        "createdAt": "2026-08-16T00:00:00Z",
        "updatedAt": "2026-08-16T00:00:00Z",
        "totalWeeks": TOTAL_WEEKS,
        "generatedBy": "Claude Coach"
    },
    "preferences": {"swim": "meters", "bike": "kilometers", "run": "kilometers", "firstDayOfWeek": "monday"},
    "assessment": {
        "foundation": {
            "raceHistory": [
                "Aucun marathon couru à ce jour",
                "RECORD 10 km : 48:27 (03/07/2025, 4:50/km) — projection Riegel 3h43, VDOT ≈ 42",
                "Semi-marathon : 1h57:03 (03/06/2025, 5:33/km, en sortie d'entraînement à allure conversationnelle)",
                "9 km à 4:49/km en test (17/11/2025) — meilleur 5 km : 24:03, FC moyenne 173, FC max 181",
                "Autres sorties longues : 21,1 km (26/10/2025, 2h12) et 20,3 km (24/08/2025)",
                "Trails : Trail des Fouées 18,2 km (07/06/2026), Trail de Valbonne 8,9 km (02/08/2026)",
                "10 km le plus récent : 52:34 (11/01/2026) — reflète la baisse de forme, pas le potentiel"
            ],
            "peakTrainingLoad": 34,
            "foundationLevel": "intermediate",
            "yearsInSport": 2
        },
        "currentForm": {
            "weeklyVolume": {"total": 2.0, "swim": 0, "bike": 0, "run": 2.0},
            "longestSessions": {"swim": 0, "bike": 21, "run": 21.1},
            "consistency": 0
        },
        "strengths": [
            {"sport": "run", "evidence": "Socle aérobie important et sous-estimé au premier examen : bloc de construction avril-juillet 2025 à 30-34 km/semaine (127, 142 puis 150 km/mois), suivi de 4 mois à 17-22 km/semaine (août-nov. 2025). Capacité déjà démontrée, il s'agit de la retrouver, pas de la créer"},
            {"sport": "run", "evidence": "Potentiel de vitesse confirmé : 10 km en 48:27 (03/07/2025) et 9 km à 4:49/km avec FC moyenne 173 (17/11/2025) — ce dernier suggère un LTHR nettement supérieur aux 169 bpm actuels, valeur d'un athlète désentraîné"},
            {"sport": "bike", "evidence": "Capacité à enchaîner de gros volumes vélo (≈30 sorties en avril 2026) — levier de cross-training sans impact"}
        ],
        "limiters": [
            {"sport": "run", "evidence": "Régularité : trois coupures ≥ 4 semaines en 12 mois (déc. 2025, avril 2026, juil.-août 2026)"},
            {"sport": "run", "evidence": "Volume actuel très faible : 15,9 km sur les 7 dernières semaines, en 2 sorties seulement (7,0 km le 30/07 et 8,9 km le 02/08). Coupure principale du 28/06 au 30/07 (32 jours), puis 14 jours sans courir depuis le 02/08"},
            {"sport": "run", "evidence": "Intensité mal calibrée : sortie longue du 28/06/2026 courue à 168,7 bpm de moyenne, soit 99,8 % du seuil lactique mesuré (169 bpm) — une sortie longue courue au seuil. Zones Strava fondées sur une FC max erronée de 200"},
            {"sport": "run", "evidence": "Body mass is a real performance lever — roughly 2 s/km per kilo, about 1.4 min on a marathon. Address it in the Base phase only, never during the Specific phase."}
        ],
        "constraints": [
            "3 sorties course maximum par semaine (mardi, jeudi, dimanche)",
            "Renforcement musculaire à horaire libre",
            "Trajets domicile-bureau à vélo (2 x 8,7 km/jour) intégrés au plan à partir de S5, une fois la canicule passée",
            "Sortie longue plafonnée à 3 h"
        ]
    },
    "zones": {
        "run": {
            "hr": {
                "lthr": LTHR,
                "zones": [
                    {"zone": 1, "name": "Récupération", "percentLow": 0,  "percentHigh": 81,  "hrLow": 0,   "hrHigh": 137},
                    {"zone": 2, "name": "Endurance fondamentale", "percentLow": 81, "percentHigh": 89, "hrLow": 137, "hrHigh": 150},
                    {"zone": 3, "name": "Tempo / Allure marathon", "percentLow": 90, "percentHigh": 93, "hrLow": 151, "hrHigh": 158},
                    {"zone": 4, "name": "Seuil", "percentLow": 94, "percentHigh": 100, "hrLow": 159, "hrHigh": 170},
                    {"zone": 5, "name": "VMA", "percentLow": 103, "percentHigh": 110, "hrLow": 174, "hrHigh": 186}
                ]
            }
        }
    },
    "phases": [
        {"name": "Reprise", "startWeek": 1, "endWeek": 4, "focus": "Réinstaller l'habitude, recalibrer les zones",
         "weeklyHoursRange": {"low": 2, "high": 3}, "keyWorkouts": ["Sortie longue progressive", "Test seuil 30 min"],
         "physiologicalGoals": ["Réhabituer tendons et articulations à l'impact", "Fixer des zones FC exactes"]},
        {"name": "Base", "startWeek": 5, "endWeek": 12, "focus": "Construire le socle aérobie",
         "weeklyHoursRange": {"low": 3, "high": 5}, "keyWorkouts": ["Sortie longue", "Côtes courtes", "Tempo continu"],
         "physiologicalGoals": ["Densité mitochondriale", "Capillarisation", "Oxydation des graisses"]},
        {"name": "Développement", "startWeek": 13, "endWeek": 20, "focus": "Élever le seuil et allonger la sortie longue",
         "weeklyHoursRange": {"low": 4, "high": 6}, "keyWorkouts": ["Seuil 2×15 min", "VMA 6×1000 m", "Sortie longue 24 km"],
         "physiologicalGoals": ["Élévation du seuil lactique", "Clairance du lactate", "VO2max"]},
        {"name": "Spécifique", "startWeek": 21, "endWeek": 27, "focus": "Ancrer l'allure marathon, pic de volume",
         "weeklyHoursRange": {"low": 5, "high": 7}, "keyWorkouts": ["Semi de test", "Sortie longue 32 km", "2×20 min allure marathon"],
         "physiologicalGoals": ["Économie de course à allure cible", "Endurance spécifique", "Stratégie nutritionnelle"]},
        {"name": "Affûtage", "startWeek": 28, "endWeek": 30, "focus": "Réduire le volume, préserver l'intensité",
         "weeklyHoursRange": {"low": 2, "high": 4}, "keyWorkouts": ["Rappels allure marathon", "Marathon"],
         "physiologicalGoals": ["Recharge glycogénique", "Réparation musculaire", "Fraîcheur nerveuse"]}
    ],
    "weeks": weeks_json,
    "raceStrategy": {
        "event": {"name": EVENT, "date": EVENT_DATE.isoformat(), "type": "marathon",
                  "distances": {"swim": 0, "bike": 0, "run": 42.195}},
        "pacing": {
            "run": {"targetPace": "5:09/km", "targetHR": "152-160 (90-95 % du seuil lactique)",
                    "notes": "DÉPART 8h30 environ, Fori Imperiali (vagues de 8h00 à 9h00 ; vérifié sur le site officiel le 23/08/2026 — confirmer ta vague à l'inscription).\n\nkm 1-5 à 5:15 (frein volontaire), km 5-32 à 5:09, km 32-42 à 5:09 ou mieux.\n\nPARCOURS : plat (altitude entre 8 et 31 m sur tout le tracé). La difficulté n'est ni le dénivelé ni la chaleur — c'est le REVÊTEMENT. Environ 6 km de sampietrini, les pavés basaltiques du centre historique, dont des portions dans le dernier tiers, là où les jambes ne pardonnent plus. Second facteur : des rues étroites et 35 000 coureurs.\n\nSUR LES PAVÉS : raccourcis la foulée, pose médio-pied, ne talonne pas, relâche les épaules. Ne cherche pas à tenir l'allure au mètre près sur ces sections — reprends après. Glissants s'il pleut."}
        },
        "nutrition": {
            "preRace": "3 h avant : 100–120 g de glucides, pauvre en fibres (pain blanc/miel, banane). Boire 500 ml jusqu'à 1 h avant.",
            "during": {"carbsPerHour": 60, "fluidPerHour": "500-600ml",
                       "products": ["Gels testés à l'entraînement", "Boisson d'effort", "Eau à chaque poste"]},
            "notes": "Premier gel au km 8, puis toutes les 35-40 min. RIEN de nouveau le jour J : tout doit avoir été testé sur les sorties longues des semaines 24 à 26."
        },
        "taper": {"startDate": (EVENT_DATE - timedelta(weeks=3)).isoformat(), "volumeReduction": 50,
                  "notes": "Volume -35 % en S28, -50 % en S29, -70 % en S30. L'intensité est maintenue : c'est ce qui préserve la fraîcheur sans perdre la forme."}
    }
}

out_json = str(BASE / "build" / "plan.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(plan, f, ensure_ascii=False, indent=2)

# ----------------------------------------------------------------------------
# Génération .ics (semaines 5 à 30 — les semaines 1 à 4 vont dans Google Agenda)
# ----------------------------------------------------------------------------
def make_ics(events, path, uid_prefix):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:-//Monday Coach//{EVENT}//FR",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:" + EVENT]
    for i, (d, heure, dur, titre, desc) in enumerate(events):
        h, m = map(int, heure.split(":"))
        start = datetime(d.year, d.month, d.day, h, m)
        end = start + timedelta(minutes=max(dur, 20))
        desc_esc = desc.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")
        titre_esc = titre.replace(",", "\\,").replace(";", "\\;")
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid_prefix}-{i}@claude-coach",
            f"DTSTAMP:20260816T120000Z",
            f"DTSTART;TZID=Europe/Paris:{start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND;TZID=Europe/Paris:{end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{titre_esc}",
            f"DESCRIPTION:{desc_esc}",
            "BEGIN:VALARM", "TRIGGER:-PT2H", "ACTION:DISPLAY",
            "DESCRIPTION:Séance dans 2 h", "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines))

cutoff = PLAN_START + timedelta(weeks=4)     # début S5
ics_s5_30 = [e for e in ics_events if e[0] >= cutoff]
make_ics(ics_s5_30, str(BASE / "build" / "programme-S05-a-S30.ics"), "rome-s5")
make_ics(ics_events, str(BASE / "build" / "programme-complet-S01-a-S30.ics"), "rome-full")

# ----------------------------------------------------------------------------
# Récap console
# ----------------------------------------------------------------------------
print(f"JSON      : {out_json}")
print(f"ICS S5-30 : {len(ics_s5_30)} séances")
print(f"ICS total : {len(ics_events)} séances")
print()
tot = sum(w["summary"]["bySport"]["run"]["km"] for w in weeks_json)
print(f"Volume total course : {tot:.0f} km sur 30 semaines")
print(f"Semaine 1  : {WEEKS[0][1]} km  |  Pic (S25) : {WEEKS[24][1]} km")
print()
print("Phase          Semaines   Dates                      Vol. moyen")
for ph in ["Reprise", "Base", "Développement", "Spécifique", "Affûtage"]:
    ws = [w for w in WEEKS if w[3] == ph]
    a, b = ws[0][0], ws[-1][0]
    d1 = PLAN_START + timedelta(weeks=a - 1)
    d2 = PLAN_START + timedelta(weeks=b - 1) + timedelta(days=6)
    avg = sum(w[1] for w in ws) / len(ws)
    print(f"{ph:<14} S{a:02d}-S{b:02d}    {d1.strftime('%d/%m/%y')} → {d2.strftime('%d/%m/%y')}    {avg:.0f} km/sem")
print()
print("Jalons :")
for wn, label in [(4, "Test seuil 30'"), (12, "Retest seuil"), (23, "SEMI DE TEST"), (26, "Sortie la plus longue (32 km)"), (30, "RACE DAY")]:
    w = next(x for x in WEEKS if x[0] == wn)
    ds = PLAN_START + timedelta(weeks=wn - 1)
    de = ds + timedelta(days=6)
    print(f"  S{wn:02d}  {ds.strftime('%d/%m/%Y')} → {de.strftime('%d/%m/%Y')}  {label}")
print()
print("Semaines 1 à 4 (à créer dans Google Agenda) :")
for e in ics_events:
    if e[0] < cutoff:
        print(f"  {e[0].strftime('%a %d/%m')} {e[1]}  {e[3]}  ({e[2]} min)")
