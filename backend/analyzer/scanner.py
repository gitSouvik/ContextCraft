"""
Walks a cloned repository and selects which .py files get analyzed, enforcing
the MVP's stated constraints: boilerplate directories are excluded, individual
files over a size threshold are skipped (usually generated code), and the
total file count is capped to keep analysis time bounded.
"""
import os
from pathlib import Path
from typing import List, Tuple

from .languages import EXTENSION_MAP

EXCLUDED_DIRS = {
    "venv", ".venv", "env", ".env", "node_modules", ".git", "tests", "test",
    "__pycache__", ".mypy_cache", ".pytest_cache", "build", "dist",
    "site-packages", ".tox", "docs", "examples", "migrations",
}

MAX_FILE_SIZE_BYTES = 500_000  # skip individual files above this (usually generated/vendored code)

CONTEXT_FILENAMES = {
    "README.md", "package.json", "pyproject.toml", "requirements.txt",
    "Dockerfile", "docker-compose.yml", "Makefile", ".env.example"
}


def _is_context_file(rel_path: str) -> bool:
    name = rel_path.split("/")[-1]
    if name in CONTEXT_FILENAMES:
        return True
    if rel_path.startswith(".github/workflows/") and name.endswith(".yml"):
        return True
    return False


def find_source_files(repo_root: str, max_files: int = 50) -> Tuple[List[str], List[str]]:
    """
    Returns (included_relative_paths, skipped_relative_paths). Skipped files are
    the ones that existed but were excluded due to the count cap or size limit —
    directory-excluded files aren't reported since they're not really "part of"
    the repo from an onboarding perspective.
    """
    included: List[str] = []
    skipped: List[str] = []
    root_path = Path(repo_root)

    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith(".")]

        for filename in sorted(filenames):
            full_path = Path(dirpath) / filename
            rel_path = str(full_path.relative_to(root_path)).replace("\\", "/")

            if not (full_path.suffix.lower() in EXTENSION_MAP or _is_context_file(rel_path)):
                continue

            if len(included) >= max_files:
                skipped.append(rel_path)
                continue

            try:
                if full_path.stat().st_size > MAX_FILE_SIZE_BYTES:
                    skipped.append(rel_path)
                    continue
            except OSError:
                skipped.append(rel_path)
                continue

            included.append(rel_path)

    return included, skipped
