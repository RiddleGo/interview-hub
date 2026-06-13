#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PYTHON_LANGS = {
    "python",
    "py",
    "python3",
    "py3",
}

NON_PYTHON_LANGS = {
    "cpp",
    "c++",
    "cc",
    "c",
    "java",
    "go",
    "js",
    "javascript",
    "ts",
    "typescript",
    "rust",
    "rs",
    "csharp",
    "cs",
    "swift",
    "php",
    "kotlin",
    "ruby",
    "scala",
    "shell",
    "bash",
    "sh",
}

IMAGE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
}


@dataclass
class Counters:
    md_files: int = 0
    converted_blocks: int = 0
    kept_python_blocks: int = 0
    copied_assets: int = 0
    generated_solution_files: int = 0
    placeholder_solutions: int = 0


def normalize_lang(raw: str) -> str:
    s = (raw or "").strip().lower()
    if not s:
        return ""
    return s.split()[0]


def safe_stem(text: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", text.strip(), flags=re.UNICODE)
    s = s.strip("_")
    return s or "untitled"


def looks_python(code: str) -> bool:
    hints = ("def ", "class ", "import ", "from ", "elif ", "except ", "None", "True", "False")
    return any(h in code for h in hints)


def to_python_placeholder(code: str, from_lang: str, source_name: str) -> str:
    escaped = code.replace('"""', r"\"\"\"")
    return (
        f'"""Auto-generated placeholder converted from `{from_lang or "unknown"}`.\n'
        f"Source: {source_name}\n"
        "Manual rewrite may be required for algorithm equivalence.\n"
        '"""\n\n'
        "from typing import Any\n\n\n"
        "def solve(*args: Any, **kwargs: Any) -> Any:\n"
        '    """\n'
        "    TODO: Replace this placeholder with a real Python implementation.\n"
        "    Original source is preserved in ORIGINAL_SNIPPET.\n"
        '    """\n'
        "    raise NotImplementedError(\"Auto-generated placeholder; implement in Python\")\n\n\n"
        f'ORIGINAL_SNIPPET = """\n{escaped}\n"""\n'
    )


FENCE_RE = re.compile(r"```([^\n`]*)\n(.*?)\n```", re.DOTALL)


def convert_markdown(md_text: str, source_name: str, counters: Counters) -> tuple[str, list[tuple[str, str]]]:
    snippets: list[tuple[str, str]] = []

    def replace(m: re.Match[str]) -> str:
        raw_lang = m.group(1)
        code = m.group(2)
        lang = normalize_lang(raw_lang)
        nonlocal snippets

        if lang in PYTHON_LANGS or (not lang and looks_python(code)):
            counters.kept_python_blocks += 1
            snippets.append(("python", code.strip()))
            return f"```python\n{code}\n```"

        if lang in NON_PYTHON_LANGS or lang:
            counters.converted_blocks += 1
            py_code = to_python_placeholder(code.strip(), lang, source_name)
            snippets.append(("python", py_code.strip()))
            return f"```python\n{py_code}\n```"

        # Plain fence with unknown language: keep it but tag as text.
        return f"```text\n{code}\n```"

    converted = FENCE_RE.sub(replace, md_text)
    return converted, snippets


def choose_solution_snippet(snippets: Iterable[tuple[str, str]]) -> tuple[str, bool]:
    for lang, code in snippets:
        if lang == "python" and "NotImplementedError" not in code:
            return code, False
    for lang, code in snippets:
        if lang == "python":
            return code, True
    return (
        '"""No fenced code block found in source markdown."""\n'
        "def solve() -> None:\n"
        "    raise NotImplementedError\n",
        True,
    )


def derive_solution_name(path: Path) -> str:
    stem = path.stem
    m = re.match(r"^(\d{1,4})[.\-_]?(.*)$", stem)
    if m:
        num = m.group(1).zfill(4)
        rest = safe_stem(m.group(2))
        return f"{num}_{rest}.py" if rest else f"{num}.py"
    return f"{safe_stem(stem)}.py"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def copy_asset(src: Path, src_root: Path, assets_root: Path) -> None:
    rel = src.relative_to(src_root)
    dst = assets_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def migrate(src_root: Path, dst_root: Path) -> Counters:
    counters = Counters()
    problems_root = dst_root / "problems"
    solutions_root = dst_root / "solutions"
    assets_root = dst_root / "assets"

    dst_root.mkdir(parents=True, exist_ok=True)
    for p in (problems_root, solutions_root, assets_root):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=True)

    solution_map: dict[str, dict[str, str | bool]] = {}

    for src in src_root.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(src_root)
        suffix = src.suffix.lower()

        if suffix in IMAGE_SUFFIXES:
            copy_asset(src, src_root, assets_root)
            counters.copied_assets += 1
            continue

        if suffix == ".md":
            counters.md_files += 1
            content = src.read_text(encoding="utf-8", errors="ignore")
            converted, snippets = convert_markdown(content, str(rel), counters)
            out_md = problems_root / rel
            write_text(out_md, converted)

            sol_name = derive_solution_name(src)
            sol_path = solutions_root / sol_name
            snippet, is_placeholder = choose_solution_snippet(snippets)
            header = (
                f'"""Python solution extracted from {rel.as_posix()}."""\n'
                "from __future__ import annotations\n\n"
            )
            write_text(sol_path, header + snippet.strip() + "\n")
            counters.generated_solution_files += 1
            if is_placeholder:
                counters.placeholder_solutions += 1

            solution_map[rel.as_posix()] = {
                "solution": sol_path.relative_to(dst_root).as_posix(),
                "placeholder": is_placeholder,
            }
            continue

        if suffix in {".cpp", ".cc", ".c", ".java", ".go", ".js", ".ts", ".rs", ".cs", ".php", ".sh"}:
            code = src.read_text(encoding="utf-8", errors="ignore")
            py_text = to_python_placeholder(code, suffix.lstrip("."), str(rel))
            out_path = solutions_root / f"{safe_stem(rel.as_posix())}.py"
            write_text(out_path, py_text)
            counters.generated_solution_files += 1
            counters.placeholder_solutions += 1
            continue

    manifest = {
        "source": src_root.as_posix(),
        "output": dst_root.as_posix(),
        "stats": counters.__dict__,
        "solutions": solution_map,
    }
    write_text(dst_root / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return counters


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate leetcode-master to Python-centric project tree.")
    parser.add_argument("--source", required=True, type=Path, help="Path to leetcode-master")
    parser.add_argument("--target", required=True, type=Path, help="Path to interview-hub/leetcode-python")
    args = parser.parse_args()

    counters = migrate(args.source, args.target)
    print(json.dumps(counters.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
