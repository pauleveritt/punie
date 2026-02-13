---
name: diary-log
description: Organize intermediate project Markdown notes into a dated diary format. Use when new or existing root-level status/summary Markdown files need to be moved into docs/diary with frontmatter, a date line under the H1, and a reverse-chronological index update.
---

# Diary Log

## Overview

Turn ad hoc project notes into consistent diary entries. Adds frontmatter, inserts a date line under the H1, moves files into docs/diary, and updates docs/diary/index.md with summaries.

## Workflow

### 1) Identify diary candidates

- Target root-level Markdown files that are intermediate notes, status updates, or summaries.
- Exclude `README.md`, `CLAUDE.md`, and `docs/diary/index.md`.

### 2) Determine entry date

- Use filesystem mtime for the date.
- Format as `YYYY-MM-DD`.

### 3) Add frontmatter summary

- Prepend frontmatter at the very top:
  ```
  ---
  date: YYYY-MM-DD
  summary: <one-sentence summary>
  ---
  ```
- Keep the summary short and specific.

### 4) Insert italic date under the H1

- Ensure the file has an H1 (`# Title`). If missing, add one based on the document title.
- Insert `*YYYY-MM-DD*` on the line directly below the H1, separated by blank lines for readability.

### 5) Move into docs/diary

- Move the file to `docs/diary/` and keep its filename unchanged.
- Preserve the body content (do not remove existing date or status lines unless asked).

### 6) Update the diary index

- Update `docs/diary/index.md` in reverse chronological order (newest first).
- Use this entry format and include the summary line:
  ```
  ## YYYY-MM-DD - [Title](FILENAME.md)
  Summary sentence.
  ```

## Quality checks

- Confirm frontmatter date matches mtime.
- Confirm the italic date line exists under the H1.
- Confirm index ordering and links are correct.
