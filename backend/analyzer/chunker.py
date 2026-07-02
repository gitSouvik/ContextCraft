"""
Builds retrieval chunks for the RAG chat feature.

Each chunk pairs a short structural summary (from the deterministic AST
analysis) with the *exact* source snippet for that node, sliced by
lineno/end_lineno while the clone is still on disk. This runs inside the
same window `analyze_repo` already has file contents in memory — before the
temp clone is deleted (see repo_cloner.cloned_repo) — so it doesn't require
keeping raw source around any longer than the existing pipeline already does.

This narrows the project's original privacy claim rather than breaking it:
"the LLM never sees raw source" becomes "the LLM only ever sees the specific
few snippets retrieved for a given question — never the whole codebase, and
never anything beyond what that question required." The onboarding-guide
path (llm/gemini_client.py) is unchanged and still never sends source at all.
"""
import re
from typing import List

from ..models import ClassInfo, CodeChunk, FileAnalysis, FunctionInfo

MAX_SNIPPET_LINES = 60  # keeps embedding + prompt cost bounded for very long functions
MAX_SNIPPET_CHARS = 3000

_NON_ALNUM = re.compile(r"[^a-zA-Z0-9_]+")


def _slice_source(source_lines: List[str], lineno: int, end_lineno: int) -> str:
    end_lineno = max(end_lineno, lineno)
    snippet_lines = source_lines[lineno - 1: min(end_lineno, lineno - 1 + MAX_SNIPPET_LINES)]
    snippet = "\n".join(snippet_lines)
    if len(snippet) > MAX_SNIPPET_CHARS:
        snippet = snippet[:MAX_SNIPPET_CHARS] + "\n# ...(truncated)"
    return snippet


def _chunk_id(path: str, kind: str, name: str, lineno: int) -> str:
    slug = _NON_ALNUM.sub("_", f"{path}_{kind}_{name}_{lineno}")
    return slug.strip("_")


def _function_chunk(source_lines: List[str], path: str, language: str, fn: FunctionInfo,
                     kind: str = "function", owner: str = "") -> CodeChunk:
    qualified_name = f"{owner}.{fn.name}" if owner else fn.name
    snippet = _slice_source(source_lines, fn.lineno, fn.end_lineno or fn.lineno)
    calls = ", ".join(fn.calls[:8]) or "none detected"
    text = (
        f"File: {path}\n{kind.capitalize()}: {qualified_name}({', '.join(fn.args)})\n"
        f"Calls: {calls}\nCyclomatic complexity: {fn.complexity}\n"
        + (f"Docstring: {fn.docstring}\n" if fn.docstring else "")
        + f"\n{snippet}"
    )
    return CodeChunk(
        chunk_id=_chunk_id(path, kind, qualified_name, fn.lineno),
        path=path, kind=kind, name=qualified_name,
        language=language,
        lineno=fn.lineno, end_lineno=fn.end_lineno or fn.lineno,
        text=text, snippet=snippet,
    )


def _class_chunk(source_lines: List[str], path: str, language: str, cls: ClassInfo) -> CodeChunk:
    snippet = _slice_source(source_lines, cls.lineno, cls.end_lineno or cls.lineno)
    method_names = ", ".join(m.name for m in cls.methods) or "none"
    text = (
        f"File: {path}\nClass: {cls.name}(bases: {', '.join(cls.bases) or 'object'})\n"
        f"Methods: {method_names}\n"
        + (f"Docstring: {cls.docstring}\n" if cls.docstring else "")
        + f"\n{snippet}"
    )
    return CodeChunk(
        chunk_id=_chunk_id(path, "class", cls.name, cls.lineno),
        path=path, kind="class", name=cls.name,
        language=language,
        lineno=cls.lineno, end_lineno=cls.end_lineno or cls.lineno,
        text=text, snippet=snippet,
    )


def _file_chunk(source_lines: List[str], path: str, file_analysis: FileAnalysis) -> CodeChunk:
    imports = sorted({imp.module for imp in file_analysis.imports if imp.module})
    top_level = [f.name for f in file_analysis.functions] + [c.name for c in file_analysis.classes]
    snippet = _slice_source(source_lines, 1, max(file_analysis.loc, 1))
    text = (
        f"File: {path}\nImports: {', '.join(imports[:20]) or 'none'}\n"
        f"Top-level definitions: {', '.join(top_level) or 'none'}\n"
        f"Entry point: {file_analysis.is_entry_point} "
        f"({'; '.join(file_analysis.entry_point_reasons)})\n"
        f"\n{snippet}"
    )
    return CodeChunk(
        chunk_id=_chunk_id(path, "file", path, 1),
        path=path, kind="file", name=path,
        language=file_analysis.language,
        lineno=1, end_lineno=max(file_analysis.loc, 1),
        text=text, snippet=snippet,
    )


def build_file_chunks(source: str, file_analysis: FileAnalysis) -> List[CodeChunk]:
    """
    Builds one file-level summary chunk, one chunk per top-level class
    (header + docstring, not the full body — methods get their own chunks),
    and one chunk per function/method (module-level and per-class).
    """
    if file_analysis.parse_error:
        return []

    source_lines = source.splitlines()
    path = file_analysis.path
    lang = file_analysis.language
    chunks: List[CodeChunk] = [_file_chunk(source_lines, path, file_analysis)]

    for fn in file_analysis.functions:
        chunks.append(_function_chunk(source_lines, path, lang, fn))

    for cls in file_analysis.classes:
        chunks.append(_class_chunk(source_lines, path, lang, cls))
        for method in cls.methods:
            chunks.append(_function_chunk(source_lines, path, lang, method, kind="method", owner=cls.name))

    return chunks
