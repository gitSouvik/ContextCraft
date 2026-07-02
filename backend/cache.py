"""
Content-addressed cache for full pipeline results, keyed by the repo's commit
SHA. A commit SHA is immutable, so cache entries never go stale and never
need an invalidation strategy — the key itself guarantees correctness.

A cache hit lets the pipeline skip AST analysis, chunk embedding, and the
Gemini guide call entirely: the three most expensive and most rate-limited
steps. Combined with `repo_cloner.resolve_remote_head_sha`, a hit can be
detected via a cheap `git ls-remote` before a clone even happens.
"""
import json
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .models import RepoAnalysis

_SCHEMA = """
CREATE TABLE IF NOT EXISTS analysis_cache (
    commit_sha TEXT PRIMARY KEY,
    repo_url TEXT NOT NULL,
    analysis_json TEXT NOT NULL,
    markdown_guide TEXT NOT NULL,
    dependency_diagram TEXT NOT NULL,
    stats_json TEXT NOT NULL,
    created_at REAL NOT NULL
);
"""


@dataclass
class CachedAnalysis:
    analysis: RepoAnalysis
    guide: str
    diagram: str
    stats: dict


class AnalysisCache:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def exists(self, commit_sha: str) -> bool:
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute(
                "SELECT 1 FROM analysis_cache WHERE commit_sha = ?", (commit_sha,)
            ).fetchone()
        return row is not None

    def load(self, commit_sha: str) -> Optional[CachedAnalysis]:
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute(
                "SELECT analysis_json, markdown_guide, dependency_diagram, stats_json "
                "FROM analysis_cache WHERE commit_sha = ?",
                (commit_sha,),
            ).fetchone()
        if row is None:
            return None
        analysis_json, guide, diagram, stats_json = row
        return CachedAnalysis(
            analysis=RepoAnalysis.model_validate_json(analysis_json),
            guide=guide,
            diagram=diagram,
            stats=json.loads(stats_json),
        )

    def save(self, commit_sha: str, repo_url: str, analysis: RepoAnalysis,
              guide: str, diagram: str, stats: dict) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO analysis_cache VALUES (?,?,?,?,?,?,?)",
                (commit_sha, repo_url, analysis.model_dump_json(), guide, diagram,
                 json.dumps(stats), time.time()),
            )
            conn.commit()
