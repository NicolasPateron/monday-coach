# Under the hood

Everything here exists because something broke during one real marathon build. Nothing was
designed up front.

---

## One command, one valid order

```bash
./harness/relancer.sh            # weekly refresh
./harness/relancer.sh --plan 2   # after a plan change, for week 2
```

| Step | Script | Why it sits here |
|---|---|---|
| 1 | `generate_plan.py` | Source of truth. Rewrites the plan from scratch — which erases completion state |
| 2 | `meteo.py` | Fills the session temperature, **before** any heart-rate analysis |
| 3 | `valider.py` | Blocks the chain on anomalous data |
| 4 | `dashboard.py` | Cross-references plan, Strava, wellness and weight |
| 5 | `marquer_realise.py` → viewer render | Completion marked **before** rendering, never after |
| 6 | `gen-fit.ts` → `zip_fit.py` | `gen-fit.ts` writes `.fit` only — **never the zips** |
| 7 | `rapport.py` | Produces the dashboard |
| 8 | `verifier_sync.py` | Verifies every destination, exits 1 on drift |

**The order is not stylistic.** Rendering the viewer before marking completions once dropped six
weeks of visible progress to 0 %: `generate_plan.py` rewrites the plan and clears `completed`, so
the viewer has to be rendered *after* Strava data is merged back in. `rapport.py` now refuses to
run if the rendered viewer predates the plan.

---

## Seven destinations, never one alone

