# Demo page — where the README screenshots come from

**Everything here is fictional.** A made-up athlete (Alex Rivera), a made-up race (Valencia
Marathon), and a made-up set of numbers. A real dashboard holds health data and a real race date,
which have no place in a public repository.

```bash
./docs/demo/shoot.sh
```

Rebuilds `demo.html`, splits it into one page per section, screenshots each with headless Chrome, and
writes the JPEGs into `docs/images/`.

| File | Role |
|---|---|
| `_style.css` | Extracted verbatim from `harness/rapport.py` — so the demo looks exactly like the real tracking tab |
| `build_demo.py` | Builds `demo.html` from the fictional data declared at the top of the file |
| `split_sections.py` | One standalone page per section, sized to its content |
| `shoot.sh` | Runs the whole chain |

## What this does *not* cover

**The programme tab is upstream's viewer, and is not reproduced here.** `docs/images/upstream-viewer.jpg`
is [claude-coach](https://github.com/felixrieseberg/claude-coach)'s own published screenshot, used
with credit.

An earlier version of this demo did mock up that interface, and got it wrong — it invented a button
labelled "Export Plan — Calendar, Zwift, Garmin, TrainerRoad" where upstream actually shows "Export to
Calendar / Download .ics file". Reproducing someone else's UI from memory produces a plausible
forgery, not documentation. Don't reintroduce it.

## Maintenance

If the real tracking tab is restyled, re-extract the stylesheet:

```bash
python3 - <<'PY'
import re; from pathlib import Path
css = re.search(r"<style>(.*?)</style>", Path("harness/rapport.py").read_text(encoding="utf-8"), re.S).group(1)
Path("docs/demo/_style.css").write_text(css.replace("{{","{").replace("}}","}").strip(), encoding="utf-8")
PY
```

Section heights in `split_sections.py` are declared, not measured — measuring them would need a
browser in the loop. If a capture clips or carries dead space at the bottom, adjust the number and
re-run.

Only colour classes that exist in the stylesheet will render: `c-run`, `c-gold`, `c-blue`. Asking for
anything else silently produces an invisible line.
