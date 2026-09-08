# Changelog

All notable changes to epy_export are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] — 2026-09-08

### Added

- **`prepend_pdf` and `append_pdf`: joining a reader's own PDF pages to
  a rendered document.** WHERE a page is joined is the whole design.
  Pages joined BEFORE the stamping are numbered with the document;
  pages joined AFTER it are not. That is how a cover template supplied
  by the reader stays unnumbered front matter while annexes continue
  the body's numbering, without one change to how numbering works.

  A page of another size is FITTED to the document's sheet rather than
  left at its own: a cover drawn on A4 dropped into a Letter report is
  visibly the wrong size, and nobody who supplied a template asked for
  one page of their report to be a different shape. It is fitted, not
  stretched, and a page already the right size is left untouched --
  scaling by exactly one still rewrites the content stream.

  A file that is not there is named, and ALL of them are named at once:
  the library raises on the first it cannot open, so a reader who
  mistyped two paths would fix one, run again, and be told about the
  other. And the merge clones rather than building a fresh writer,
  because a fresh one drops the document catalogue and with it the
  named destinations the index links to.

- **`require_pdfs`: the same refusal, callable before rendering.** The
  check the joining does was only reachable BY joining, so an
  application that renders for a minute and then joins could only
  discover a mistyped path after paying for the render — and, in a
  window, deliver it as a bare "export failed" with no reason in it.
  It is one implementation and one message, used by the joining and by
  the callers that want to fail early.

## [0.3.0] — 2026-09-08

### Added

- **`backend_route`: one answer to "can this process reach the engine",
  and one that is right inside a frozen bundle.** Every application
  asked whether ePy Docs imports HERE, and PyInstaller closes
  `sys.path` to the bundle, so that question has a permanently wrong
  answer in every shipped executable: "export through ePy Docs" has
  been greyed out for every user since the first release, ePy Draft's
  DEFAULT engine included. The route answers `in_process` when the
  import works, `subprocess` when ePy Studio has named an interpreter
  that carries it, and `none` otherwise. `available()` and therefore
  `installed()` now ask the route rather than the import.

- **`ENV_DOCS_PYTHON`, with one home.** ePy Studio publishes the
  variable and the applications read it, and neither package depends on
  the other. Named here, where both already depend, a rename cannot
  leave one side listening for a variable the other stopped setting.

- **The ePy Docs render runs out of process when it has to.** The call
  sequence is built once as DATA and applied twice: to a writer imported
  here, or to one in the interpreter Studio found, reached with `-c` and
  handed the job on stdin. One definition, two executions, so a document
  cannot change because the renderer moved to another process — there is
  a corpus rendered the old way, and a test compares the two sequences
  against a real child interpreter.

  Three things the wrapper respects, all measured: the child's exit code
  is NOT the signal, because without Quarto the library swallows the
  failure, logs it at INFO and exits zero, so the produced files on disk
  are what is checked; the child's stderr travels back, because the
  library's own diagnosis is the message a reader can act on; and a
  child that hangs is given up on, because a wrong interpreter must not
  hang the application for ever.

- **`DOCUMENT_TYPES`, beside `APPEARANCES`.** A dialog that asked the
  engine for its layouts and document types could not be BUILT inside
  a frozen bundle, where the engine cannot be imported, so the export
  entry stayed unreachable for a second reason. Both vocabularies now
  live here, which every application already carries, and a test
  compares them with the engine wherever it can be reached so the
  copy cannot drift in silence.

- **`RenderOptions.document_type`, and the dispatcher forwards it.**
  The kind is chosen in a dialog and only ePy Docs reads it, but it
  stopped at the dispatcher, which always passed the default: a
  reader who asked for a notebook received a report and no signal,
  which is precisely the failure RenderOptions exists to refuse.
  Asking another engine for a document kind is now refused by name,
  and so is a kind nobody publishes -- symmetric with the appearance
  check, because a typo reaching the writer produces a document of
  the DEFAULT kind, which looks like a correct render of the wrong
  thing.

- **One export dialog for the three editors**, in `_ui`. It is the
  same two combos, the same directory picker, the same format
  checkboxes and the same three remembered keys in each of them;
  only the registry scope and the two translators differ, so those
  are passed in. Three copies of one window is the shape this suite
  has been paying for elsewhere. The subpackage is never imported by
  the facade, so a caller who only wants to read front matter still
  pays nothing for Qt.

## [0.2.0] — 2026-09-05

### Added
- **`is_truthy`**, the front-matter truth test the two editors each kept
  their own copy of. They differed only in how much of the rule their
  docstring wrote down; the accepted spellings were already identical,
  which is the shape a duplicate takes just before the two drift.

### Fixed
- **`extract_anchor_pages` raised on a PDF it promised to survive.** It
  added one to whatever pypdf answered for a destination's page number,
  and pypdf answers None for a destination it cannot place -- so a single
  unplaceable anchor raised TypeError inside the helper whose contract is
  "returns an empty dict rather than failing". Unplaceable anchors are
  skipped now.

### Changed
- A pinned pyright configuration, so this repository and a developer's
  local run evaluate the same tree. Zero errors, zero warnings.

## [0.1.0] — 2026-09-04

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
