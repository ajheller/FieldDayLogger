# Paper Log Ingest and OCR Workflow

Paper logs should be treated as a supported offline input path, not as a weird
exception. They are useful for operators who prefer paper, operators who need a
non-screen workflow, and stations recovering from laptop, power, or network
trouble.

This document describes a practical route for bringing paper logs into the
rewrite event store while preserving auditability.

## Goals

- Let paper-log operators participate without forcing a screen workflow.
- Preserve the original paper sheet as the audit source.
- Avoid silent OCR or LLM corrections.
- Let a human review every transcribed row before import.
- Import reviewed rows as append-only QSO events with paper-source metadata.
- Run duplicate detection and reconciliation against electronic logs.

## Recommended Event-Day Paper Sheet

Printable paper sheets should use the same fields the app expects:

- sheet id
- row number
- date
- time
- call
- class
- section
- band
- mode
- power
- operator
- notes

The top of each sheet should include station defaults when possible:

- club call
- station id
- band
- mode
- power
- operator
- page number

Numbering sheets and rows matters. Later, a questionable imported contact can be
traced back to `sheet 3 row 12` instead of becoming folklore.

## Photo Capture Workflow

1. Write contacts on numbered paper sheets.
2. Photograph each sheet with a cellphone after the operating block or at the
   end of the event.
3. Keep the original paper until final submission is complete.
4. Name photos consistently, for example:

```text
FD2026-station1-sheet03.jpg
FD2026-station1-sheet04.jpg
```

5. Store photos in a shared club folder or local recovery folder.
6. Transcribe photos into a strict CSV template.
7. Human-review the CSV against the photo.
8. Import only reviewed CSV rows into FieldDayLogger.

## LLM/OCR Transcription

ChatGPT, Claude, or another OCR tool can be helpful for transcription, but its
output should be treated as a draft. Callsigns, sections, times, and band/mode
fields are compact and easy to misread. A confident one-character error can
break a contact.

Do not import OCR or LLM output directly without review.

Recommended prompt:

```text
Transcribe this Field Day paper log sheet into CSV.

Use this exact header:
sheet_id,row_number,date,time,call,class,section,band,mode,power,operator,notes

Rules:
- Do not guess unclear characters.
- Use [unclear] for anything you cannot read.
- Preserve handwritten values exactly.
- Do not correct callsigns or ARRL sections.
- One paper row equals one CSV row.
- Output CSV only.
```

Recommended CSV header:

```csv
sheet_id,row_number,date,time,call,class,section,band,mode,power,operator,notes,source_image
```

The `source_image` column should point back to the photo filename.

## Review Rules

Before import:

- Compare every CSV row against the photo.
- Replace `[unclear]` only when a reviewer can confidently read the paper.
- Do not silently normalize callsigns or ARRL sections during review.
- Keep notes when a row is ambiguous.
- Mark reviewed files with reviewer initials or a separate review log.

Suggested review metadata:

```text
transcribed_by = ChatGPT / Claude / OCR / human call sign
reviewed_by = reviewer call sign
reviewed_at = timestamp
source_image = FD2026-station1-sheet03.jpg
```

## Import Model

Imported paper rows should become normal `qso.created` events with extra source
metadata. The contact should behave like any other QSO after import, but its
origin should remain auditable.

Suggested event metadata:

```text
source = paper_ocr
sheet_id = FD2026-station1-sheet03
row_number = 12
source_image = FD2026-station1-sheet03.jpg
transcribed_by = ChatGPT
reviewed_by = AK6IM
```

If a human typed the paper sheet directly without OCR:

```text
source = paper_manual
```

## Duplicate and Reconciliation Rules

Paper imports should go through the same duplicate detection as live electronic
logging.

Import should flag, not silently merge, likely duplicates:

- same call, band, and mode
- nearby timestamps
- same class and section

Reviewers can then decide whether to:

- skip the paper row because it duplicates an electronic QSO
- import it as a separate contact
- edit an existing QSO
- keep both while adding a note for post-event cleanup

## Future Tooling

Short-term:

- printable paper log sheet template
- CSV import command for reviewed paper logs
- import preview with duplicate warnings
- source metadata on imported events

Medium-term:

- guided row-by-row paper entry mode
- OCR/LLM prompt templates included in docs
- import report listing accepted, skipped, duplicate, and unclear rows
- photo filename and sheet/row references visible in QSO history

Long-term:

- optional local OCR integration
- side-by-side image and CSV review UI
- club recovery workflow that merges paper, local DBs, and hub logs

## Acceptance Checklist

Before relying on this workflow at a club event:

- Print and test sample paper sheets.
- Photograph at least one completed sheet.
- Transcribe with the chosen OCR/LLM tool.
- Human-review the CSV.
- Import into a test database.
- Confirm duplicate warnings are understandable.
- Confirm imported contacts export correctly.
- Confirm each imported QSO can be traced back to sheet id, row number, and
  source image.
