#!/usr/bin/env python3
"""
repo_to_latex_fixed.py

Convert a local Git repository or GitHub repository clone into a LaTeX document.

Usage:
    python3 repo_to_latex_fixed.py /path/to/repo output.tex
    python3 repo_to_latex_fixed.py /path/to/repo output.tex --title "Repository Report"

Then compile:
    pdflatex -interaction=nonstopmode -halt-on-error output.tex
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Set

EXCLUDE_DIRS: Set[str] = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "node_modules",
    "dist",
    "build",
    "target",
    ".next",
    ".venv",
    "venv",
    "env",
    ".tox",
    ".cache",
}

EXCLUDE_FILES: Set[str] = {
    ".DS_Store",
    "Thumbs.db",
}

TEXT_EXTENSIONS: Set[str] = {
    ".py", ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp",
    ".java", ".kt", ".scala", ".rs", ".go",
    ".js", ".ts", ".jsx", ".tsx",
    ".php", ".rb", ".pl", ".pm",
    ".sh", ".bash", ".zsh",
    ".f", ".for", ".f77", ".f90", ".f95", ".f03", ".f08",
    ".tex", ".bib",
    ".md", ".txt", ".rst",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".csv", ".sql", ".xml", ".html", ".css",
}

TEXT_ONLY_EXTENSIONS: Set[str] = {
    ".md", ".txt", ".rst", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".conf", ".csv", ".xml",
}

LISTINGS_LANGUAGE_MAP = {
    ".py": "Python",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".java": "Java",
    ".kt": "Java",
    ".scala": "Scala",
    ".rs": "Rust",
    ".go": "Go",
    ".js": "JavaScript",
    ".php": "PHP",
    ".rb": "Ruby",
    ".pl": "Perl",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".sql": "SQL",
    ".html": "HTML",
    ".xml": "XML",
    ".f": "Fortran",
    ".for": "Fortran",
    ".f77": "Fortran",
    ".f90": "Fortran",
    ".f95": "Fortran",
    ".f03": "Fortran",
    ".f08": "Fortran",
    ".tex": "TeX",
}

MAX_FILE_SIZE = 300_000  # bytes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a repository into a LaTeX document."
    )
    parser.add_argument("repo", help="Path to local repository")
    parser.add_argument("output", help="Output .tex file")
    parser.add_argument("--title", default=None, help="Optional document title")
    parser.add_argument(
        "--include-skipped",
        action="store_true",
        help="Append a list of skipped binary/large files",
    )
    return parser.parse_args()


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def ascii_safe(text: str) -> str:
    """
    Make text safe for pdflatex by replacing non-ASCII characters.
    """
    result = []
    for ch in text:
        code = ord(ch)
        if ch == "\t":
            result.append("    ")
        elif ch == "\n":
            result.append("\n")
        elif 32 <= code <= 126:
            result.append(ch)
        else:
            result.append("?")
    return "".join(result)


def is_probably_text(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    try:
        with path.open("rb") as f:
            chunk = f.read(4096)
        if b"\x00" in chunk:
            return False
        chunk.decode("utf-8")
        return True
    except Exception:
        return False


def safe_read_text(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            pass
    return "[Could not decode file as text]"


def should_skip_dir(name: str) -> bool:
    return name in EXCLUDE_DIRS


def should_skip_file(name: str) -> bool:
    return name in EXCLUDE_FILES


def collect_files(repo_root: Path) -> List[Path]:
    out: List[Path] = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in sorted(dirs) if not should_skip_dir(d)]
        files = sorted(files)
        root_path = Path(root)
        for fname in files:
            if should_skip_file(fname):
                continue
            full_path = root_path / fname
            rel = full_path.relative_to(repo_root)
            if any(part in EXCLUDE_DIRS for part in rel.parts):
                continue
            out.append(full_path)
    out.sort(key=lambda p: str(p.relative_to(repo_root)).lower())
    return out


def build_ascii_tree(repo_root: Path, files: List[Path]) -> str:
    """
    ASCII-only tree to avoid pdflatex UTF-8 problems.
    """
    lines = [repo_root.name + "/"]
    for path in files:
        rel = path.relative_to(repo_root)
        depth = max(len(rel.parts) - 1, 0)
        indent = "    " * depth
        lines.append(f"{indent}+-- {rel.parts[-1]}")
    return "\n".join(lines)


def latex_preamble(title: str) -> str:
    return rf"""\documentclass[11pt,a4paper]{{article}}
\usepackage[margin=1in]{{geometry}}
\usepackage[T1]{{fontenc}}
\usepackage[utf8]{{inputenc}}
\usepackage{{hyperref}}
\usepackage{{listings}}
\usepackage{{upquote}}
\usepackage{{textcomp}}

\hypersetup{{
  colorlinks=true,
  linkcolor=blue,
  urlcolor=blue
}}

