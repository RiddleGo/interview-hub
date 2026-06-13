#!/usr/bin/env python3
from __future__ import annotations

import argparse
import py_compile
from pathlib import Path
from typing import Any


def sanitize_file(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return False
    except Exception:
        original = path.read_text(encoding="utf-8", errors="ignore")
        escaped = original.replace('"""', r"\"\"\"")
        sanitized = (
            '"""Auto-sanitized placeholder after syntax validation failure."""\n'
            "from typing import Any\n\n"
            "def solve(*args: Any, **kwargs: Any) -> Any:\n"
            '    raise NotImplementedError("Sanitized placeholder; manual Python rewrite required")\n\n'
            f'ORIGINAL_SNIPPET = """\n{escaped}\n"""\n'
        )
        path.write_text(sanitized, encoding="utf-8", newline="\n")
        return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Sanitize invalid Python solution files")
    parser.add_argument("--solutions", required=True, type=Path)
    args = parser.parse_args()

    total = 0
    fixed = 0
    for file in args.solutions.glob("*.py"):
        total += 1
        if sanitize_file(file):
            fixed += 1

    print({"total": total, "sanitized": fixed})


if __name__ == "__main__":
    main()
