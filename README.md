# Monday Coach

**A fork of [claude-coach](https://github.com/felixrieseberg/claude-coach) that keeps the plan
honest for the six months after you build it.**

*Français : [README](docs/fr/README.fr.md)*

---

## What claude-coach already does — and does well

[claude-coach](https://github.com/felixrieseberg/claude-coach) by
[Felix Rieseberg](https://github.com/felixrieseberg) is the engine. It:

- **interviews you** like a coach would — race, target, available days, injuries, constraints
- **reads your Strava history** and tells you honestly what shape you're in
- **builds the plan**: phases, zones, session structure, race-day strategy, all from a real
  coaching method
- **renders it as an app** you can edit, reorder and tick off, offline and on a phone
- **exports every session** to calendar, Garmin, Zwift and TrainerRoad

That is the hard part, and it is all his work. **If you just want a training plan, use
claude-coach and stop reading here.** Its README is kept at
[`docs/README.upstream.md`](docs/README.upstream.md).

---

## What this fork adds, and why it matters

claude-coach answers *what should I do?*

This fork answers *what should I do now that week 3 didn't go to plan?*

A plan is written once. A build lasts six months. In between, you sleep badly, it gets hot, you
skip a week, your shoes die, and you run your easy runs too fast without noticing. **None of that
is visible in a plan.** It is visible in your data — and nobody has the patience to
cross-reference it every Monday.

So this fork does it for you, every Monday morning, without you launching anything.

| | claude-coach | + this fork |
|---|---|---|
| Builds the plan | ✅ | uses it as the source of truth |
| Knows if you actually did the session | you tick a box | **read from Strava automatically** |
| Knows if you're recovering | — | **sleep, HRV, resting heart rate from Garmin** |
| Knows if you're getting fitter | — | **pace at constant heart rate, corrected for temperature** |
| Knows if your shoes are dead | — | **wear gauge + the week each pair runs out** |
| Puts next week in your calendar | download a `.ics` | **written and kept in sync, every week** |
| Adjusts when you fall behind | — | **the Monday review does it** |

### The five additions, plainly

**1 · It reads what you actually ran.** Every Monday it pulls your week from Strava and puts it
next to the plan. Volume, pace, and above all heart rate on easy runs — the most common and most
expensive mistake in endurance training.

**2 · It sees what Strava cannot.** Sleep, heart-rate variability, resting heart rate and steps
come from your Garmin data exports, which Strava does not carry. These are the numbers that warn
you *before* you break down, not after.

**3 · It measures progress, not weather.** Heat raises your heart rate by roughly 0.65 bpm per °C.
Across a build from summer to spring, that alone makes you look 20 s/km faster. Every heart rate
is temperature-corrected before anything is concluded from it.

**4 · It writes your week into your calendar.** Not a file to import — actual events, with pace,
heart-rate ceiling, the full session and *why* it exists. Done sessions turn grey and get a ✅.

**5 · It adjusts.** Fell behind? It resumes from what you actually held and shifts the plan
instead of pretending you did the missing weeks. Recovery drifting? It lightens the week rather
than holding the line.

### What it looks like

Your goal, always in view. Two tabs: this tracking tab, and claude-coach's plan viewer beside it.

![Tab bar](docs/images/tabs-bar.jpg)

It opens on **sentences, not charts** — each with the number that justifies it.

![Weekly observations](docs/images/observations.jpg)

Planned against actual. The gap between the two is the most useful number on the page.

![Planned versus actual volume](docs/images/volume.jpg)

Are you getting fitter? Pace at a constant 145 bpm, temperature-corrected — and weight against its
target.

![Pace at 145 bpm, and weight](docs/images/efficiency.jpg)

Are you recovering? Each metric against **your** normal band, computed from your own history —
not population averages. A resting heart rate of 51 is unremarkable in general and alarming for
someone who normally sits at 43.

![Sleep, HRV, resting heart rate](docs/images/recovery.jpg)

Are your shoes dead? A shoe loses its cushioning long before it looks worn.

![Shoe wear](docs/images/shoes.jpg)

> All screenshots show a **fictional athlete**. Regenerate them with `./docs/demo/shoot.sh`.

And the second tab, which is claude-coach's viewer, unchanged:

![claude-coach's plan viewer](docs/images/upstream-viewer.jpg)

*Screenshot from the [claude-coach repository](https://github.com/felixrieseberg/claude-coach).*

---

## What this fork fixes in claude-coach

Eight bugs, found by using it hard for six months. All in two files.

**Seven in the Garmin `.fit` export** — the watch was silently rejecting workouts, or showing them
with no name:

| Bug | Fix |
|---|---|
| `targetType: "heart_rate"` | `"heartRate"` — the SDK wants camelCase |
| `durationType: "repeat_until_steps_cmplt"` | `"repeatUntilStepsCmplt"` |
| `subSport: "lap_swimming"` / `"strength_training"` | `"lapSwimming"` / `"strengthTraining"` |
| Field `workoutStepName` | `wktStepName` — the real field name; the other is ignored in silence |
| Field `workoutName` | `wktName` — same |
| Repeat step placed *before* its children | Goes *after*: `durationValue` = first child index, `targetValue` = repeat count |
| Heart rate written as raw bpm | FIT reads 1–100 as % of max, so 145 bpm became "145 % of max". Converted |

**One in the viewer** — `loadCompleted()` read only `localStorage` and overwrote the plan's own
`completed` field, so a run you had actually done never showed as done. Now the plan wins, and it
no longer breaks in an opaque origin (`file://`, `srcdoc` iframe).

**Plus one naming problem, not strictly a bug:** the watch displays the internal workout name,
never the filename — so a Tuesday and a Thursday both called "Easy run" collapsed into a single
entry. Names are now prefixed with the date, date first, because the watch truncates from the
right.

**Why seven bugs lived here undetected:** `.ics`, `.zwo` and `.mrc` each had a test file.
`.fit` did not. This fork adds
[`tests/viewer/export-fit.test.ts`](tests/viewer/export-fit.test.ts) — seven cases that decode
what was encoded, six of which fail against the unfixed exporter. The full suite is 166 tests,
all passing.

> These fixes are self-contained and would apply cleanly upstream.

---

## Setup

About 90 minutes, once. Steps 3 and 4 are claude-coach's; the rest wires the loop around it.

| | | |
|---|---|---|
| **0** | **Request your Garmin data export** at garmin.com → Data Management. Up to 48 h, so start it now and carry on. | 2 min |
| **1** | Install [Claude Code](https://claude.ai/download), open the **Code** tab, create a folder, pick **Opus**. | 10 min |
| **2** | Connect Strava: **Customize → Connectors →** `https://mcp.strava.com/mcp`. Read-only. | 5 min |
| **3** | Install the coach skill — [prompt](docs/prompts/setup.md#1--install-the-coach-skill). | 5 min |
| **4** | **Let the skill build your plan.** claude-coach doing its job: the interview, the zones, the plan, the viewer. | 30 min |
| **5** | Load your Garmin history — [prompt](docs/prompts/setup.md#2--load-your-garmin-history). | 10 min |
| **6** | Build the tracking tab — [prompt](docs/prompts/dashboard.md). | 20 min |
| **7** | Schedule the Monday review — [prompt](docs/prompts/weekly-review.md). | 15 min |
| **8** | Dry run, so it asks for its permissions while you're watching — [why](docs/prompts/setup.md#3--dry-run). | 10 min |

> **Don't create a Strava API application.** claude-coach's README describes a Client ID / Client
> Secret route — written before Strava published an official connector. With the connector you
> don't need it. If the skill asks, reply *"use the Strava connector already connected"*.

**Requirements:** a paid Claude plan (Pro or above), a Strava subscription (the connector is
subscriber-only), Python 3. A Garmin watch is optional — without it you lose the recovery curves
and the guided workouts, and keep everything else.

---

## Your week, once it's running

| When | What you do |
|---|---|
| Every run | Nothing. Your watch syncs to Strava. |
| Monday morning | Read the review that wrote itself. **3 minutes.** |
| Monday, optional | Drop your Garmin daily exports in Downloads. 2 min. |
| When you weigh yourself | Add one line to a file. 10 seconds. |
| When you buy shoes | Tell Claude, in one sentence. |

You never prompt the Monday review. If you find yourself typing *"do my weekly review"*, the
scheduled task isn't running.

---

## Under the hood

Twelve Python scripts in [`harness/`](harness/), no dependencies, one command:
`./harness/relancer.sh`.

The parts worth knowing about are in **[docs/architecture.md](docs/architecture.md)**:

- **why the pipeline has exactly one valid order** — getting it wrong once wiped six weeks of
  visible progress
- **why calendar text is generated and never typed** — two sources of truth always diverge; this
  one produced two incompatible versions of the same session
- **how data is validated before anything is concluded from it** — four extraction bugs once
  produced three confident, wrong conclusions about sleep
- **the rule that came out of all of it**: *a destination that isn't verified isn't synchronised*

---

## Privacy

Everything stays on your machine. Strava is read-only and revocable. **No Garmin password is ever
requested** — there is no official Garmin connector, and the community ones want your credentials
in clear text; this project uses data exports you download yourself instead. Your Garmin export
contains GPS traces of your home: keep it local. Memory is text you can read and erase with
`/memory`.

---

## Limitations

- **Not medical advice.** These are training proposals from your own data, produced by something
  that has never examined you.
- **`harness/generate_plan.py` is calibrated for one athlete's marathon build.** claude-coach's
  `/coach` skill is the general-purpose tool, and for most people it is the right one.
- **The harness is written in French** — comments, script names, session text. Translating it is
  the obvious first contribution.
- **One athlete, one build.** Validated against a single real preparation.

---

## Thanks

**None of this would exist without [claude-coach](https://github.com/felixrieseberg/claude-coach)
by [Felix Rieseberg](https://github.com/felixrieseberg).**

The hard part was already done: a real coaching method, an interview that means you never have to
know what to ask, and a plan viewer that is genuinely well made. Everything here is built on top
of that.

The bugs listed above aren't a criticism — they're what surfaces when a good tool meets one
specific watch and six months of daily use. They're documented in detail so they can go back
upstream if useful.

## Licence

MIT, same as upstream. Copyright for the original work remains with Felix Rieseberg. See
[`LICENSE.md`](LICENSE.md).
