"""
Handles cloning a public GitHub repo into an ephemeral temp directory.

Security posture (this is the part that matters most for a tool that clones
arbitrary user-supplied URLs):
  - URL is validated against an allowlist pattern for github.com before any
    network call is made, to avoid this becoming an open SSRF proxy.
  - Clones are shallow (--depth 1) and single-branch, minimizing data pulled.
  - A post-clone size check aborts and cleans up before analysis if the repo
    is larger than expected (protects disk + keeps analysis time bounded).
  - Cleanup is guaranteed via try/finally regardless of what happens inside
    the `with cloned_repo(...)` block — no cloned source ever outlives the
    request that triggered it.
"""
import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import git

GITHUB_URL_PATTERN = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+/?$")
MAX_CLONE_SIZE_BYTES = 200 * 1024 * 1024  # 200MB safety cap


class InvalidRepoUrlError(ValueError):
    pass


class RepoTooLargeError(ValueError):
    pass


def validate_github_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not GITHUB_URL_PATTERN.match(url):
        raise InvalidRepoUrlError(
            "Please provide a public GitHub repo URL in the form "
            "https://github.com/owner/repo"
        )
    return url


def resolve_remote_head_sha(repo_url: str) -> Optional[str]:
    """
    A `git ls-remote` lookup of HEAD's commit SHA, without cloning anything.
    Used to check the content-addressed analysis cache (keyed by commit SHA)
    *before* spending time on a shallow clone at all — on a cache hit, the
    clone is skipped entirely. Returns None on any failure so callers can
    fall back to the normal clone path, which will surface a clearer error.
    """
    try:
        output = git.cmd.Git().ls_remote(repo_url, "HEAD", env={"GIT_TERMINAL_PROMPT": "0"})
        if not output:
            return None
        return output.split()[0]
    except Exception:
        return None


def _dir_size_bytes(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


@contextmanager
def cloned_repo(repo_url: str):
    """
    Validates the URL, shallow-clones it into a temp dir, yields
    (path, commit_sha), and guarantees the temp dir is removed afterward —
    whether analysis succeeds, fails, or raises.
    """
    url = validate_github_url(repo_url)
    tmp_dir = tempfile.mkdtemp(prefix="contextcraft_")
    try:
        try:
            repo = git.Repo.clone_from(url, tmp_dir, depth=1, single_branch=True, env={"GIT_TERMINAL_PROMPT": "0"})
        except git.exc.GitCommandError as e:
            raise ValueError(
                f"Could not clone '{url}'. Check that it's a public repository. ({e})"
            ) from e

        size = _dir_size_bytes(Path(tmp_dir))
        if size > MAX_CLONE_SIZE_BYTES:
            raise RepoTooLargeError(
                f"Repository is too large to analyze "
                f"({size / 1_000_000:.0f}MB, limit is {MAX_CLONE_SIZE_BYTES / 1_000_000:.0f}MB)."
            )

        commit_sha = repo.head.commit.hexsha
        yield tmp_dir, commit_sha
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
