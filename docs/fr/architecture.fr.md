> **Traduction française de [architecture.md](../architecture.md).** La version anglaise fait foi.

# Sous le capot

Tout ce qui est ici existe parce que quelque chose a cassé pendant une vraie préparation marathon.
Rien n'a été conçu à l'avance.

---

## Une commande, un seul ordre valide

```bash
./harness/relancer.sh            # rafraîchissement hebdomadaire
./harness/relancer.sh --plan 2   # après un changement de plan, pour la semaine 2
```

| Étape | Script | Pourquoi elle est ici |
|---|---|---|
| 1 | `generate_plan.py` | Source de vérité. Réécrit le plan de zéro — ce qui efface l'état de complétion |
| 2 | `meteo.py` | Renseigne la température de la séance, **avant** toute analyse de FC |
| 3 | `valider.py` | Bloque la chaîne sur des données anormales |
| 4 | `dashboard.py` | Croise plan, Strava, bien-être et poids |
| 5 | `marquer_realise.py` → rendu du viewer | Complétion marquée **avant** le rendu, jamais après |
| 6 | `gen-fit.ts` → `zip_fit.py` | `gen-fit.ts` n'écrit que les `.fit` — **jamais les zips** |
| 7 | `rapport.py` | Produit le tableau de bord |
| 8 | `verifier_sync.py` | Vérifie chaque destination, sort en 1 en cas de dérive |

**L'ordre n'est pas stylistique.** Rendre le viewer avant de marquer les séances faites a un jour
fait retomber six semaines de progression visible à 0 % : `generate_plan.py` réécrit le plan et
efface `completed`, donc le viewer doit être rendu *après* la réintégration des données Strava.
`rapport.py` refuse désormais de tourner si le viewer rendu est antérieur au plan.

---

## Sept destinations, jamais une seule

| Destination | Écrite par |
|---|---|
| `harness/generate_plan.py` | **la source** — les changements structurels passent par là |
| `build/plan.json` | `generate_plan.py` |
| `build/programme.html` (le viewer de claude-coach) | rendu du viewer, **après** `marquer_realise.py` |
| `dashboard.html` | `rapport.py` |
| `garmin-fit/` **et les deux zips** | `gen-fit.ts` **puis** `zip_fit.py` |
| **Google Agenda** | charges utiles d'`agenda.py`, poussées par MCP |
| Tâche planifiée, mémoire, docs | à la main |

Changer l'horaire d'une séance dans l'agenda est un changement de plan. Il se répercute partout, ou
il n'a pas lieu.

---

## Le texte de l'agenda est généré, jamais saisi

**Aucune description de séance n'est jamais écrite à la main dans Google Agenda.** Le texte d'un
événement est une fonction déterministe du plan :

```
description = en-tête de semaine généré + le champ humanReadable de la séance
```

Taper directement dans l'agenda crée une deuxième source de vérité, et deux sources divergent
toujours. En pratique, ça a produit deux versions incompatibles de la même séance de renfo — jour,
horaire, nombre d'exercices et consigne d'intensité différents — pendant qu'une troisième séance
n'existait pas du tout dans l'agenda.

**Trois axes tenus alignés, pas un seul :**

| Axe | Porté par | Vérifié par |
|---|---|---|
| Date et heure | le plan, ou la date réelle une fois la séance faite | `agenda.py verifier` |
| Complétion | Strava via `marquer_realise.py` → ✅ et gris | `agenda.py verifier` |
| Contenu | `humanReadable`, au caractère près | empreinte SHA-256 tronquée |

**Une séance faite porte sa date, son heure et sa durée réelles**, pas celles prescrites. Une séance
déplacée dans la semaine reste légitime ; un agenda qui ment sur le passé ne sert à rien.

```bash
python3 harness/agenda.py generer <semaine>   # charges utiles exactes
   # pousser par MCP sans reformuler un seul mot
   # relire l'agenda dans suivi/agenda-reel.json
python3 harness/verifier_sync.py              # doit sortir en 0
```

La comparaison porte sur **ce qui est réellement dans l'agenda**, jamais sur ce qu'on croit y avoir
poussé. Elle échoue sur : un événement manquant, une date ou une heure différente, un texte
divergent d'un caractère, un événement présent dans l'agenda mais absent du plan, ou un relevé plus
ancien que le dernier changement réel de contenu.

Pour déplacer l'heure d'une séance sans toucher au plan — un rendez-vous personnel ce soir-là —
utilise `suivi/agenda-horaires.json`. La déplacer directement dans Google Agenda la ferait signaler
comme divergente à chaque passage suivant.

> Google Agenda n'interprète pas le Markdown. Les astérisques s'affichent littéralement — utilise
> les capitales.

---

## Lire ses données sans se raconter d'histoires

Protocole complet dans [`METHODE-DONNEES.md`](../METHODE-DONNEES.md). Il existe parce que quatre
bugs d'extraction ont produit des conclusions assurées et fausses — trois d'entre elles sur le
sommeil. Les quatre ont été attrapés par le coureur comparant les chiffres à sa propre application
Garmin, aucun par un test. D'où les tests.

`valider.py` doit passer avant tout bilan chiffré.

| Test | Principe | Ce qu'il aurait attrapé |
|---|---|---|
| **Variance nulle** | Un champ constant sur des centaines de jours est presque toujours le mauvais champ | FC de repos figée à 43-44 sur 447 jours |
| **Bornes physiologiques** | Sommeil 4-12 h · FC repos 35-70 · phases ≤ durée | Une nuit de 24 minutes, une sieste de 16 heures |
| **Recoupement des sources** | Sur les jours communs, l'export complet et les exports quotidiens doivent concorder | Les quatre, sans exception |

