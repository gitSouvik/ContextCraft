"""
Generic tree-sitter–backed analyzer, parameterized by a LanguageSpec.

tree-sitter 0.26 API notes:
  - tree_sitter.Parser(language) - constructor takes language
  - parser.parse(bytes) -> Tree
  - tree.root_node -> Node (property, not method)
  - node.start_point / node.end_point -> Point(row, column)  (0-based)
  - node.text -> bytes
  - node.type -> str
  - node.children -> List[Node]
  - tree_sitter.Query(language, query_str) -> Query
  - tree_sitter.QueryCursor(query) -> QueryCursor
  - cursor.matches(node) -> List[Tuple[int, Dict[str, List[Node]]]]
"""
from dataclasses import dataclass
from typing import Dict, Optional, Set

import tree_sitter
from tree_sitter_language_pack import get_language

from ...models import ClassInfo, FileAnalysis, FunctionInfo, ImportInfo
from .base import LanguageAnalyzer


@dataclass
class LanguageSpec:
    language_id: str
    ts_language_name: str
    function_query: str
    class_query: str
    import_query: str
    branch_node_types: Set[str]
    entry_point_query: Optional[str] = None


def _text(node) -> str:
    """Decode node text bytes to str."""
    return node.text.decode("utf8") if node.text else ""


def _lineno(node) -> int:
    """1-based start line."""
    return node.start_point.row + 1


def _end_lineno(node) -> int:
    """1-based end line."""
    return node.end_point.row + 1


class TreeSitterAnalyzer(LanguageAnalyzer):
    language_id: str

    def __init__(self, spec: LanguageSpec):
        self.spec = spec
        self.language_id = spec.language_id
        self.language = get_language(spec.ts_language_name)
        self.parser = tree_sitter.Parser(self.language)

        self.function_q: Optional[tree_sitter.Query] = (
            tree_sitter.Query(self.language, spec.function_query)
            if spec.function_query.strip() else None
        )
        self.class_q: Optional[tree_sitter.Query] = (
            tree_sitter.Query(self.language, spec.class_query)
            if spec.class_query.strip() else None
        )
        self.import_q: Optional[tree_sitter.Query] = (
            tree_sitter.Query(self.language, spec.import_query)
            if spec.import_query.strip() else None
        )
        self.entry_q: Optional[tree_sitter.Query] = (
            tree_sitter.Query(self.language, spec.entry_point_query)
            if spec.entry_point_query and spec.entry_point_query.strip() else None
        )

    def analyze(self, source: str, rel_path: str) -> FileAnalysis:
        source_bytes = source.encode("utf8")
        tree = self.parser.parse(source_bytes)
        root = tree.root_node

        analysis = FileAnalysis(
            path=rel_path,
            language=self.spec.language_id,
            loc=len(source.splitlines()),
            source_bytes=len(source_bytes),
        )

        # --- Entry point detection ---
        if self.entry_q:
            cursor = tree_sitter.QueryCursor(self.entry_q)
            matches = cursor.matches(root)
            if matches:
                analysis.is_entry_point = True
                analysis.entry_point_reasons.append("Matches known entry point pattern")

        # Also detect entry point by filename heuristic
        filename = rel_path.split("/")[-1]
        if filename in {"main.py", "index.js", "server.js", "app.js", "main.go",
                        "main.rs", "Main.java"}:
            analysis.is_entry_point = True
            if "Common entry-point filename" not in analysis.entry_point_reasons:
                analysis.entry_point_reasons.append("Common entry-point filename")

        # --- Imports ---
        if self.import_q:
            cursor = tree_sitter.QueryCursor(self.import_q)
            seen_modules: Set[str] = set()
            for _, match_dict in cursor.matches(root):
                source_nodes = match_dict.get("source", [])
                for node in source_nodes:
                    raw = _text(node).strip("'\"` ")
                    if raw and raw not in seen_modules:
                        seen_modules.add(raw)
                        analysis.imports.append(ImportInfo(
                            module=raw,
                            lineno=_lineno(node),
                        ))

        # --- Classes ---
        classes_by_range: Dict[str, ClassInfo] = {}
        if self.class_q:
            cursor = tree_sitter.QueryCursor(self.class_q)
            for _, match_dict in cursor.matches(root):
                cls_nodes = match_dict.get("class", [])
                name_nodes = match_dict.get("name", [])
                for i, cls_node in enumerate(cls_nodes):
                    name = _text(name_nodes[i]) if i < len(name_nodes) else "Anonymous"
                    c_info = ClassInfo(
                        name=name,
                        lineno=_lineno(cls_node),
                        end_lineno=_end_lineno(cls_node),
                        docstring=None,
                    )
                    analysis.classes.append(c_info)
                    key = f"{c_info.lineno}:{c_info.end_lineno}"
                    classes_by_range[key] = c_info

        # --- Functions / Methods ---
        if self.function_q:
            cursor = tree_sitter.QueryCursor(self.function_q)
            for _, match_dict in cursor.matches(root):
                func_nodes = match_dict.get("func", [])
                name_nodes = match_dict.get("name", [])
                for i, func_node in enumerate(func_nodes):
                    name = _text(name_nodes[i]) if i < len(name_nodes) else "anonymous"
                    complexity = self._count_branches(func_node) + 1
                    lineno = _lineno(func_node)
                    end_lineno = _end_lineno(func_node)

                    f_info = FunctionInfo(
                        name=name,
                        lineno=lineno,
                        end_lineno=end_lineno,
                        docstring=None,
                        complexity=complexity,
                    )

                    # Assign to parent class if this function's range is inside one
                    parent_class: Optional[ClassInfo] = None
                    for c in analysis.classes:
                        if (c.lineno <= lineno and
                                (c.end_lineno is None or c.end_lineno >= end_lineno)):
                            # Prefer the innermost (narrowest) class
                            if (parent_class is None or
                                    (c.end_lineno or 0) - c.lineno <
                                    (parent_class.end_lineno or 0) - parent_class.lineno):
                                parent_class = c

                    if parent_class is not None:
                        parent_class.methods.append(f_info)
                    else:
                        analysis.functions.append(f_info)

        return analysis

    def _count_branches(self, node) -> int:
        """Recursively count branch nodes matching spec.branch_node_types."""
        count = 1 if node.type in self.spec.branch_node_types else 0
        for child in node.children:
            count += self._count_branches(child)
        return count
