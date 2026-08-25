/**
 * Génère les fichiers .fit Garmin de toutes les séances du plan,
 * en réutilisant le convertisseur officiel de claude-coach.
 * Lancement : npx tsx gen-fit.ts
 */
import { readFileSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { generateFit, isFitSupported } from "./src/viewer/lib/export/fit.js";

const PLAN = "build/plan.json";
const OUT = "garmin-fit";

const slug = (s: string) =>
  s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40);

// La montre affiche le nom INTERNE de la séance, jamais le nom du fichier.
// Deux séances homonymes s'écrasent donc l'une l'autre dans la liste
// Entraînements — c'est ce qui faisait disparaître le jeudi, identique au mardi.
// La date est placée en tête : si l'écran tronque, elle reste visible.
const JOURS = ["dim", "lun", "mar", "mer", "jeu", "ven", "sam"];

const nomPourLaMontre = (date: string, nom: string) => {
  const [, mois, jour] = date.split("-");
  const abrev = JOURS[new Date(`${date}T12:00:00Z`).getUTCDay()];
  return `${abrev} ${jour}/${mois} — ${nom}`;
};

const plan = JSON.parse(readFileSync(PLAN, "utf-8"));
rmSync(OUT, { recursive: true, force: true });
mkdirSync(OUT, { recursive: true });

let ok = 0;
const skipped: string[] = [];

for (const week of plan.weeks) {
  for (const day of week.days) {
    for (const w of day.workouts) {
      if (w.sport === "rest") continue;
      if (w.sport === "bike") continue; // trajets domicile-bureau : aucun intérêt à les structurer
      if (w.sport === "strength") continue; // renfo : se fait sans montre, cf. fiches exercices
      if (!isFitSupported(w.sport)) {
        skipped.push(`${day.date} ${w.sport} — ${w.name}`);
        continue;
      }
      const bytes = await generateFit(
        { ...w, name: nomPourLaMontre(day.date, w.name) },
        {} as never
      );
      const file = `S${String(week.weekNumber).padStart(2, "0")}_${day.date}_${slug(w.name)}.fit`;
      writeFileSync(`${OUT}/${file}`, bytes);
      ok++;
    }
  }
}

console.log(`${ok} fichiers .fit générés dans ${OUT}`);
if (skipped.length) {
  console.log(`\n${skipped.length} séances non exportables (sport non géré par le SDK) :`);
  for (const s of [...new Set(skipped.map((x) => x.split("—")[0].split(" ")[1]))])
    console.log(`  - sport "${s}"`);
}
