# Python Solution Conventions

This repository standardizes algorithm solutions to Python-first files.

## Structure

- `problems/`: migrated markdown with Python code blocks.
- `solutions/`: one Python solution file per source markdown/code artifact.
- `assets/`: copied images used by markdown documents.
- `templates/solution_template.py`: canonical style template.

## Coding Conventions

- Use `from __future__ import annotations` when needed.
- Prefer `class Solution` + method signatures expected by LeetCode.
- Keep helper functions private and colocated in the same file.
- Use `typing` annotations for public methods.
- Add concise comments only for non-obvious transitions.
- Keep line endings as LF and encoding UTF-8.

## Placeholder Policy

Some files are auto-converted placeholders when no reliable Python snippet
exists in source content. Placeholder files always include:

- source path metadata
- original snippet in `ORIGINAL_SNIPPET`
- `NotImplementedError` marker

These files are valid Python and easy to search for manual completion.