Les quatre bugs :

1. **La durée de sommeil** sommait les écarts entre marqueurs de phase — sous-évaluation jusqu'à
   quatre heures (3 h 50 relevées pour 7 h 47 réelles). Utiliser les événements de session, pas la
   somme des phases.
2. **La FC de repos** lue sur `restingHeartRate`, une référence glissante figée, au lieu de
   `currentDayRestingHeartRate`. Faux dans *les deux* sources — 447 jours.
3. **Deux définitions du sommeil** mélangées selon la source : temps au lit contre temps endormi.
4. **Le dernier jour d'un export Garmin est partiel**, et écrasait une journée complète.

> **Cadrage des jours.** Une ligne datée D couvre la nuit qui se *termine* le matin de D. Une
> semaine du lundi au dimanche est complète dès l'export du dimanche ; celui du lundi appartient à
> la suivante.

> `extract_garmin.py` **a besoin des fichiers d'export en argument**. Lancé à vide, il réaffiche les
> données existantes sans rien ingérer — en affichant un tableau d'apparence parfaitement normale.

---

## Les indicateurs

**L'allure à fréquence cardiaque constante** — indice d'efficience `vitesse ÷ FC`, extrapolé à
145 bpm. Le seul chiffre qui mesure le progrès aérobie indépendamment de la météo et de la forme du
jour. Tout le reste du tableau de bord est du contexte.

**La correction thermique** — la chaleur élève la FC d'environ 0,65 bpm par °C au-dessus de 15 °C.
Sur une prépa de l'été au printemps, ça suffit à améliorer « l'allure à 145 bpm » d'environ 20 s/km.
Un artefact lu comme un progrès. `meteo.py` la renseigne automatiquement (Open-Meteo, coordonnées au
niveau de la ville, sans clé, sans identifiant).

**Strava expose bien la température** — `get_activity_streams` accepte un flux `temp`. Il n'est
renseigné que si la montre a un capteur qui l'enregistre, et beaucoup ne le font pas : le flux
revient alors vide. `meteo.py` est le repli pour ce cas. Si ta montre l'enregistre, préfère le flux
Strava : c'est la température à ton poignet pendant l'effort, pas celle d'une station météo.

**Matin contre soir** — `moment_journee.py` sépare l'effet circadien de l'effet thermique, et
**refuse de conclure** en dessous de cinq sorties par créneau. En été, une sortie du matin est aussi
une sortie 10 °C plus fraîche ; sans séparer les deux, on mesure la météo en l'appelant biologie.

**La charge d'entraînement** — les concepts viennent de la référence de coaching de claude-coach
(`skill/reference/load-management.md`) : TSS, charges chronique et aiguë, limites de progression,
suivi de récupération. Ce que ce fork ajoute, c'est les calculer sur les données réelles chaque
semaine et agir dessus.

---

## La règle qui en est sortie

> **Une destination qui n'est pas vérifiée n'est pas synchronisée.**
>
> Ajouter une étape au pipeline ne suffit pas — une étape peut échouer, être contournée, ou être
> lancée à la main dans le mauvais ordre. Chaque destination vient avec son test dans
> `verifier_sync.py`, et chaque test est validé en injectant le défaut qu'il est censé attraper.
>
> Un contrôle au vert sur une chaîne cassée est pire que pas de contrôle.

Ça a été appris deux fois. La seconde, l'archive pour la montre était périmée d'une semaine — elle
contenait des séances qui avaient changé depuis — pendant que tous les contrôles annonçaient un
succès, parce qu'ils regardaient le dossier et que personne ne regardait le zip.

---

## Si ça coince

| Symptôme | Cause |
|---|---|
| L'onglet **Code** propose un abonnement | Plan gratuit. Claude Code demande Pro ou au-dessus. |
| Strava ne trouve aucune activité | Dans l'ordre : abonnement inactif, autorisation non aboutie, connecteur déconnecté. Tape `/mcp`. |
| Il réclame un **Client ID** Strava | Réponds *« utilise le connecteur Strava déjà branché »*. |
| Le bilan du lundi n'a pas eu lieu | App fermée ou machine en veille. Settings → Desktop app → General → **Keep computer awake**. Refermer le capot endort quand même la machine. |
| Il redemande une autorisation chaque semaine | Essai à blanc non fait, ou « autoriser une fois ». |
| Second onglet noir sur iPhone | Safari bloque les inclusions locales. Embarquer via `srcdoc`. |
| Les zones de FC semblent fausses | Celles de Strava reposent sur une FC max estimée. Repartir d'un seuil lactique mesuré. |
| Les kilomètres de chaussures ne bougent plus | L'export est une photographie. Les nouveaux kilomètres vont à la paire marquée comme portée. |
| La VFC reste vide | Pas dans l'export complet — seulement dans les exports quotidiens. |
| La montre refuse les fichiers de séance | Bugs d'encodage amont. Ce fork les corrige ; vérifie que tu ne lances pas `npx claude-coach@latest`. |
| Montre invisible en USB | Encore en mode USB Garmin — basculer en **MTP** (maintenir MENU → Paramètres → Système → Mode USB), puis un client MTP comme OpenMTP. Fermer Garmin Express d'abord. |
| Deux séances, une seule entrée sur la montre | Noms internes identiques. Préfixer par la date, date en tête. |
| Il conclut n'importe quoi sur une semaine | Bâtir un récit sur 7 jours. Réponds *« regarde tout mon historique avant de conclure »*. |

> ⚠️ **Ne jamais lancer `npx claude-coach@latest`** si tu dépends des correctifs FIT — c'est la
> version publiée, qui les contient encore. Utilise la build locale :
> `npx tsx src/cli.ts render ...`.
