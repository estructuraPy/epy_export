# epy_export

The shared export engine of the ePy document family.

Author: Ing. Angel Navarro-Mora M.Sc.

## What this is for

`epy_reports`, `epy_slides`, `epy_papers`, `epy_draft` and `epy_docs`
produce different documents through genuinely different technology —
Paged.js, reveal.js, LaTeX. **This library does not try to make them
one.** What it owns is everything they were doing *identically*, in
separate copies:

| Concern | Where it lived before |
|---|---|
| Stamping a finished PDF | `_pdf_footer`, twice — 546 lines differing in 8, all comment text |
| Reading front matter | `_core/snippets`, twice — byte for byte identical |
| Pinning ICU before Qt loads | three times; two copies documented that they mirrored the first |
| Driving a headless print | reimplemented twice, and the two **diverged** |
| Reaching `epy_docs` | twice, **incompatibly**; two of the four apps could not reach it at all |

A fix to any one of those reached the others only if somebody remembered.

## Install

```
pip install epy_export           # front matter, the engine registry
pip install epy_export[pdf]      # + stamping (pypdf, reportlab, Pillow)
pip install epy_export[qt]       # + the headless print plumbing
```

Nothing is required by default, on purpose. A caller who only wants to
read a document's header pays for nothing else, and a missing extra
raises a named `RuntimeError` at the call rather than an `ImportError`
from a dependency the caller never chose.

## Use

```python
from pathlib import Path
from epy_export import RenderOptions, installed, render

installed()          # ('reports', 'slides')  -- what is on THIS machine
render(
    Path("answer.md"),
    Path("out"),
    engine_id="slides",
    formats=("pdf", "pptx"),
    options=RenderOptions(appearance="corporate"),
)
```

## Two rules this library keeps

**Refuse by name; never skip.** A format an engine cannot produce, an
option another engine reads, an appearance that does not exist — each
raises, naming what was asked and what is offered. Silently producing
two of three requested files is how a caller comes to believe it has a
`.docx` it never got.

**Success is not evidence of content.** A print engine reports success
for a blank page, and LaTeX leaves a partial PDF on disk after aborting.
So readiness is *asserted* before printing, the LaTeX log is read, and
every produced file is checked — because "the file exists" once passed a
three-page PDF of a ten-page document.

## Layout

```
src/epy_export/
  _core/_runtime/       pin_system_icu()
  _core/_backends/      backend_present() / load_backend()
  _core/_frontmatter/   parse_front_matter() and friends
  _core/_pdf_stamp/     background, watermark, header, footer, metadata
  _core/_qt_print/      pump, eval_js, wait_until, print_to_pdf
  epy_suite_connect/    _contract/ (what an engine is)
                        _data/     (which engines exist)
                        _adapters/ (how each is driven)
```

`epy_suite_connect/` is the only place a sibling package is named, and
every one of them is reached by module name *at call time*. That is what
keeps the dependency graph a tree: the applications import this library;
this library imports no application.

## License

MIT. See `LICENSE`.
