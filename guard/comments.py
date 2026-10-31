"""Extract comment blocks from Python and C-like source.

A block is a run of consecutive line comments, one block comment, or one
docstring. Each block keeps the source lines it covers so the guard can
remove it without touching code.
"""
from __future__ import annotations

import ast
import io
import tokenize
from dataclasses import dataclass


@dataclass
class Comment:
    text: str
    start_line: int  # 1-based, inclusive
    end_line: int
    kind: str  # "line", "block", "docstring"
    # For a trailing comment (code before it on the same line) we must cut
    # from this column instead of dropping the whole line.
    start_col: int = 0
    trailing: bool = False


def detect_language(code: str) -> str:
    """Rough guess. Callers should pass the language when they know it."""
    c_signals = code.count(";") + code.count("{") + code.count("//") + code.count("/*")
    py_signals = code.count("def ") + code.count("import ") + code.count("#") + code.count(":\n")
    return "c" if c_signals > py_signals else "python"


def _merge_line_comments(items: list[Comment]) -> list[Comment]:
    out: list[Comment] = []
    for c in items:
        prev = out[-1] if out else None
        if (prev and prev.kind == "line" and c.kind == "line" and not prev.trailing
                and not c.trailing and c.start_line == prev.end_line + 1):
            prev.text += "\n" + c.text
            prev.end_line = c.end_line
        else:
            out.append(c)
    return out


def extract_python(code: str) -> list[Comment]:
    items: list[Comment] = []
    lines = code.splitlines()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(code).readline):
            if tok.type == tokenize.COMMENT:
                row, col = tok.start
                before = lines[row - 1][:col] if row - 1 < len(lines) else ""
                items.append(Comment(tok.string.lstrip("#").strip(), row, row, "line",
                                     start_col=col, trailing=bool(before.strip())))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Fragments and diffs often do not tokenize; fall back to a line scan.
        return extract_python_lines(code)
    try:
        tree = ast.parse(code)
        nodes = [tree] + [n for n in ast.walk(tree)
                          if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        for n in nodes:
            body = getattr(n, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
                    and isinstance(body[0].value.value, str):
                e = body[0]
                items.append(Comment(e.value.value.strip(), e.lineno, e.end_lineno or e.lineno, "docstring"))
    except SyntaxError:
        pass
    items.sort(key=lambda c: (c.start_line, c.start_col))
    return _merge_line_comments(items)


def extract_python_lines(code: str) -> list[Comment]:
    items = []
    for i, line in enumerate(code.splitlines(), 1):
        s = line.lstrip()
        if s.startswith("#"):
            items.append(Comment(s.lstrip("#").strip(), i, i, "line"))
    return _merge_line_comments(items)


def extract_c(code: str) -> list[Comment]:
    """State machine over C, C++, Java, JS, Go source. Skips string and char literals."""
    items: list[Comment] = []
    i, n, line = 0, len(code), 1
    line_start = 0
    while i < n:
        ch = code[i]
        if ch == "\n":
            line += 1
            line_start = i + 1
            i += 1
        elif ch in "\"'":
            q = ch
            i += 1
            while i < n and code[i] != q:
                if code[i] == "\\":
                    i += 1
                elif code[i] == "\n":
                    line += 1
                    line_start = i + 1
                i += 1
            i += 1
        elif code.startswith("//", i):
            j = code.find("\n", i)
            j = n if j == -1 else j
            before = code[line_start:i]
            items.append(Comment(code[i + 2:j].strip(), line, line, "line",
                                 start_col=i - line_start, trailing=bool(before.strip())))
            i = j
        elif code.startswith("/*", i):
            j = code.find("*/", i + 2)
            j = n if j == -1 else j
            body = code[i + 2:j]
            start = line
            before = code[line_start:i]
            line += body.count("\n")
            text = "\n".join(l.strip().lstrip("*").strip() for l in body.splitlines()).strip()
            items.append(Comment(text, start, line, "block", start_col=i - line_start,
                                 trailing=bool(before.strip())))
            if "\n" in body:
                line_start = code.rfind("\n", i, j) + 1
            i = j + 2
        else:
            i += 1
    return _merge_line_comments(items)


def extract(code: str, language: str | None = None) -> list[Comment]:
    lang = (language or detect_language(code)).lower()
    if lang in ("python", "py"):
        return extract_python(code)
    return extract_c(code)


def remove(code: str, comments: list[Comment]) -> str:
    """Return code with the given comment blocks removed. Code lines are kept."""
    lines = code.splitlines()
    drop: set[int] = set()
    for c in comments:
        if c.trailing and c.start_line == c.end_line:
            idx = c.start_line - 1
            lines[idx] = lines[idx][:c.start_col].rstrip()
        else:
            drop.update(range(c.start_line, c.end_line + 1))
    return "\n".join(l for i, l in enumerate(lines, 1) if i not in drop)
