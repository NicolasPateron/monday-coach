import type { TrainingPlan } from "../../schema/training-plan.js";

// Load plan from embedded JSON
function loadPlanData(): TrainingPlan {
  const el = document.getElementById("plan-data");
  if (!el) throw new Error("Plan data not found");
  return JSON.parse(el.textContent || "{}");
}

// Reactive state using Svelte 5's $state rune is only available in .svelte files
// So we export the raw data and let components create reactive state
export const planData = loadPlanData();

// Completed workouts stored in localStorage
const storageKey = `plan-${planData.meta.id}-completed`;

export function loadCompleted(): Record<string, boolean> {
  // Les séances marquées `completed` dans le plan lui-même sont pilotées par les
  // données réelles (Strava) : elles font autorité et sont fusionnées par-dessus
  // l'état local du navigateur. Sans ça, une séance effectivement courue
  // n'apparaîtrait jamais faite — le localStorage seul est aussi peu fiable sur
  // une page file:// ou dans une iframe srcdoc (origine opaque).
  const depuisPlan: Record<string, boolean> = {};
  for (const semaine of planData.weeks ?? [])
    for (const jour of semaine.days ?? [])
      for (const w of jour.workouts ?? []) if (w.completed) depuisPlan[w.id] = true;

  let local: Record<string, boolean> = {};
  try {
    const saved = localStorage.getItem(storageKey);
    local = saved ? JSON.parse(saved) : {};
  } catch {
    /* stockage indisponible (origine opaque) : on se contente du plan */
  }
  return { ...local, ...depuisPlan };
}

export function saveCompleted(completed: Record<string, boolean>): void {
  try {
    localStorage.setItem(storageKey, JSON.stringify(completed));
  } catch {
    /* stockage indisponible : le plan reste la source de vérité */
  }
}
