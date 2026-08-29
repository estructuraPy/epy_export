# Changelog

All notable changes to epy_export are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **First cut of the shared export engine.** The ePy document family had
  five applications doing the same four things in separate copies. This
  library is where those now live once.

  - `_core/_pdf_stamp` — the PDF stamping that existed twice, as 546
    lines differing in eight, all of them comment text. Renamed from
    `_pdf_footer`: it stamps backgrounds, watermarks, headers, footers
    and metadata, and the footer is one of five. `creator` and
    `producer` became **required keywords with no default**, because
    four applications share one frozen runtime and a default there is a
    global that mislabels a PDF the day the wrong caller omits it.
  - `_core/_frontmatter` — the front-matter parser that existed twice,
    byte for byte. Ported unchanged, deliberately: every title, footer
    and watermark path already written was parsed by these exact rules,
    quoting quirks included.
  - `_core/_runtime` — the ICU pin that existed three times, two of its
    copies documenting that they mirrored the first.
  - `_core/_backends` — one answer to "is this engine here". The two
    bridges asked differently (`import_module` vs `find_spec`) and
    disagreed on a package that is present but broken. Both mechanisms
    are kept for their two different jobs: `backend_present` imports
    nothing, because it answers while a menu is being built;
    `load_backend` raises named, at the moment of use.
  - `_core/_qt_print` — the print plumbing, **with a clock per wait**.
    One shared clock makes every later budget the leftover of the
    earlier stage, which produces a deck of one blank page reported as a
    success. `wait_until` starts its own clock; that is why it exists.
  - `epy_suite_connect/` — the engine registry and one adapter per
    producing sibling, which is what dissolved the
    `if engine_id == "papers"` chain the dispatcher used to carry.

### Fixed

- **The two failures were one type.** The check that refuses a truncated
  PDF — written after a three-of-ten-page file passed a file-exists test
  — raised the *engine unavailable* error, so a partial document was
  reported to the reader as "epy_docs is not installed". One of those is
  fixed by installing something and the other never is. Split into
  `BackendUnavailableError` and `RenderFailedError`.
- **The LaTeX log is now read for every caller.** `epy_reports` had no
  equivalent check, so it has been accepting exactly this class of
  partial document.
- **An option meant for another engine is refused by name.** Passing a
  journal profile to ePy Reports was silently dropped, so a caller who
  believed they had asked for a journal draft received a report and no
  signal — the same failure the format check already refused.
- **A misspelled appearance is refused.** It otherwise reached the
  engine, which fell back to its own default, and the document arrived
  looking almost right.
- **`epy_papers` refuses to invent a journal.** Measured: an empty id
  reached `profile("")` and came back as a bare `KeyError: ''`.
