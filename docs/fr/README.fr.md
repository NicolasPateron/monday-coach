> **Traduction française du [README](../../README.md).** La version anglaise fait foi.
> Voir aussi : [architecture](architecture.fr.md) · [prompts](prompts.fr.md)

# Monday Coach

**Un fork de [claude-coach](https://github.com/felixrieseberg/claude-coach) qui garde le plan
honnête pendant les six mois qui suivent sa création.**

---

## Ce que claude-coach fait déjà — et fait bien

[claude-coach](https://github.com/felixrieseberg/claude-coach), de
[Felix Rieseberg](https://github.com/felixrieseberg), est le moteur. Il :

- **te fait passer un entretien** comme le ferait un entraîneur — course, objectif, jours
  disponibles, blessures, contraintes
- **lit ton historique Strava** et te dit honnêtement dans quelle forme tu es
- **construit le plan** : phases, zones, structure des séances, stratégie de course, le tout depuis
  une vraie méthode d'entraînement
- **le rend sous forme d'application** que tu peux éditer, réorganiser et cocher, hors ligne et sur
  téléphone
- **exporte chaque séance** vers agenda, Garmin, Zwift et TrainerRoad

C'est le plus dur, et c'est entièrement son travail. **Si tu veux juste un plan d'entraînement,
utilise claude-coach et arrête ta lecture ici.** Son README est conservé dans
[`docs/README.upstream.md`](../README.upstream.md).

---

## Ce que ce fork ajoute, et pourquoi ça compte

claude-coach répond à *qu'est-ce que je dois faire ?*

Ce fork répond à *qu'est-ce que je fais maintenant que la semaine 3 ne s'est pas passée comme
prévu ?*

Un plan s'écrit une fois. Une préparation dure six mois. Entre les deux, tu dors mal, il fait
chaud, tu sautes une semaine, tes chaussures meurent, et tu cours tes sorties faciles trop vite
sans t'en rendre compte. **Rien de tout ça n'est visible dans un plan.** C'est visible dans tes
données — et personne n'a la patience de les croiser chaque lundi.

Alors ce fork le fait pour toi, chaque lundi matin, sans que tu lances quoi que ce soit.

| | claude-coach | + ce fork |
|---|---|---|
| Construit le plan | ✅ | l'utilise comme source de vérité |
| Sait si tu as vraiment fait la séance | tu coches une case | **lu automatiquement depuis Strava** |
| Sait si tu récupères | — | **sommeil, VFC, FC de repos depuis Garmin** |
| Sait si tu progresses | — | **allure à FC constante, corrigée de la température** |
| Sait si tes chaussures sont mortes | — | **jauge d'usure + la semaine où chaque paire lâche** |
| Met la semaine à venir dans ton agenda | tu télécharges un `.ics` | **écrite et maintenue à jour, chaque semaine** |
| Ajuste quand tu prends du retard | — | **le bilan du lundi s'en charge** |

### Les cinq ajouts, simplement

**1 · Il lit ce que tu as réellement couru.** Chaque lundi il récupère ta semaine depuis Strava et
la met à côté du plan. Volume, allure, et surtout la fréquence cardiaque sur les sorties faciles —
l'erreur la plus fréquente et la plus coûteuse en endurance.

**2 · Il voit ce que Strava ne peut pas voir.** Sommeil, variabilité cardiaque, FC de repos et pas
viennent de tes exports de données Garmin, que Strava ne transporte pas. Ce sont les chiffres qui
préviennent *avant* que tu casses, pas après.

**3 · Il mesure le progrès, pas la météo.** La chaleur élève ta FC d'environ 0,65 bpm par °C. Sur
une prépa qui va de l'été au printemps, ça suffit à te faire paraître 20 s/km plus rapide. Chaque
fréquence cardiaque est corrigée de la température avant qu'on en conclue quoi que ce soit.

**4 · Il écrit ta semaine dans ton agenda.** Pas un fichier à importer — de vrais événements, avec
l'allure, le plafond de FC, le déroulé complet et le *pourquoi* de la séance. Les séances faites
passent en gris et prennent un ✅.

**5 · Il ajuste.** Du retard ? Il repart du niveau que tu as réellement tenu et décale le plan, au
lieu de faire comme si tu avais fait les semaines manquantes. Récupération qui dérive ? Il allège
la semaine plutôt que de maintenir la ligne.

### À quoi ça ressemble

Ton objectif, toujours visible. Deux onglets : cet onglet de suivi, et le viewer de claude-coach à
côté.

![Barre d'onglets](../images/tabs-bar.jpg)

Il s'ouvre sur **des phrases, pas des courbes** — chacune avec le chiffre qui la justifie.

![Constats hebdomadaires](../images/observations.jpg)

Prévu contre réalisé. L'écart entre les deux est le chiffre le plus utile de la page.

![Volume prévu contre réalisé](../images/volume.jpg)

Est-ce que tu progresses ? L'allure à 145 bpm constants, corrigée de la température — et le poids
contre sa cible.

![Allure à 145 bpm, et poids](../images/efficiency.jpg)

Est-ce que tu récupères ? Chaque indicateur contre **ta** bande de normalité, calculée sur ton
propre historique — pas des moyennes de population. Une FC de repos à 51 n'a rien de notable en
général, et devient inquiétante chez quelqu'un qui tourne habituellement à 43.

![Sommeil, VFC, FC de repos](../images/recovery.jpg)

Tes chaussures sont-elles mortes ? Une chaussure perd son amorti bien avant de paraître usée.

![Usure des chaussures](../images/shoes.jpg)

> Toutes les captures montrent un **coureur fictif**. Régénération : `./docs/demo/shoot.sh`.

Et le second onglet, qui est le viewer de claude-coach, inchangé :

![Le viewer de claude-coach](../images/upstream-viewer.jpg)

*Capture issue du [dépôt claude-coach](https://github.com/felixrieseberg/claude-coach).*

---

## Ce que ce fork corrige dans claude-coach

Huit bugs, trouvés en l'utilisant intensivement pendant six mois. Tous dans deux fichiers.

**Sept dans l'export Garmin `.fit`** — la montre refusait silencieusement les séances, ou les
affichait sans nom :

| Bug | Correctif |
|---|---|
| `targetType: "heart_rate"` | `"heartRate"` — le SDK veut du camelCase |
| `durationType: "repeat_until_steps_cmplt"` | `"repeatUntilStepsCmplt"` |
| `subSport: "lap_swimming"` / `"strength_training"` | `"lapSwimming"` / `"strengthTraining"` |
| Champ `workoutStepName` | `wktStepName` — le vrai nom du champ ; l'autre est ignoré en silence |
| Champ `workoutName` | `wktName` — pareil |
| Pas de répétition placé *avant* ses enfants | Va *après* : `durationValue` = index du 1er enfant, `targetValue` = nombre de répétitions |
| FC écrite en bpm bruts | FIT lit 1–100 comme un % de FC max : 145 bpm devenait « 145 % de la max ». Converti |

**Un dans le viewer** — `loadCompleted()` ne lisait que le `localStorage` et écrasait le champ
`completed` du plan : une sortie réellement courue n'apparaissait jamais faite. Le plan fait
désormais autorité, et ça ne casse plus en origine opaque (`file://`, iframe `srcdoc`).

**Plus un problème de nommage, pas vraiment un bug :** la montre affiche le nom interne de la
séance, jamais celui du fichier — un mardi et un jeudi tous deux appelés « Endurance fondamentale »
se réduisaient à une seule entrée. Les noms sont maintenant préfixés par la date, date en tête,
parce que la montre tronque par la droite.

**Pourquoi sept bugs ont survécu ici sans être vus :** `.ics`, `.zwo` et `.mrc` avaient chacun
un fichier de tests. `.fit` n'en avait aucun. Ce fork ajoute
[`tests/viewer/export-fit.test.ts`](../../tests/viewer/export-fit.test.ts) — sept cas qui décodent
ce qui a été encodé, dont six échouent sur l'exporteur non corrigé. La suite complète fait
166 tests, tous au vert.

> Ces correctifs sont autonomes et s'appliqueraient proprement en amont.

---

## Montage

Environ 90 minutes, une seule fois. Les étapes 3 et 4 sont celles de claude-coach ; le reste câble
la boucle autour.

| | | |
|---|---|---|
| **0** | **Demande ton export de données Garmin** sur garmin.com → Gestion des données. Jusqu'à 48 h, donc lance-le maintenant et continue. | 2 min |
| **1** | Installe [Claude Code](https://claude.ai/download), ouvre l'onglet **Code**, crée un dossier, choisis **Opus**. | 10 min |
| **2** | Branche Strava : **Customize → Connectors →** `https://mcp.strava.com/mcp`. Lecture seule. | 5 min |
| **3** | Installe la compétence coach — [prompt](prompts.fr.md#1--installer-la-compétence-coach). | 5 min |
| **4** | **Laisse la compétence construire ton plan.** C'est claude-coach qui fait son travail : l'entretien, les zones, le plan, le viewer. | 30 min |
| **5** | Charge ton historique Garmin — [prompt](prompts.fr.md#2--charger-ton-historique-garmin). | 10 min |
| **6** | Fabrique l'onglet de suivi — [prompt](prompts.fr.md#3--longlet-de-suivi). | 20 min |
| **7** | Programme le bilan du lundi — [prompt](prompts.fr.md#4--le-bilan-du-lundi). | 15 min |
| **8** | Essai à blanc, pour qu'il demande ses autorisations pendant que tu regardes. | 10 min |

> **Ne crée pas d'application Strava.** Le README de claude-coach décrit un chemin par Client ID et
> Client Secret — écrit avant que Strava publie un connecteur officiel. Avec le connecteur, tu n'en
> as pas besoin. Si la compétence en réclame un, réponds *« utilise le connecteur Strava déjà
> branché »*.

**Prérequis :** un abonnement Claude payant (Pro ou au-dessus), un abonnement Strava (le connecteur
est réservé aux abonnés), Python 3. La montre Garmin est facultative — sans elle tu perds les
courbes de récupération et les séances guidées, et tu gardes tout le reste.

---

## Ta semaine, une fois que ça tourne

| Quand | Ce que tu fais |
|---|---|
| Chaque sortie | Rien. Ta montre synchronise avec Strava. |
| Lundi matin | Tu lis le bilan qui s'est écrit tout seul. **3 minutes.** |
| Lundi, facultatif | Tu déposes tes exports Garmin quotidiens dans Téléchargements. 2 min. |
| Quand tu te pèses | Tu ajoutes une ligne à un fichier. 10 secondes. |
| Quand tu achètes des chaussures | Tu le dis à Claude, en une phrase. |

Tu ne promptes jamais le bilan du lundi. Si tu te retrouves à taper « fais mon bilan », la tâche
planifiée ne tourne pas.

---

## Sous le capot

Douze scripts Python dans [`harness/`](../../harness/), sans dépendances, une commande :
`./harness/relancer.sh`.

Ce qui vaut la peine d'être connu est dans **[architecture.fr.md](architecture.fr.md)** :

- **pourquoi le pipeline n'a qu'un seul ordre valide** — s'être trompé une fois a effacé six
  semaines de progression visible
- **pourquoi le texte de l'agenda est généré et jamais saisi** — deux sources de vérité divergent
  toujours ; celle-ci a produit deux versions incompatibles de la même séance
- **comment les données sont validées avant d'en conclure quoi que ce soit** — quatre bugs
  d'extraction ont produit trois conclusions assurées et fausses sur le sommeil
- **la règle qui en est sortie** : *une destination qui n'est pas vérifiée n'est pas synchronisée*

---

## Confidentialité

Tout reste sur ta machine. Strava est en lecture seule et révocable. **Aucun mot de passe Garmin
n'est jamais demandé** — il n'existe pas de connecteur Garmin officiel, et les communautaires
réclament tes identifiants en clair ; ce projet utilise à la place des exports que tu télécharges
toi-même. Ton export Garmin contient les traces GPS de ton domicile : garde-le en local. La mémoire
est du texte que tu peux lire et effacer avec `/memory`.

---

## Limites

- **Ce n'est pas un avis médical.** Ce sont des propositions d'entraînement issues de tes données,
  produites par quelque chose qui ne t'a jamais examiné.
- **`harness/generate_plan.py` est calibré sur une préparation marathon précise.** La compétence
  `/coach` de claude-coach est l'outil générique, et pour la plupart des gens c'est le bon.
- **L'outillage est écrit en français** — commentaires, noms de scripts, texte des séances. Le
  traduire est la première contribution évidente.
- **Un athlète, une préparation.** Validé sur une seule prépa réelle.

---

## Remerciements

**Rien de tout ça n'existerait sans
[claude-coach](https://github.com/felixrieseberg/claude-coach) de
[Felix Rieseberg](https://github.com/felixrieseberg).**

Le plus dur était déjà fait : une vraie méthode d'entraînement, un entretien qui fait qu'on n'a
jamais besoin de savoir quoi demander, et un viewer de plan réellement bien fait. Tout ce qui est
ici est construit par-dessus.

Les bugs listés plus haut ne sont pas une critique — ils sont ce qui remonte quand un bon outil
rencontre une montre précise et six mois d'usage quotidien. Ils sont documentés en détail pour
pouvoir remonter vers l'amont si c'est utile.

## Licence

MIT, comme l'amont. Le copyright de l'œuvre originale reste à Felix Rieseberg. Voir
[`LICENSE.md`](../../LICENSE.md).
