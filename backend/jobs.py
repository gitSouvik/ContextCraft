"""
SQLite-backed job store.

This used to be a dict behind a lock — fine for a demo, but jobs vanished on
every restart and it couldn't be shared across multiple worker processes.
The `JobStore` interface (create/update/get) was kept narrow from day one
specifically so it could be swapped without touching main.py or pipeline.py,
and this is that swap: a single-file SQLite database gives jobs real
persistence with zero infrastructure to stand up. It's still single-writer
(SQLite's own limitation) — the next swap past this, if this ever needs to
run behind multiple app servers, is Postgres, for exactly the same reason
this swap didn't touch any calling code.
"""
import os
import sqlite3
import time
import uuid
from contextlib import closing
from pathlib import Path
from threading import Lock
from typing import Optional

from .models import JobResult, JobStatus

DEFAULT_DB_PATH = os.environ.get("CONTEXTCRAFT_DB_PATH", "./data/contextcraft.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    updated_at REAL NOT NULL
);
"""


class SQLiteJobStore:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        # SQLite connections aren't safe to share across threads, and FastAPI
        # runs sync background tasks in a worker thread pool, so each method
        # opens its own short-lived connection rather than holding one open.
        self._lock = Lock()
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def create(self) -> str:
        job_id = str(uuid.uuid4())
        job = JobResult(job_id=job_id, status=JobStatus.PENDING)
        self._write(job)
        return job_id

    def update(self, job_id: str, **fields) -> None:
        with self._lock:
            job = self._read(job_id)
            if job is None:
                return
            updated = job.model_copy(update=fields)
            self._write(updated)

    def get(self, job_id: str) -> Optional[JobResult]:
        return self._read(job_id)

    def _read(self, job_id: str) -> Optional[JobResult]:
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute("SELECT data FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        return JobResult.model_validate_json(row[0])

    def _write(self, job: JobResult) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO jobs VALUES (?, ?, ?)",
                (job.job_id, job.model_dump_json(), time.time()),
            )
            conn.commit()


job_store = SQLiteJobStore()
