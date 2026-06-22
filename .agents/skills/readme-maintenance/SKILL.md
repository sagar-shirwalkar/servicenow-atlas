---
name: readme-maintenance
description: >-
  Patterns for keeping READMEs accurate as code evolves. Focused on structural
  consistency, not prose style. Use when editing a README with ASCII tree
  diagrams, version callouts, config examples, or cross-document line ranges.
  Avoids generic "write clearly" advice — targets the concrete rot patterns
  that accumulate in docs-heavy repos.
---

## When to use

- Adding/removing/renaming a file in the project — is the tree diagram still right?
- Changing a CLI flag, config key, or command signature — are all code blocks updated?
- Bumping a version — does the "current version" note need updating?
- Changing architecture (e.g., swapping build strategy) — are all prose claims still true?
- Adding or removing a section — does the table of contents still match?
- Editing the README at all — always check for stale claims while you're there.

## Rot patterns to catch

### 1. Stale prose claims

Assertions about how the system works that were true at vN but wrong at vN+1.
Search the README for every occurrence of the changed concept.

Common culprits:
- **Build/deploy strategy** — "CI does X" after CI was rewritten
- **Default behavior** — "the server auto-selects Y" after the default was changed to Z
- **Dependency claims** — "requires pandas" after it was removed
- **Status labels** — `[planned]` on something now implemented, or vice versa

### 2. Broken section references

Internal links `[§5.3](#53-smoke-test-ci)` break when section headings change.
After editing any heading, grep the README for the old anchor text and update
every cross-reference.

### 3. Version note rot

Many READMEs have a "current version" callout box. This should be updated on
every release — at minimum the version number and a one-line summary of what
changed. If you bump the version in pyproject.toml but not the README note,
it's wrong.

### 4. ASCII tree diagram drift

Directory structure diagrams (`├── foo.py  description`) rot silently because
they look right at a glance. After any file add/remove/rename:

- Verify every file in the diagram still exists
- Verify every file in the project that matters is listed
- **Align descriptions vertically** — pick a column position for descriptions
  and pad every filename to it. Use monospace alignment: the longest filename
  in the diagram sets the column for its nesting level.

  Bad (misaligned):
  ```
  ├── foo.py        Does X
  ├── bar.py                  Does Y
  ├── baz-long-name.py   Does Z
  ```

  Good (aligned):
  ```
  ├── foo.py                                  Does X
  ├── bar.py                                  Does Y
  ├── baz-long-name.py                        Does Z
  ```

### 5. Configuration block drift

JSON, YAML, and TOML blocks in READMEs are often copied from config files
during writing and never updated. After changing a config schema:

- Grep the README for any code block containing the changed key
- Update the example to match the actual schema
- If examples reference specific paths, verify those paths still exist

### 6. Command output / flag drift

After changing a CLI tool's flags or output format:

- Find all ` ```bash ` blocks in the README that invoke the tool
- Verify every flag used still exists
- If the README claims a command produces specific output, verify that

### 7. File outline line range drift

If the README has a navigation outline with `[L42-57]`-style line ranges,
they will shift on every edit. Update them whenever the file length changes
or content moves. One reliable approach:

1. After all edits are done, get the current line count: `wc -l README.md`
2. Grep for each section heading to get its new line number
3. Update every range in the outline

## Recommended workflow

When editing a README, do this in order:

1. Understand what changed in the code (`git diff` if it's a code change,
   otherwise ask the user what the new behavior is).
2. Search the README for every mention of the changed concepts.
3. Make all edits.
4. After edits, update the file outline (if any) and table of contents.
5. Re-read the changed sections one final time to catch anything missed.
