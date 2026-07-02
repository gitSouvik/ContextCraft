from pathlib import Path
from typing import Dict, Optional

from .base import LanguageAnalyzer
from .python_analyzer import PythonAnalyzer
from .specs.c_cpp import C_SPEC, CPP_SPEC
from .specs.go import GO_SPEC
from .specs.java import JAVA_SPEC
from .specs.javascript import JAVASCRIPT_SPEC
from .specs.ruby import RUBY_SPEC
from .specs.rust import RUST_SPEC
from .specs.typescript import TYPESCRIPT_SPEC
from .treesitter_analyzer import TreeSitterAnalyzer

EXTENSION_MAP: Dict[str, LanguageAnalyzer] = {
    # Python — uses the existing ast_visitor path unchanged
    ".py": PythonAnalyzer(),
    # JavaScript / TypeScript
    ".js": TreeSitterAnalyzer(JAVASCRIPT_SPEC),
    ".jsx": TreeSitterAnalyzer(JAVASCRIPT_SPEC),
    ".mjs": TreeSitterAnalyzer(JAVASCRIPT_SPEC),
    ".cjs": TreeSitterAnalyzer(JAVASCRIPT_SPEC),
    ".ts": TreeSitterAnalyzer(TYPESCRIPT_SPEC),
    ".tsx": TreeSitterAnalyzer(TYPESCRIPT_SPEC),
    # Go
    ".go": TreeSitterAnalyzer(GO_SPEC),
    # Java
    ".java": TreeSitterAnalyzer(JAVA_SPEC),
    # Rust
    ".rs": TreeSitterAnalyzer(RUST_SPEC),
    # C / C++
    ".c": TreeSitterAnalyzer(C_SPEC),
    ".h": TreeSitterAnalyzer(C_SPEC),
    ".cpp": TreeSitterAnalyzer(CPP_SPEC),
    ".cc": TreeSitterAnalyzer(CPP_SPEC),
    ".cxx": TreeSitterAnalyzer(CPP_SPEC),
    ".hpp": TreeSitterAnalyzer(CPP_SPEC),
    # Ruby
    ".rb": TreeSitterAnalyzer(RUBY_SPEC),
}


def analyzer_for(path: str) -> Optional[LanguageAnalyzer]:
    """Return the LanguageAnalyzer for this file path, or None if unsupported."""
    return EXTENSION_MAP.get(Path(path).suffix.lower())