| Destination | Written by |
|---|---|
| `harness/generate_plan.py` | **the source** — structural changes go here |
| `build/plan.json` | `generate_plan.py` |
| `build/programme.html` (claude-coach's viewer) | viewer render, **after** `marquer_realise.py` |
| `dashboard.html` | `rapport.py` |
| `garmin-fit/` **and both zips** | `gen-fit.ts` **then** `zip_fit.py` |
| **Google Calendar** | payloads from `agenda.py`, pushed over MCP |
| Scheduled task, memory, docs | by hand |

Changing a session's time in the calendar is a change of plan. It propagates everywhere, or it
doesn't happen.

---

## Calendar text is generated, never typed

**No session description is ever written by hand into Google Calendar.** An event's text is a
deterministic function of the plan:

```
description = generated week header + the session's humanReadable field
```

Typing straight into the calendar creates a second source of truth, and two sources always
diverge. In practice this produced two incompatible versions of the same strength session —
different day, time, exercise count and intensity instruction — while a third session didn't exist
in the calendar at all.

**Three axes held aligned, not one:**

| Axis | Carried by | Verified by |
|---|---|---|
| Date and time | the plan, or the real date once the session is done | `agenda.py verifier` |
| Completion | Strava via `marquer_realise.py` → ✅ and grey | `agenda.py verifier` |
| Content | `humanReadable`, character for character | truncated SHA-256 fingerprint |

**A completed session carries its real date, time and duration**, not the prescribed ones. A
session moved within the week stays legitimate; a calendar that lies about the past is useless.

```bash
python3 harness/agenda.py generer <week>   # exact payloads
   # push over MCP without rewording a single word
   # read the calendar back into suivi/agenda-reel.json
python3 harness/verifier_sync.py           # must exit 0
```

The comparison runs against **what is actually in the calendar**, never against what was believed
to have been pushed. It fails on a missing event, a different date or time, a text differing by one
character, an event present in the calendar but absent from the plan, or a readback older than the
last real content change.

To move a session's time without touching the plan — a personal commitment that evening — use
`suivi/agenda-horaires.json`. Moving it in Google Calendar directly would be flagged as drift on
every later run.

> Google Calendar doesn't render Markdown. Asterisks show up literally — use capitals.

---

## Reading data without fooling yourself

Full protocol in [`METHODE-DONNEES.md`](METHODE-DONNEES.md) *(French)*. It exists because four
extraction bugs produced confident, wrong conclusions — three of them about sleep. All four were
caught by the athlete comparing figures against his own Garmin app, none by any test. Hence the
tests.

`valider.py` must pass before any numeric review.

| Test | Principle | What it would have caught |
|---|---|---|
| **Zero variance** | A field constant across hundreds of days is almost always the wrong field | Resting HR frozen at 43–44 for 447 days |
| **Physiological bounds** | Sleep 4–12 h · resting HR 35–70 · phases ≤ duration | A 24-minute night, a 16-hour nap |
| **Cross-source reconciliation** | On overlapping days, the full export and the daily exports must agree | All four, without exception |

The four bugs:

1. **Sleep duration** summed the gaps between phase markers — under-reporting by up to four hours
   (3 h 50 recorded for a real 7 h 47). Use session events, not phase sums.
2. **Resting heart rate** read from `restingHeartRate`, a frozen rolling reference, instead of
   `currentDayRestingHeartRate`. Wrong in *both* sources — 447 days.
3. **Two definitions of sleep** mixed depending on source: time in bed versus time asleep.
4. **The last day of a Garmin export is partial**, and was overwriting a complete day.

> **Day framing.** A row dated D covers the night *ending* on the morning of D. A Monday-to-Sunday
> week is complete with Sunday's export; Monday's belongs to the next week.

> `extract_garmin.py` **needs the export files as arguments**. Run bare, it re-displays existing
> data without ingesting anything — while printing a perfectly normal-looking table.

---

## The metrics

**Pace at constant heart rate** — efficiency index `speed ÷ heart rate`, extrapolated to 145 bpm.
The only figure that measures aerobic progress independently of weather and daily form. Everything
else on the dashboard is context.

**Temperature correction** — heat raises heart rate by roughly 0.65 bpm per °C above 15 °C. Across
a summer-to-spring build, that alone improves "pace at 145 bpm" by about 20 s/km. An artefact read
as progress. `meteo.py` fills it in automatically (Open-Meteo, city-level coordinates, no key, no
identifier); watches don't record ambient temperature and Strava doesn't expose it.

**Morning versus evening** — `moment_journee.py` separates the circadian effect from the
temperature effect, and **refuses to conclude** below five runs per slot. In summer a morning run
is also a 10 °C cooler run; without separating the two you measure the weather and call it
biology.

**Training load** — the concepts come from claude-coach's own coaching reference
(`skill/reference/load-management.md`): TSS, chronic and acute load, ramp-rate limits, recovery
monitoring. What this fork adds is computing them from actual data every week and acting on them.

---

## The rule that came out of all of it

> **A destination that isn't verified isn't synchronised.**
>
> Adding a step to the pipeline is not enough — a step can fail, be skipped, or be run by hand in
> the wrong order. Every destination ships with a test in `verifier_sync.py`, and every test is
> validated by injecting the fault it is supposed to catch.
>
> A check showing green on a broken chain is worse than no check at all.

This was learned twice. The second time, the watch archive had been a week stale — containing
sessions that had since changed — while every check reported success, because the checks looked at
the folder and nobody was looking at the zip.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| The **Code** tab offers a subscription | Free tier. Claude Code needs Pro or above. |
| Strava finds no activities | In order: inactive subscription, incomplete authorisation, disconnected connector. Type `/mcp`. |
| It asks for a Strava **Client ID** | Reply *"use the Strava connector already connected"*. |
| The Monday review didn't happen | App closed or machine asleep. Settings → Desktop app → General → **Keep computer awake**. Closing the lid sleeps it anyway. |
| It asks permission every week | Dry run not done, or you answered "allow once". |
| Second tab black on iPhone | Safari blocks local iframe includes. Embed via `srcdoc`. |
| Heart-rate zones look wrong | Strava zones rest on an estimated max HR. Rebuild from a measured lactate threshold. |
| Shoe kilometres stopped moving | The export is a snapshot. New kilometres go to the pair marked as currently worn. |
| HRV is empty | Not in the full export — only in the daily wellness exports. |
| Watch rejects workout files | Upstream encoding bugs. This fork fixes them; check you're not running `npx claude-coach@latest`. |
| Watch invisible over USB | Still in Garmin's USB mode — switch to **MTP** (hold MENU → Settings → System → USB Mode), then use an MTP client such as OpenMTP. Close Garmin Express first. |
| Two workouts, one entry on the watch | Identical internal names. Prefix with the date, date first. |
| It concludes something absurd from one week | Building a narrative on 7 days. Reply *"look at my whole history before concluding"*. |

> ⚠️ **Never run `npx claude-coach@latest`** if you depend on the FIT fixes — that's the published
> version, which still has them. Use the local build: `npx tsx src/cli.ts render ...`.