\lstset{{
  basicstyle=\ttfamily\small,
  breaklines=true,
  breakatwhitespace=false,
  columns=fullflexible,
  keepspaces=true,
  showstringspaces=false,
  frame=single,
  tabsize=2
}}

\title{{{latex_escape(title)}}}
\author{{Generated by repo\_to\_latex\_fixed.py}}
\date{{\today}}

\begin{{document}}
\maketitle
\tableofcontents
\newpage
"""


def latex_end() -> str:
    return "\\end{document}\n"


def section_summary(repo_root: Path, files: List[Path]) -> str:
    total_size = 0
    for p in files:
        try:
            total_size += p.stat().st_size
        except OSError:
            pass
    return (
        "\\section{Repository Summary}\n"
        "\\begin{itemize}\n"
        f"\\item Repository name: \\texttt{{{latex_escape(repo_root.name)}}}\n"
        f"\\item Total files found: {len(files)}\n"
        f"\\item Total size found: {total_size} bytes\n"
        "\\end{itemize}\n\n"
    )


def section_tree(tree_text: str) -> str:
    return (
        "\\section{Repository Tree}\n"
        "\\begin{lstlisting}\n"
        f"{tree_text}\n"
        "\\end{lstlisting}\n\n"
    )


def make_file_section(repo_root: Path, path: Path) -> str:
    rel = path.relative_to(repo_root)
    rel_str = str(rel)
    rel_tex = latex_escape(rel_str)
    suffix = path.suffix.lower()

    try:
        size = path.stat().st_size
    except OSError:
        size = 0

    out = []
    out.append(f"\\section{{{rel_tex}}}")
    out.append("")
    out.append(f"\\textbf{{Path:}} \\texttt{{{rel_tex}}}\\\\")
    out.append(f"\\textbf{{Size:}} {size} bytes")
    out.append("")

    if size > MAX_FILE_SIZE:
        out.append("\\textit{Skipped content because file is too large.}")
        out.append("")
        return "\n".join(out) + "\n"

    if not is_probably_text(path):
        out.append("\\textit{Skipped content because file appears to be binary.}")
        out.append("")
        return "\n".join(out) + "\n"

    content = safe_read_text(path)
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    content = ascii_safe(content)

    if suffix in TEXT_ONLY_EXTENSIONS:
        out.append("\\subsection*{Content}")
        out.append("")
        out.append("\\begin{verbatim}")
        out.append(content)
        out.append("\\end{verbatim}")
        out.append("")
    else:
        lang = LISTINGS_LANGUAGE_MAP.get(suffix, "")
        if lang:
            out.append(f"\\begin{{lstlisting}}[language={lang}]")
        else:
            out.append("\\begin{lstlisting}")
        out.append(content)
        out.append("\\end{lstlisting}")
        out.append("")

    return "\n".join(out) + "\n"


def skipped_section(repo_root: Path, skipped: List[str]) -> str:
    if not skipped:
        return ""
    lines = []
    lines.append("\\appendix")
    lines.append("")
    lines.append("\\section{Skipped Files}")
    lines.append("")
    lines.append("\\begin{itemize}")
    for rel in skipped:
        lines.append(f"\\item \\texttt{{{latex_escape(rel)}}}")
    lines.append("\\end{itemize}")
    lines.append("")
    return "\n".join(lines) + "\n"


def generate_latex(repo_root: Path, title: str, include_skipped: bool) -> str:
    files = collect_files(repo_root)
    skipped: List[str] = []

    parts: List[str] = []
    parts.append(latex_preamble(title))
    parts.append(section_summary(repo_root, files))
    parts.append(section_tree(ascii_safe(build_ascii_tree(repo_root, files))))

    for path in files:
        try:
            size = path.stat().st_size
        except OSError:
            size = 0

        if size > MAX_FILE_SIZE or not is_probably_text(path):
            skipped.append(str(path.relative_to(repo_root)))

        parts.append(make_file_section(repo_root, path))

    if include_skipped:
        parts.append(skipped_section(repo_root, skipped))

    parts.append(latex_end())
    return "".join(parts)


def main() -> int:
    args = parse_args()

    repo_root = Path(args.repo).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not repo_root.exists():
        print(f"Error: repository path does not exist: {repo_root}", file=sys.stderr)
        return 1

    if not repo_root.is_dir():
        print(f"Error: repository path is not a directory: {repo_root}", file=sys.stderr)
        return 1

    title = args.title if args.title else f"Repository Report: {repo_root.name}"

    try:
        tex = generate_latex(repo_root, title, args.include_skipped)
        output_path.write_text(tex, encoding="utf-8")
    except Exception as exc:
        print(f"Error while generating LaTeX: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote: {output_path}")
    print(f"Compile with: pdflatex -interaction=nonstopmode -halt-on-error {output_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
