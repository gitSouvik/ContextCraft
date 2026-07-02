"""
Ties scanner.py + ast_visitor.py together into a single RepoAnalysis, and
builds a deterministic Mermaid dependency diagram directly from the import
graph — no LLM involved. Keeping this deterministic means the diagram can
never hallucinate a dependency that isn't actually in the code.
"""
from pathlib import Path
from typing import List, Tuple

from ..models import CodeChunk, FileAnalysis, RepoAnalysis
from .chunker import build_file_chunks
from .languages import analyzer_for
from .scanner import _is_context_file, find_source_files


def _read_and_analyze_files(repo_root: str, included_paths: List[str],
                             build_chunks: bool) -> Tuple[List[FileAnalysis], List[CodeChunk], int]:
    """
    Shared read+parse loop: reads each included file's source exactly once,
    runs it through the AST visitor, and optionally builds RAG chunks from it
    while the source is still in hand. Keeping this in one place means the
    chunk-building pass costs nothing extra beyond what analyze_repo already
    did — no second read of the clone, no source kept around any longer than
    before.
    """
    file_analyses: List[FileAnalysis] = []
    chunks: List[CodeChunk] = []
    total_bytes = 0
    for rel_path in included_paths:
        full_path = Path(repo_root) / rel_path
        try:
            source = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            file_analyses.append(FileAnalysis(path=rel_path, parse_error=f"Could not read file: {e}"))
            continue

        analyzer = analyzer_for(rel_path)
        if analyzer:
            analysis = analyzer.analyze(source, rel_path)
            total_bytes += analysis.source_bytes
            file_analyses.append(analysis)
            if build_chunks:
                chunks.extend(build_file_chunks(source, analysis))
        elif _is_context_file(rel_path):
            analysis = FileAnalysis(
                path=rel_path,
                language="markdown" if rel_path.endswith(".md") else "text",
                loc=len(source.splitlines()),
                source_bytes=len(source.encode("utf-8"))
            )
            total_bytes += analysis.source_bytes
            file_analyses.append(analysis)
            if build_chunks:
                snippet = source[:10000]
                if len(source) > 10000:
                    snippet += "\n# ...(truncated)"
                text = f"Context file: {rel_path}\n\n{snippet}"
                chunks.append(CodeChunk(
                    chunk_id=rel_path.replace("/", "_").replace(".", "_") + "_context",
                    path=rel_path,
                    language=analysis.language,
                    kind="context_file",
                    name=rel_path.split("/")[-1],
                    lineno=1,
                    end_lineno=max(analysis.loc, 1),
                    text=text,
                    snippet=snippet
                ))
        else:
            continue
    return file_analyses, chunks, total_bytes


def analyze_repo(repo_root: str, repo_url: str, commit_sha: str, max_files: int = 50) -> RepoAnalysis:
    included_paths, skipped_paths = find_source_files(repo_root, max_files=max_files)
    file_analyses, _, total_bytes = _read_and_analyze_files(repo_root, included_paths, build_chunks=False)

    repo_name = repo_url.rstrip("/").split("/")[-1]

    return RepoAnalysis(
        repo_url=repo_url,
        repo_name=repo_name,
        commit_sha=commit_sha,
        files=file_analyses,
        total_files_scanned=len(included_paths) + len(skipped_paths),
        total_files_included=len(included_paths),
        skipped_files=skipped_paths,
        total_source_bytes=total_bytes,
    )


def analyze_repo_with_chunks(repo_root: str, repo_url: str, commit_sha: str,
                              max_files: int = 50) -> Tuple[RepoAnalysis, List[CodeChunk]]:
    """Same as analyze_repo, but also returns RAG chunks for the chat feature."""
    included_paths, skipped_paths = find_source_files(repo_root, max_files=max_files)
    file_analyses, chunks, total_bytes = _read_and_analyze_files(repo_root, included_paths, build_chunks=True)

    repo_name = repo_url.rstrip("/").split("/")[-1]

    analysis = RepoAnalysis(
        repo_url=repo_url,
        repo_name=repo_name,
        commit_sha=commit_sha,
        files=file_analyses,
        total_files_scanned=len(included_paths) + len(skipped_paths),
        total_files_included=len(included_paths),
        skipped_files=skipped_paths,
        total_source_bytes=total_bytes,
    )
    return analysis, chunks


def _sanitize(name: str) -> str:
    return name.replace(".", "_").replace("-", "_").replace("/", "_")


def build_dependency_mermaid(analysis: RepoAnalysis) -> str:
    """
    Deterministic Mermaid `graph TD` of intra-repo module dependencies.
    Only edges between files that both appear to be part of this repo's
    scanned module set are drawn — stdlib/third-party imports are omitted
    to keep the diagram focused on "how does *this* codebase wire together."

    This is a heuristic, not a full import resolver: it matches an imported
    module's dotted name (or its final segment) against known module names
    derived from scanned file paths. Relative imports and dynamic imports
    won't be perfectly resolved, but it's good enough to anchor a mental
    model of the codebase's internal structure.
    """
    module_names = {f.path[:-3].replace("/", ".") for f in analysis.files if not f.parse_error}

    lines = ["graph TD"]
    seen_edges = set()

    for f in analysis.files:
        if f.parse_error or f.language not in ("python", "javascript", "typescript"):
            continue
        src_mod = f.path[:-3].replace("/", ".")
        for imp in f.imports:
            target = imp.module
            if not target:
                continue

            # Candidate dotted names this import could refer to. Covers both
            # `import pkg.utils` / `from pkg.utils import helper` (target itself)
            # and `from pkg import utils` (target + each imported name).
            probe_names = [target]
            if imp.is_from:
                probe_names.extend(f"{target}.{n}" for n in imp.names)

            candidates = set()
            for probe in probe_names:
                last_segment = probe.split(".")[-1]
                for m in module_names:
                    if m == probe or m.endswith("." + last_segment) or m == last_segment:
                        candidates.add(m)

            for match in candidates:
                if match == src_mod:
                    continue
                edge = (src_mod, match)
                if edge in seen_edges:
                    continue
                seen_edges.add(edge)
                lines.append(f'    {_sanitize(src_mod)}["{f.path}"] --> {_sanitize(match)}')

    if len(lines) == 1:
        lines.append('    empty["No intra-repo dependency edges detected"]')

    return "\n".join(lines)
