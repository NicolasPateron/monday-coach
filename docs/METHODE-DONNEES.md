# Méthode de lecture des données

> *Ce document est en français. Sa traduction est la
> [première contribution évidente](../README.md#limitations).*

Ce document est **contraignant**. Il existe parce que quatre bugs d'extraction ont produit
des analyses fausses entre le 17 et le 20 août 2026, toutes découvertes par l'athlète en
comparant à son application. Aucune de ces erreurs n'était techniquement difficile : elles
ont survécu parce qu'aucune sortie n'était confrontée à sa source.

---

## 1. Les trois principes

**Une extraction non recoupée n'est pas une donnée.** Tant qu'un chiffre n'a pas été
confronté à une seconde source ou à une référence externe, il n'est qu'une hypothèse sur
le contenu d'un fichier. On ne construit pas un récit dessus.

**Une fenêtre courte ne définit pas une norme.** Sept jours ne sont pas une baseline. La
première erreur de cette prépa fut de conclure « sommeil 6h06, principal levier » sur une
semaine qui s'est révélée être le pire creux de l'année. Toute norme se calcule sur
plusieurs mois, ou se déclare provisoire.

**L'absence de donnée n'est pas une donnée d'absence.** Le MCP Strava ne renvoie ni les
séries de musculation ni la température : en avoir déduit que la montre ne les avait pas
détectées était faux. Avant de conclure qu'une chose n'a pas eu lieu, vérifier que l'outil
sait la voir.

---

## 2. Séquence obligatoire

**Utiliser `./relancer.sh`**, jamais les scripts un par un.

```
1.  Collecter          Strava (MCP) · zips Garmin · poids.csv
2.  Enrichir           scripts/meteo.py            températures
3.  VALIDER            scripts/valider.py          ← BLOQUANT, code 0 exigé
4.  Agréger            scripts/dashboard.py
5.  Marquer le fait    scripts/marquer_realise.py  ← AVANT le rendu
6.  Rendre le plan     claude-coach → programme.html
7.  Restituer          scripts/rapport.py
```

**L'ordre des étapes 5 et 6 est critique.** `generate_plan.py` réécrit le plan de zéro
et efface l'état des séances faites ; le programme doit être rendu après le marquage. Une
inversion le 21/08/2026 a fait retomber la progression affichée à 0 %. `rapport.py` refuse
maintenant de tourner si `programme.html` est antérieur à `plan.json`.

**L'étape 3 est un verrou, pas un avertissement.** Si `valider.py` sort en code 1, aucun
chiffre n'est communiqué avant traitement de l'anomalie. Un bilan faux est pire qu'un bilan
retardé : il oriente 30 semaines d'entraînement.

---

## 2 bis. Règle de synchronisation des destinations

**Toute modification touche plusieurs destinations. Les vérifier une par une est
obligatoire, pas optionnel.** Le 22/08/2026, une séance de renfo déplacée dans Google
Agenda n'a été reportée nulle part ailleurs : ni dans le plan, ni dans le programme, ni
dans le support. l'athlète a dû croiser les sources lui-même pour s'en apercevoir — et un
second défaut se cachait derrière : l'appariement des séances faites se faisant sur la date
exacte, la séance déplacée n'aurait jamais été cochée.

### Les sept destinations

| # | Destination | Mise à jour par |
|---|---|---|
| 1 | `scripts/generate_plan.py` | **la source** — toute modification structurelle passe par là |
| 2 | `build/plan.json` | `generate_plan.py` |
| 3 | `build/programme.html` | rendu claude-coach, **après** `marquer_realise.py` |
| 4 | `marathon.html` | `rapport.py` |
| 5 | `garmin-fit/` **+ les deux zips** | `gen-fit.ts` **puis `zip_fit.py`** — `gen-fit.ts` n'écrit QUE les `.fit` |
| 6 | **Google Agenda** | charges utiles produites par `scripts/agenda.py`, poussées par MCP |
| 7 | Tâche du lundi + mémoire + ce document | à la main |

### Le contenu se rédige UNE fois, dans le plan

**Aucune description de séance n'est écrite à la main dans Google Agenda.** Le texte d'un
événement est une fonction déterministe de `build/plan.json` :

    description = en-tête de semaine (calculé) + humanReadable de la séance

Toute rédaction directe dans l'agenda crée une deuxième source de vérité, et deux sources
divergent toujours. Constaté le 22/08/2026 : la même séance de renfo existait en deux
versions incompatibles — jour, horaire, nombre d'exercices, consigne d'intensité — et le
renfo du mercredi n'existait pas du tout dans l'agenda. Les trois courses portaient elles
aussi un texte sans rapport avec le plan. Quand une consigne doit changer, elle change dans
`generate_plan.py`, jamais ailleurs.

**Trois axes tenus alignés, pas un seul :**

| Axe | Porté par | Vérifié par |
|---|---|---|
| Date et heure | `plan.json`, ou `completedAt` si la séance est faite | `agenda.py verifier` |
| Complétion | Strava via `marquer_realise.py` → préfixe ✅ et couleur grise | `agenda.py verifier` |
| Contenu | `humanReadable` du plan, au caractère près | empreinte SHA-256 tronquée |

**Séance faite = date réelle.** Tant qu'une séance n'est pas réalisée, l'agenda porte la
date prescrite. Dès que Strava la confirme, l'événement prend la date, l'heure et la durée
réelles. Un agenda qui ment sur le passé ne sert à rien, et un renfo déplacé dans la
semaine reste légitime — c'est le plan qui note l'écart, pas l'agenda qui le cache.

### Ce qui n'est pas vérifié n'est pas synchronisé

Le 24/08/2026, `garmin-fit.zip` datait du 17/08 alors que les séances avaient changé
entre-temps : on allait charger d'anciennes séances dans la montre. **Le contrôle
était vert.** Il comptait les `.fit` du dossier et leur fraîcheur, mais le dossier n'est
pas ce qu'on charge dans la montre — le zip l'est, et personne ne le regardait.

La leçon vaut au-delà de ce cas : **ajouter une étape au pipeline ne suffit pas.** Une
étape peut échouer, être contournée, ou être lancée à la main dans le mauvais ordre. Tant
qu'aucun test ne constate son résultat, la destination peut dériver en silence — et un
contrôle qui affiche « ✓ » sur une chaîne cassée est pire que pas de contrôle.

Règle : **toute destination ajoutée à la liste doit venir avec son test dans
`verifier_sync.py`**, et ce test doit être validé en injectant le défaut qu'il est censé
attraper. Les zips : périmé et absent, vérifiés le 24/08/2026.


### Procédure

1. `./relancer.sh` couvre les destinations 1 à 5, puis lance `scripts/verifier_sync.py`.
2. Si l'agenda doit changer :

```
python3 scripts/agenda.py generer <semaine>   # charges utiles exactes
   → pousser par MCP, sans reformuler un seul mot
   → relire par list_events, enregistrer dans suivi/agenda-reel.json
python3 scripts/verifier_sync.py              # doit sortir en code 0
```

3. `verifier_sync.py` compare l'empreinte du texte **réellement présent** dans l'agenda à
   celle attendue. Il échoue si un événement manque, si sa date ou son heure diffèrent, si
   son texte diffère d'un caractère, s'il traîne un événement absent du plan, ou si
   `agenda-reel.json` est plus ancien que `plan.json` — un relevé périmé ne prouve rien.
   Les quatre défauts ont été injectés le 22/08/2026 pour vérifier qu'ils sont bien
   attrapés : ils le sont.
4. La comparaison porte sur le relevé de l'agenda, **jamais sur ce que je crois y avoir
   poussé**. C'est la seule vérification qui vaut.

**Ne jamais modifier une seule destination.** Un changement d'horaire ou de formulation
dans l'agenda est un changement de plan : il se répercute partout, ou il n'a pas lieu.

## 3. Les trois tests, et ce qu'ils attrapent

| Test | Principe | Bug qu'il aurait détecté |
|---|---|---|
| **Variance nulle** | Un champ constant sur des centaines de jours est presque toujours le mauvais champ | `restingHeartRate` figé à 43-44 sur 447 jours |
| **Bornes physiologiques** | Sommeil 4-12 h · FC repos 35-70 · phases ≤ durée | Sommeil de 24 min, sieste de 16h21 |
| **Recoupement de sources** | Sur les jours communs, l'export RGPD et les zips doivent concorder | Les quatre bugs, sans exception |

Le troisième est le plus puissant : il ne suppose rien sur la physiologie, seulement que
deux extractions du même fait doivent donner le même chiffre.

---

## 4. Registre des pièges rencontrés

À relire avant toute nouvelle ingestion.

**Champs de référence pris pour des mesures du jour.** `restingHeartRate` est une moyenne
glissante ; la valeur du jour est **`currentDayRestingHeartRate`**. Le piège existait dans
les zips quotidiens *et* dans l'`UDSFile` de l'export RGPD. Signature : variance quasi
nulle.

**Durées reconstruites par sommation d'intervalles.** Sommer les écarts entre marqueurs de
phase de sommeil sous-estimait jusqu'à **4 heures**. La durée vient des **événements de
session** (`sleepEvents` start/stop). Règle : chercher un champ ou un événement qui donne
la grandeur directement avant de la recalculer.

**Deux définitions pour un même nom.** « Sommeil » désignait le temps au lit dans une source
et le temps endormi dans l'autre — 7 min d'écart, série incohérente. Fixer la définition
avant de mélanger des sources.

**Derniers jours partiels.** Un export s'arrête à l'heure de sa génération : 70 pas au lieu
de 4 986. Marquer et écarter les compteurs de journée du dernier jour couvert.

**Compteurs cumulés tronqués par l'heure de l'export.** Le champ `steps` des fichiers
`monitoring` n'est pas un incrément : c'est un **compteur cumulé de la journée**, remis à
zéro à minuit local (vérifié le 24/08/2026 — 4502 pas à 22h00 UTC le 19/08, puis 74 à
23h56 : la remise à zéro tombe à 22h00 UTC, soit minuit à Paris en été). Et l'export
quotidien s'arrête à l'heure exacte du téléchargement. Un export du matin ne livre donc
qu'une demi-matinée : **893 pas le 20/08/2026**, jour d'une sortie de 6,7 km le soir. Lu
brut, c'est un effondrement de l'activité — soit exactement le signal d'alerte précoce que
l'on surveille. Le zip du lendemain ne rattrape rien : le compteur est déjà reparti à zéro.
Un jour n'est un total réel que s'il porte un **relevé de clôture de minuit**
(`pas_arret == "00:00"`) ; c'est sur ces jours-là, et seulement ceux-là, que les deux
sources concordent (7 jours comparables, écart nul). Les autres sont marqués
`pas_partiel: true` et signalés par `valider.py`. **Conséquence pratique : télécharger
l'export quotidien le lendemain, pas le matin même.**

Tentative écartée le 24/08/2026, à ne pas rejouer : filtrer les relevés par date locale
avant d'en prendre le maximum paraissait plus rigoureux, mais s'écartait de la référence
RGPD de 469 à 1824 pas sur les 6 jours comparables. **Le recoupement de sources prime sur
le raisonnement** : l'agrégation brute a été restaurée et seul le diagnostic conservé.
Reste une question ouverte, documentée et non tranchée : le relevé de clôture porte
l'horodatage local `00:00`, donc l'attribution d'un total à sa journée civile mériterait
une vérification dédiée. Sans incidence sur la détection de tendance, qui est l'usage réel.

**Fenêtres récentes non représentatives.** `sample_race_pace` de Strava renvoie un record
sur fenêtre glissante, pas le record absolu : 52:30 affiché contre 48:27 réel. Balayer
l'historique complet avant de conclure sur une référence de performance.

**Écrasement de fichiers édités à la main.** `chaussures.json` est saisi manuellement ;
l'import historique le régénérait depuis un export périmé. Tout fichier édité à la main est
protégé en écriture par les scripts.

**Effets saisonniers pris pour des progrès.** La chaleur élève la FC à effort constant
(~0,65 bpm/°C au-dessus de 15 °C). Sans correction, l'allure à 145 bpm gagnait ~20 s/km
d'août à mars par simple refroidissement. Corriger, et **toujours afficher la valeur brute
à côté de la corrigée**.

---

## 5. Champs de référence

| Grandeur | Source | Champ |
|---|---|---|
| Durée de sommeil | `SLEEP_DATA.fit` · `sleepData.json` | événements start/stop, **jamais** la somme des phases |
| FC de repos | `WELLNESS.fit` · `UDSFile` | **`currentDayRestingHeartRate`** |
| VFC | `HRV_STATUS.fit` uniquement | `lastNightAverage` + `baselineBalanced*` |
| Pas | `monitoring` | somme des maxima par type d'activité — **valide seulement si `pas_arret == "00:00"`** |
| VO2max | `MetricsMaxMetData` | `vo2MaxValue`, sport `RUNNING` |
| Chaussures | `chaussures.json` | **saisie manuelle**, jamais l'export |
| Température | Open-Meteo | via `scripts/meteo.py` |

Convention Garmin : **une nuit est attribuée au jour du réveil.** Le zip du 20 contient la
nuit du 19 au 20.

---

## 6. Traitement des valeurs douteuses

On ne supprime jamais une donnée. On la **marque** (`sommeil_fiable: false`), on la
conserve, et on l'exclut des moyennes et des graphiques. Une valeur effacée est une
information perdue ; une valeur marquée reste auditable.

---

## 7. Formulation

Distinguer systématiquement, dans tout bilan :

- **mesuré** — lu dans une source validée ;
- **dérivé** — calculé, avec la formule et son incertitude (la correction thermique est une
  estimation, pas une loi) ;
- **hypothèse** — à confirmer, avec ce qui la confirmerait et sous quel délai.

Trois estimations empilées donnent une fourchette, pas un chiffre. Le dire.

Et lorsqu'un chiffre paraît faux à l'athlète : **il a raison jusqu'à preuve du contraire.**
C'est vrai quatre fois sur quatre à ce jour.


---

## 8. Enseignements tirés des données corrigées (20/08/2026)

**La FC de repos est son meilleur baromètre de forme, et il est fiable.** Corrélation de
rang de +0,47 avec la prédiction marathon de Garmin sur 15 mois : 42,4 au pic de juillet-août
2025 (prédiction 3h52), 49,4 au creux de janvier-avril 2026 (prédiction 4h30). Aujourd'hui
44,8 — soit **à mi-chemin, plus près du pic que du creux**. C'est un indicateur gratuit,
quotidien, sans test.

**Le sommeil n'explique rien de sa FC de repos.** Après une nuit de moins de 6h30 (n=72) :
46,4 bpm. Après plus de 8 h (n=135) : 46,0. Écart de 0,4 bpm — inexistant. Ne pas
construire de raisonnement liant les deux chez lui.

**Le stress et la respiration accompagnent les pics de FC de repos.** Les six jours au-delà
de 55 bpm montrent tous un stress de 45-66 (contre 37 en moyenne) et une respiration de
13,6-18,4 (contre 12,5). Le 24/02/2026 cumule FC 62, sommeil 2h24, stress 66, respiration
18,4 — profil d'un épisode infectieux, non d'une simple fatigue d'entraînement. Utiliser le
trio FC + stress + respiration plutôt que la FC seule.

**Son ratio de charge aiguë/chronique n'a jamais été dangereux.** Sur 15 mois, un seul mois
au-delà de 1,4 (mars 2026, à 1,48). La montée de volume prévue est donc à surveiller pour
un motif inédit : il n'a **jamais** connu de charge chronique élevée durablement.

**Le volume de pas reste le signal d'alerte le plus net.** 11 935/jour au pic, 6 497 au
creux, 7 443 aujourd'hui. Il décroche avant les courses, pas après.
