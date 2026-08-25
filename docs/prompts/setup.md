# Setup prompts

Three short prompts referenced from the [README](../../README.md#setup). Everything in
`[brackets]` is yours to replace.

---

## 1 · Install the coach skill

*This installs [claude-coach](https://github.com/felixrieseberg/claude-coach) itself — the engine
that builds your plan.*

```
Install the "coach" skill from the claude-coach project: download
https://github.com/felixrieseberg/claude-coach/releases/latest/download/coach-skill.zip
and unzip it into ~/.claude/skills/coach/ (the zip contains SKILL.md at the root
and a reference/ folder). Then reload skills and confirm /coach is available.
```

**You should see** `/coach` in the list when you type `/`. If not, run `/reload-skills`.

Then let it build your plan:

```
Use the coach skill to build a plan for [race name] on [DD/MM/YYYY]. Take my data
via the Strava connector already connected, not through your own Strava access.
```

That second sentence matters: without it the skill offers its older Client ID route, which the
official Strava connector makes unnecessary.

The skill runs the interview from there — how many days a week you can train, your long-session
ceiling, your target, injuries, travel. Two things worth asking for if it doesn't offer them:

- **An honest verdict.** *"Is my target realistic, and if not, what is?"* A useful truth beats a
  flattering plan.
- **Where your zones come from.** Strava's usually rest on an estimated max heart rate.

> ⚕️ A plan produced by an AI is a proposal. It has not examined you and knows nothing about a
> niggle that won't go away. Medical history, doubt, pain that settles in: that's between you and a
> professional.

---

## 2 · Load your Garmin history

*This is what gives you sleep, HRV and resting heart rate — none of which Strava carries.*

Unzip the export Garmin emailed you, then:

```
I've received my full Garmin export, unzipped at [folder path].
Write an import script that produces a single daily history file with, for each day:
sleep and its phases, resting HR, steps, stress, and anything else useful.
Also extract separately my VO2max trend, race predictions and training load.

Also extract my shoes: the export contains a gear file with cumulative kilometres
per pair and the replacement threshold I set in Garmin. Put that in a separate
small file, marking which pair I'm currently wearing.

Then tell me my real baselines computed over the whole history: mean and median
sleep, resting-HR range, and the thresholds above which you consider I'm drifting.
I want thresholds computed on my data, not general values.
```

That last paragraph is the important one. General thresholds can't tell you that *you* are
drifting.

> ⚠️ **Two different Garmin exports — don't confuse them.**
>
> The **full export** is requested once from garmin.com → Data Management. It carries the long
> history: sleep, resting HR, steps, stress, VO2max.
>
> The **daily wellness export** is requested one date at a time, from connect.garmin.com →
> Settings → Account Information → bottom of the page. It carries the one thing the full export
> lacks: **heart-rate variability**. Seven clicks for a week, and it's optional.

---

## 3 · Dry run

Don't let the first real Monday also be the first test. The first run asks for permissions, and if
nobody's there to answer, the task sits waiting.

**Routines** → your task → **Run now**. Stay at the screen, choose **always allow** on every
prompt, and read what it produces. Then:

```
Remember for all our future sessions: my goal and its date, my HR zones and what they're
based on, my training days, my recovery baselines, and the two or three most important
things you've understood about how I train — including my weaknesses. Then show me what
you wrote.
```

Re-read what it saved. An error there repeats every week.
