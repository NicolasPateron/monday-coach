> **Traduction française des prompts** ([setup](../prompts/setup.md) ·
> [dashboard](../prompts/dashboard.md) · [weekly-review](../prompts/weekly-review.md)).
> Les versions anglaises font foi.

# Les prompts

Ce qui est entre `[crochets]` est à remplacer par ta réponse.

---

## 1 · Installer la compétence coach

*Ceci installe [claude-coach](https://github.com/felixrieseberg/claude-coach) lui-même — le moteur
qui construit ton plan.*

```
Installe la skill "coach" du projet claude-coach : télécharge
https://github.com/felixrieseberg/claude-coach/releases/latest/download/coach-skill.zip
et décompresse-la dans ~/.claude/skills/coach/ (le zip contient un SKILL.md à la
racine et un dossier reference/). Ensuite, recharge les skills et confirme-moi
que /coach est disponible.
```

**Tu dois voir** `/coach` dans la liste quand tu tapes `/`. Sinon, `/reload-skills`.

Puis laisse-la construire ton plan :

```
Utilise la skill coach pour me préparer un plan pour [nom de la course] le
[JJ/MM/AAAA]. Prends mes données via le connecteur Strava déjà branché, pas
par ton propre accès Strava.
```

Cette seconde phrase compte : sans elle, la compétence propose son ancien chemin par Client ID, que
le connecteur Strava officiel rend inutile.

La compétence mène l'entretien à partir de là — combien de jours par semaine, ta durée maximale de
sortie longue, ton objectif, tes blessures, tes voyages. Deux choses à réclamer si elle ne les
propose pas :

- **Un avis franc.** *« Mon objectif est-il réaliste, et sinon lequel l'est ? »* Une vérité utile
  vaut mieux qu'un plan flatteur.
- **Sur quoi reposent tes zones.** Celles de Strava reposent souvent sur une FC max estimée.

> ⚕️ Un plan produit par une IA est une proposition. Elle ne t'a pas examiné et ne sait rien d'une
> douleur qui traîne. Antécédent médical, doute, douleur qui s'installe : ça se règle entre toi et
> un professionnel.

---

## 2 · Charger ton historique Garmin

*C'est ce qui t'apporte le sommeil, la VFC et la FC de repos — dont Strava ne transporte rien.*

Décompresse l'export que Garmin t'a envoyé par mail, puis :

```
J'ai reçu mon export Garmin complet, il est décompressé dans [chemin du dossier].
Écris un script d'import qui en tire un historique quotidien unique avec, pour
chaque jour : sommeil et ses phases, FC de repos, pas, stress, et ce que tu
trouves d'autre d'utile. Récupère aussi à part l'évolution de mon VO2max, mes
prédictions de course et ma charge d'entraînement.

Récupère aussi mes chaussures : l'export contient un fichier de matériel avec,
pour chaque paire, son kilométrage cumulé et le seuil de remplacement que j'ai
réglé dans Garmin. Fais-en un petit fichier à part, en marquant quelle paire je
porte actuellement.

Puis dis-moi mes baselines réelles calculées sur tout l'historique : sommeil
moyen et médian, plage de FC de repos, et à partir de quels seuils tu considères
que je dérive. Je veux des seuils calculés sur mes données, pas des valeurs
générales.
```

Ce dernier paragraphe est le plus important. Des seuils généraux ne peuvent pas te dire que *toi* tu
dérives.

> ⚠️ **Deux exports Garmin différents — ne les confonds pas.**
>
> L'**export complet** se demande une fois depuis garmin.com → Gestion des données. Il apporte
> l'historique long : sommeil, FC de repos, pas, stress, VO2max.
>
> L'**export de bien-être quotidien** se demande une date à la fois, depuis connect.garmin.com →
> Paramètres → Informations sur le compte → tout en bas. Il apporte la seule chose qui manque au
> premier : **la variabilité cardiaque**. Sept clics pour une semaine, et c'est facultatif.

---

## 3 · L'onglet de suivi

claude-coach a déjà produit ton plan et son viewer. Ceci construit **l'autre onglet** — celui qui
suit ce que tu as réellement fait — et emballe les deux dans un fichier que tu ouvres sur ton
téléphone.

```
Construis mon support de suivi : UN SEUL fichier HTML autonome, à deux onglets,
que je puisse ouvrir sur mon téléphone.

ONGLET 1 — SUIVI. Il commence par des phrases, pas par des courbes :
3 à 5 constats en langage clair sur ma semaine, chacun avec un verdict
(ça va / attention) et le chiffre qui le justifie. Ensuite les courbes :
- volume prévu contre réalisé, semaine par semaine
- mon allure à fréquence cardiaque constante (autour de 145 bpm) :
  c'est le seul indicateur qui mesure mes progrès aérobies
  indépendamment de la météo et de la forme du jour, mets-le en avant
- mon poids contre sa trajectoire cible
- sommeil, VFC et FC de repos, chacun avec MA bande de normalité
  calculée sur mon historique, pas des valeurs générales
- l'usure de mes chaussures : une jauge par paire, les kilomètres courus
  sur le seuil de remplacement, et la semaine du plan où chaque paire
  atteindra sa limite si elle porte le volume prévu

ONGLET 2 — PROGRAMME. Reprends la page de programme que la skill coach
a déjà produite, et EMBARQUE-la dans le fichier (via srcdoc), sans
pointer vers un fichier voisin : Safari bloque ce genre d'inclusion
quand la page est ouverte depuis le disque, et l'onglet s'afficherait
noir sur iPhone.

Écris les scripts nécessaires pour que tout se régénère d'une seule
commande, garde un journal cumulatif semaine après semaine, et
donne-moi en une ligne par fichier ce que chacun fait.
```

**Trois choses à ne pas changer :**

**`srcdoc`, pas `src`.** Le réglage précis qui évite l'onglet noir sur iPhone. Il ne s'adresse pas à
toi mais à Claude.

**« MA bande de normalité calculée sur mon historique ».** Sans ça, tu obtiens des moyennes de
population, qui ne peuvent pas te dire que *toi* tu dérives.

**Ne lui demande pas de refaire l'onglet Programme.** Le viewer de claude-coach existe déjà, il est
bien fait, et il gère l'édition, la complétion et les exports. La consigne est de l'*embarquer*, pas
de le réimplémenter.

Les courbes seront vides au début et se rempliront semaine après semaine. C'est normal. Dis ensuite
ce qui te manque : c'est une conversation, pas un prompt unique.

---

## 4 · Le bilan du lundi

C'est le contrat de ton entraîneur. Écrit une fois, appliqué chaque semaine sans toi — donc sois
précis. C'est le texte avec lequel tu vas vivre pendant des mois.

Branche d'abord Google Agenda (**Customize → Connectors**), puis colle :

```
Crée une tâche planifiée locale appelée "bilan-hebdo", tous les lundis
à 10h30, sur ce dossier. Voici ses instructions :

Tu es mon entraîneur. C'est le bilan hebdomadaire du lundi. Réponds en
français, court et lisible. N'invente jamais une séance que Strava ne
montre pas.

1. Lis mes 7 derniers jours d'activités via le connecteur Strava :
   distance, allure, FC moyenne et max, dénivelé.
2. Si j'ai déposé des exports Garmin quotidiens dans mes
   téléchargements, décode-les et fusionne-les avec mon historique.
   Sinon, relis simplement l'historique existant.
3. Relis le plan et retrouve la semaine écoulée et la semaine à venir.
4. Compare honnêtement : volume réalisé contre prévu, allures tenues,
   et surtout ma FC sur les sorties faciles. Si je cours mon endurance
   trop vite, dis-le explicitement, c'est mon erreur la plus probable.
5. Regarde mes signaux de récupération contre MES baselines : sommeil,
   VFC, FC de repos. Si deux d'entre eux dérivent, allège la semaine à
   venir au lieu de la maintenir.
6. Ajuste la semaine à venir. Règles : jamais plus de +10 % de volume
   d'une semaine sur l'autre, ni plus de 2 à 3 km sur la sortie longue.
   Si j'ai fait moins de la moitié du prévu, ne repars pas au volume
   théorique : reprends au niveau réellement tenu et décale la suite du
   plan au lieu de sauter des étapes. Si je n'ai rien fait du tout :
   message court, sans reproche, avec UNE seule action facile pour
   redémarrer, et ne réécris pas le plan entier.
7. Vérifie l'usure de mes chaussures et signale-moi toute paire
   au-dessus de 75 % du seuil de remplacement. Sur une prépa entière
   j'en userai probablement deux : je préfère être prévenu deux
   semaines trop tôt que le jour où mes genoux le sentent.
8. Recalcule le tableau de bord et régénère ma page de suivi, puis
   envoie-la-moi.
9. Écris les séances de la semaine à venir dans mon Google Agenda
   ([mardi 19h, jeudi 19h, dimanche 9h30]). Titre court, et dans la
   description : allure, FC cible, déroulé, et le pourquoi de la
   séance. Vérifie d'abord qu'elles n'y sont pas déjà.
10. Prépare les fichiers .fit de la semaine à venir et envoie-les-moi
   dans une archive, prêts à glisser dans ma montre.

Format de réponse : un tableau prévu contre réalisé, deux à quatre
constats dont au moins un positif s'il y a matière, les séances de la
semaine à venir en une ligne chacune, et un seul point de vigilance.
```

Les points 4, 6 et 7 s'appuient sur la référence de coaching de claude-coach —
`load-management.md` pour les limites de progression et le suivi de récupération, `workouts.md` pour
la structure des séances. Tu n'inventes pas une méthode ; tu demandes à Claude d'appliquer celle
qu'il a déjà, à tes données réelles, chaque semaine.

### Quatre règles à ajouter tôt

Chacune vient d'une panne réelle.

**Vérifier les entrées avant de clore une semaine.** Le poids et l'export Garmin quotidien ne
viennent que de toi, et aucun script ne peut les inventer. Si l'un manque, le dire en tête et ne pas
présenter la semaine comme close. **Un poids inchangé n'est pas un poids stable — c'est une absence
de mesure**, et les deux se ressemblent sur un graphique.

**Ne jamais conclure sur une seule semaine.** Bâtir un récit sur 7 jours est l'erreur la plus
fréquente. Une mauvaise semaine ressemble beaucoup à une tendance, et une bonne encore plus.

**Vérifier toutes les destinations, pas seulement celle qu'on a touchée.** Générer les charges
utiles d'agenda depuis le plan, les pousser sans reformuler, relire l'agenda, et laisser le contrôle
comparer. Ne jamais saisir une description de séance à la main.

**Renseigner la température de la séance avant d'analyser la FC.** Sans elle, l'automne ressemble à
un progrès.

---

## 5 · L'essai à blanc

Ne laisse pas le premier vrai lundi être aussi le premier essai. La première exécution demande des
autorisations, et si personne n'est là pour répondre, la tâche reste à attendre.

**Routines** → ta tâche → **Run now**. Reste devant l'écran, choisis **toujours autoriser** à chaque
demande, et lis ce qu'il produit. Puis :

```
Garde en mémoire, pour toutes nos prochaines sessions : mon objectif et sa date,
mes zones de FC et sur quoi elles sont calculées, mes jours d'entraînement, mes
baselines de récupération, et les deux ou trois choses les plus importantes que
tu as comprises sur ma façon de m'entraîner — y compris mes points faibles. Puis
montre-moi ce que tu as écrit.
```

Relis ce qu'il a enregistré. Une erreur qui s'y glisse se répétera chaque semaine.
