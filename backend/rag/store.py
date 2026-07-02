"""
Persists code chunks + their embedding vectors, keyed by commit SHA (the same
content-address used by the analysis cache — see backend/cache.py). Content-
addressing means a repeat analysis of the same commit reuses the same chunk
index instead of re-embedding.

Retrieval is a plain numpy cosine-similarity scan rather than an ANN library
like FAISS: the repo scanner caps a single analysis at 50 files, so a given
commit's chunk set is at most a few hundred vectors — a linear scan over
that is sub-millisecond and adding an ANN index would be complexity with no
payoff at this scale.
"""
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import List, Tuple

import numpy as np

from ..models import CodeChunk

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    cache_key TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    path TEXT NOT NULL,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    lineno INTEGER NOT NULL,
    end_lineno INTEGER NOT NULL,
    text TEXT NOT NULL,
    snippet TEXT NOT NULL,
    embedding TEXT NOT NULL,
    PRIMARY KEY (cache_key, chunk_id)
);
"""


class ChunkStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def exists(self, cache_key: str) -> bool:
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute(
                "SELECT 1 FROM chunks WHERE cache_key = ? LIMIT 1", (cache_key,)
            ).fetchone()
        return row is not None

    def save(self, cache_key: str, chunks: List[CodeChunk], vectors: List[List[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must be the same length")
        rows = [
            (cache_key, c.chunk_id, c.path, c.kind, c.name, c.lineno, c.end_lineno,
             c.text, c.snippet, json.dumps(v))
            for c, v in zip(chunks, vectors, strict=True)
        ]
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?)", rows
            )
            conn.commit()

    def load(self, cache_key: str) -> List[Tuple[CodeChunk, List[float]]]:
        with closing(sqlite3.connect(self.db_path)) as conn:
            rows = conn.execute(
                "SELECT chunk_id, path, kind, name, lineno, end_lineno, text, snippet, embedding "
                "FROM chunks WHERE cache_key = ?",
                (cache_key,),
            ).fetchall()
        result = []
        for chunk_id, path, kind, name, lineno, end_lineno, text, snippet, embedding in rows:
            chunk = CodeChunk(
                chunk_id=chunk_id, path=path, kind=kind, name=name,
                lineno=lineno, end_lineno=end_lineno, text=text, snippet=snippet,
            )
            result.append((chunk, json.loads(embedding)))
        return result


def top_k(query_vector: List[float], candidates: List[Tuple[CodeChunk, List[float]]],
          k: int = 6) -> List[Tuple[float, CodeChunk]]:
    """Ranks candidates by cosine similarity to query_vector, highest first."""
    if not candidates:
        return []
    q = np.asarray(query_vector, dtype=np.float32)
    q_norm = float(np.linalg.norm(q)) or 1.0

    matrix = np.asarray([vec for _, vec in candidates], dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1)
    norms[norms == 0] = 1.0
    sims = (matrix @ q) / (norms * q_norm)

    ranked_indices = np.argsort(-sims)[:k]
    return [(float(sims[i]), candidates[i][0]) for i in ranked_indices]
