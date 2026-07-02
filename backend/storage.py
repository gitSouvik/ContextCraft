"""
Shared persistent-storage singletons. All three stores — jobs, the content-
addressed analysis cache, and the RAG chunk index — live in the same SQLite
file (different tables), so there's exactly one file to mount as a Docker
volume for full persistence across restarts.
"""
import os

from .cache import AnalysisCache
from .rag.store import ChunkStore

DB_PATH = os.environ.get("CONTEXTCRAFT_DB_PATH", "./data/contextcraft.db")

analysis_cache = AnalysisCache(DB_PATH)
chunk_store = ChunkStore(DB_PATH)
