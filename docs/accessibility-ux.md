# Accessibility and Alternate UX

Field Day logging should not require perfect vision, perfect pointing accuracy,
or a specific visual workflow. The rewrite prototype should keep alternate UX
paths available from the beginning so accessibility does not become a late
retrofit.

This document is written for the experimental `fdlogger_next` prototype. It
describes what is available now, what is only partially available, and what the
rewrite should grow toward.

For paper-log operators and cellphone-photo transcription, see
[`paper-log-ingest.md`](paper-log-ingest.md).

## Current Available Paths

### Command Line

The most usable non-visual path today is `fdlogger-next-cli`. It is verbose, but
it works in a terminal with the operator's preferred screen reader, terminal
font, shell history, aliases, and speech settings.

Setup from the checkout:

```bash
make install-dev
rehash
make commands
```

Create and use a prototype database:

```bash
fdlogger-next-cli accessible-test.db init

fdlogger-next-cli accessible-test.db add \
  --call K6ABC \
  --class-name 1A \
  --section SCV \
  --band 20 \
  --mode CW \
  --power 100 \
  --station station-1 \
  --operator AK6IM

fdlogger-next-cli accessible-test.db list
fdlogger-next-cli accessible-test.db score
fdlogger-next-cli accessible-test.db rebuild
```

The `list` command prints the QSO id first. Use that id for edit or delete:

```bash
fdlogger-next-cli accessible-test.db edit QSO_ID --section SV
fdlogger-next-cli accessible-test.db delete QSO_ID
```

Useful shell aliases for practice:

```bash
alias fdn='fdlogger-next-cli accessible-test.db'
fdn add --call K6ABC --class-name 1A --section SCV --band 20 --mode CW --power 100
fdn list
fdn edit QSO_ID --section SV
fdn delete QSO_ID
fdn score
```

### Prototype GUI

The current `fdlogger-next` PyQt5 GUI now sets accessible names and descriptions
on the main QSO fields, buttons, score label, status bar, database label, and
contact table. Field labels are linked to their input widgets.

That is a baseline, not a complete accessibility solution. Screen reader
quality depends on the OS, Qt accessibility bridge, and the screen reader in
use.

## Known Limitations

- The GUI has not yet been tested with VoiceOver, NVDA, JAWS, or Orca.
- The CLI add command is too verbose for high-rate live operation.
- The GUI table may still be awkward for screen readers.
- Duplicate warnings and status messages need real screen reader testing.
- Color, visual layout, and table position should not be treated as sufficient
  status indicators.
- There is no dedicated text-user-interface or speech-first operator mode yet.

## Accessibility Requirements

The rewrite should treat these as product requirements, not polish:

- Full keyboard operation for normal QSO logging.
- Predictable tab order.
- Enter logs the current QSO.
- Esc clears the current QSO.
- Sticky defaults for band, mode, power, class, section, station, and operator.
- All controls have accessible names.
- Status changes are available as text, not only color or icons.
- Duplicate warnings are keyboard reachable and default to the safe option.
- High contrast and large-font operation remain usable.
- The log can be reviewed without relying on visual table layout.
- All core workflows are available outside the GUI.

## Alternate UX Roadmap

### Short Term

- Add preference persistence so a CLI or GUI operator does not need to repeat
  station, operator, class, section, band, mode, and power.
- Add a faster CLI logging command with positional arguments or an interactive
  prompt mode.
- Add CSV export for quick review in accessible tools.
- Test `fdlogger-next` with macOS VoiceOver and at least one Linux screen reader.
- Document successful and unsuccessful screen reader combinations.

### Medium Term

- Add a curses/textual-style operator mode or a line-oriented interactive mode.
- Add a screen-reader-friendly log review command.
- Add reviewed paper-log CSV import as another non-GUI input path.
- Add configurable spoken or terminal-bell alerts for duplicate and error states.
- Add explicit diagnostics commands for score, QSO count, last QSO, and pending
  sync state.
- Include accessibility checks in practice-session testing.

### Long Term

- Make accessible operation part of release acceptance.
- Test with operators who actually use assistive technology.
- Keep GUI, CLI, and recovery tooling behavior consistent.
- Provide a club setup guide for accessible stations.

## Practice Test Checklist

Before a club tries this with a sight-impaired operator, run a short practice
session:

- Confirm the chosen screen reader can read the command output or GUI fields.
- Log at least 20 contacts.
- Trigger and dismiss a duplicate warning.
- Edit one contact.
- Delete one contact.
- Rebuild contacts.
- Export or list the log for review.
- Confirm score and QSO count are understandable without visual inspection.

Record which OS, screen reader, terminal, font size, and workflow were used.
That feedback should drive the next UI slice.
