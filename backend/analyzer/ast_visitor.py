"""
Deterministic static analysis of a single Python source file using the stdlib
`ast` module. No source code ever leaves this process as raw text beyond what's
needed to build the typed structures below — the LLM only ever sees the
condensed JSON produced from these objects (see llm/gemini_client.py).

Design notes:
- We deliberately walk `tree.body` directly for module-level classes/functions
  instead of a single recursive NodeVisitor over the whole tree. A plain
  NodeVisitor.generic_visit() would also fire on nested/inner functions and
  methods, making it hard to tell "top-level" from "nested" apart. Iterating
  `tree.body` gives us that distinction for free.
- Cyclomatic complexity and call extraction *do* want the full subtree of a
  given function, so those use `ast.walk()` scoped to that function's node.
"""
import ast
from typing import List, Optional, Tuple

from ..models import ClassInfo, FileAnalysis, FunctionInfo, ImportInfo

# Decorator names that strongly suggest "a request/command enters the system here"
ENTRY_POINT_DECORATOR_HINTS = {
    "route", "get", "post", "put", "delete", "patch", "websocket",  # Flask / FastAPI
    "command", "group",  # click
    "task",  # celery
}


def _name_of(node: Optional[ast.AST]) -> Optional[str]:
    """Best-effort extraction of a readable name from a Name/Attribute/Call node."""
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _name_of(node.func)
    return None


def _decorator_names(decorator_list: list) -> List[str]:
    return [n for n in (_name_of(d) for d in decorator_list) if n]


def compute_cyclomatic_complexity(node: ast.AST) -> int:
    """
    McCabe-style complexity: start at 1, add 1 for each independent branch point
    in the function's subtree (if/for/while/except/with, boolean-op branches,
    and comprehensions). This is intentionally simple, not a full McCabe
    implementation with basic-block graphs — good enough to flag "this function
    is doing a lot" without needing a control-flow graph library.
    """
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While,
                               ast.Try, ast.ExceptHandler, ast.With, ast.AsyncWith)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += max(len(child.values) - 1, 0)
        elif isinstance(child, ast.comprehension):
            complexity += 1
    return complexity


def extract_calls(node: ast.AST, limit: int = 25) -> List[str]:
    """Names of functions/methods called anywhere within this node's subtree."""
    seen: List[str] = []
    seen_set = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            name = _name_of(child.func)
            if name and name not in seen_set:
                seen_set.add(name)
                seen.append(name)
                if len(seen) >= limit:
                    break
    return seen


def _build_function_info(node) -> FunctionInfo:
    args = [a.arg for a in node.args.args]
    return FunctionInfo(
        name=node.name,
        args=args,
        lineno=node.lineno,
        end_lineno=getattr(node, "end_lineno", None) or node.lineno,
        docstring=ast.get_docstring(node),
        decorators=_decorator_names(node.decorator_list),
        complexity=compute_cyclomatic_complexity(node),
        calls=extract_calls(node),
    )


def _build_class_info(node: ast.ClassDef) -> ClassInfo:
    methods = [
        _build_function_info(item)
        for item in node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    return ClassInfo(
        name=node.name,
        bases=[n for n in (_name_of(b) for b in node.bases) if n],
        lineno=node.lineno,
        end_lineno=getattr(node, "end_lineno", None) or node.lineno,
        docstring=ast.get_docstring(node),
        methods=methods,
        decorators=_decorator_names(node.decorator_list),
    )


def _is_main_guard(node: ast.If) -> bool:
    """Detects `if __name__ == "__main__":`."""
    test = node.test
    if isinstance(test, ast.Compare) and isinstance(test.left, ast.Name) and test.left.id == "__name__":
        for comparator in test.comparators:
            if isinstance(comparator, ast.Constant) and comparator.value == "__main__":
                return True
    return False


def _detect_entry_point(tree: ast.Module, functions: List[FunctionInfo],
                         classes: List[ClassInfo]) -> Tuple[bool, List[str]]:
    reasons: List[str] = []

    for node in tree.body:
        if isinstance(node, ast.If) and _is_main_guard(node):
            reasons.append('Contains an `if __name__ == "__main__":` block')

    all_decorators = set()
    for fn in functions:
        all_decorators.update(fn.decorators)
    for cls in classes:
        all_decorators.update(cls.decorators)
        for m in cls.methods:
            all_decorators.update(m.decorators)

    hits = sorted(all_decorators & ENTRY_POINT_DECORATOR_HINTS)
    if hits:
        reasons.append(f"Defines route/CLI/task handlers (`@{'`, `@'.join(hits)}`)")

    return (len(reasons) > 0, reasons)


def analyze_source(source: str, relative_path: str) -> FileAnalysis:
    """Parse one Python file's source and return its structural analysis."""
    loc = len(source.splitlines())
    source_bytes = len(source.encode("utf-8"))

    try:
        tree = ast.parse(source, filename=relative_path)
    except SyntaxError as e:
        return FileAnalysis(
            path=relative_path, loc=loc, source_bytes=source_bytes,
            parse_error=f"SyntaxError: {e}",
        )

    imports: List[ImportInfo] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(ImportInfo(module=alias.name, is_from=False, lineno=node.lineno))
        elif isinstance(node, ast.ImportFrom):
            imports.append(ImportInfo(
                module=node.module or "",
                names=[a.name for a in node.names],
                is_from=True,
                lineno=node.lineno,
            ))

    top_level_functions = [
        _build_function_info(node) for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    top_level_classes = [
        _build_class_info(node) for node in tree.body
        if isinstance(node, ast.ClassDef)
    ]

    is_entry, reasons = _detect_entry_point(tree, top_level_functions, top_level_classes)

    return FileAnalysis(
        path=relative_path,
        imports=imports,
        classes=top_level_classes,
        functions=top_level_functions,
        is_entry_point=is_entry,
        entry_point_reasons=reasons,
        loc=loc,
        source_bytes=source_bytes,
    )
