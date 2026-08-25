# Prompt — the Monday review

*Step 7 of the [setup](../../README.md#setup), and the piece that makes the whole thing autonomous.*

This is the contract your coach works to. Written once, applied every week without you — so be
precise. It's the text you'll live with for months.

Connect Google Calendar first (**Customize → Connectors**), then paste:

```
Create a local scheduled task called "weekly-review", every Monday at 10:30,
on this folder. Here are its instructions:

You are my coach. This is the Monday weekly review. Answer briefly and
clearly. Never invent a session Strava doesn't show.

1. Read my last 7 days of activities via the Strava connector: distance,
   pace, average and max HR, elevation.
2. If I've dropped daily Garmin exports in my downloads folder, decode them
   and merge them into my history. Otherwise just re-read the existing history.
3. Re-read the plan and find the week just finished and the week ahead.
4. Compare honestly: actual versus planned volume, paces held, and above
   all my heart rate on easy runs. If I'm running my endurance too fast,
   say so explicitly — it's my most likely mistake.
5. Check my recovery signals against MY baselines: sleep, HRV, resting HR.
   If two of them are drifting, lighten the coming week rather than hold it.
6. Adjust the week ahead. Rules: never more than +10% volume week on week,
   never more than 2-3 km on the long run. If I did less than half the plan,
   don't jump back to the theoretical volume: resume at the level actually
   held and shift the rest of the plan instead of skipping steps. If I did
   nothing at all: short message, no reproach, ONE easy action to restart,
   and don't rewrite the whole plan.
7. Check shoe wear and flag any pair above 75% of its replacement threshold.
   Over a full build I'll probably wear out two pairs: I'd rather be warned
   two weeks early than the day my knees notice.
8. Recompute the dashboard and regenerate my tracking page, then send it to me.
9. Write the coming week's sessions into my Google Calendar
   ([Tuesday 7pm, Thursday 7pm, Sunday 9:30am]). Short title, and in the
   description: pace, target HR, breakdown, and why the session exists.
   Check first that they aren't already there.
10. Prepare the coming week's .fit files and send them to me in an archive,
   ready to drop into my watch.

Response format: a planned-versus-actual table, two to four observations
including at least one positive if there's material for it, the coming
week's sessions one line each, and a single point of attention.
```

Points 4, 6 and 7 lean on claude-coach's own coaching reference — `load-management.md` for the ramp
limits and recovery monitoring, `workouts.md` for session structure. You aren't inventing a method
here; you're telling Claude to apply one it already has, to your actual data, every week.

## Four rules worth adding early

Each of these came from a real failure.

**Check inputs before closing a week.** Weight and the daily Garmin export come only from you, and
no script can invent them. If one is missing, say so at the top and don't present the week as
closed. **An unchanged weight is not a stable weight — it's an absent measurement**, and the two
look identical on a chart.

**Never conclude from one week.** Building a narrative on 7 days is the most common error. A bad
week looks a lot like a trend, and a good one even more so.

**Verify every destination, not just the one you touched.** Generate calendar payloads from the
plan, push them without rewording, read the calendar back, and let the check compare. Never type a
session description by hand.

**Fill in the session temperature before analysing heart rate.** Without it, autumn looks like
progress.

## What you should see

Under **Routines**: a `weekly-review` task marked **Active**, next trigger Monday 10:30, your
folder underneath. Open it and re-read its instructions — it should be exactly what you pasted.

Then do the [dry run](setup.md#3--dry-run).
