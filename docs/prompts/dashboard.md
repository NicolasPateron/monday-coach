# Prompt — the tracking tab

*Step 6 of the [setup](../../README.md#setup).*

claude-coach has already produced your plan and its viewer. This builds **the other tab** — the one
that tracks what you actually did — and wraps both into one file you open on your phone.

```
Build my tracking dashboard: ONE self-contained HTML file, two tabs, that I can
open on my phone.

TAB 1 — TRACKING. It opens on sentences, not charts:
3 to 5 plain-language observations about my week, each with a verdict
(fine / watch this) and the number that justifies it. Then the charts:
- planned versus actual volume, week by week
- my pace at constant heart rate (around 145 bpm): this is the only
  indicator that measures aerobic progress independently of weather and
  daily form — put it front and centre
- my weight against its target trajectory
- sleep, HRV and resting heart rate, each with MY normal band computed
  from my own history, not general values
- shoe wear: one gauge per pair, kilometres run against the replacement
  threshold, and the plan week each pair will reach its limit if it
  carries the planned volume

TAB 2 — PROGRAMME. Take the programme page the coach skill already
produced and EMBED it in the file (via srcdoc), without pointing at a
neighbouring file: Safari blocks that kind of include when the page is
opened from disk, and the tab would render black on iPhone.

Write whatever scripts are needed so everything regenerates with a single
command, keep a cumulative week-by-week journal, and give me one line per
file explaining what each one does.
```

## Three things not to change

**`srcdoc`, not `src`.** The precise setting that avoids a black second tab on iPhone. It isn't
addressed to you — it's addressed to Claude.

**"MY normal band computed from my own history".** Without this you get population averages, which
cannot tell you that *you* are drifting.

**Don't ask it to rebuild the programme tab.** claude-coach's viewer already exists, is well made,
and handles editing, completion and exports. The instruction is to *embed* it, not reimplement it.

## What you should see

A file that opens on both tabs, and a short list explaining each script it created. Send the page
to yourself and check it really opens on your phone — **both tabs**, not just the first.

The charts will be empty at first and fill in week by week. That's expected.

Then say what's missing. This is a conversation, not a one-shot prompt: the useful additions tend
to appear after you've stared at the page for a week.
