"""
Orchestrates the full pipeline for a single job:

  validate URL -> cheap ls-remote HEAD lookup -> cache check
    -> [cache hit: done immediately]
    -> [cache miss: shallow clone -> AST analyze -> build+embed RAG chunks
        -> build dependency diagram -> generate LLM guide -> cache it all]

Runs as a FastAPI background task (see main.py) so /analyze can return a
job_id immediately instead of holding the HTTP connection open for the full
clone+embed+LLM round trip.
"""
import logging

from .analyzer.repo_analyzer import analyze_repo_with_chunks, build_dependency_mermaid
from .analyzer.repo_cloner import (
    InvalidRepoUrlError,
    RepoTooLargeError,
    cloned_repo,
    resolve_remote_head_sha,
    validate_github_url,
)
from .jobs import job_store
from .llm.gemini_client import GeminiClientError, condensed_payload_json, generate_onboarding_guide
from .models import JobStatus
from .observability import cache_lookups_total, jobs_total, timed_stage
from .rag.embeddings import EmbeddingError, embed_texts
from .storage import analysis_cache, chunk_store

logger = logging.getLogger("contextcraft.pipeline")

MAX_FILES = 50


def _serve_from_cache(job_id: str, commit_sha: str) -> bool:
    cached = analysis_cache.load(commit_sha)
    if cached is None:
        return False
    cache_lookups_total.labels(result="hit").inc()
    job_store.update(
        job_id,
        status=JobStatus.DONE,
        repo_analysis=cached.analysis,
        markdown_guide=cached.guide,
        dependency_diagram=cached.diagram,
        stats={**cached.stats, "cache_hit": True},
        chat_available=chunk_store.exists(commit_sha),
    )
    jobs_total.labels(status="done_cached").inc()
    return True


def run_pipeline(job_id: str, repo_url: str) -> None:
    try:
        url = validate_github_url(repo_url)
        job_store.update(job_id, status=JobStatus.CLONING)

        # Cheap `git ls-remote` check: if we've already analyzed this exact
        # commit before, skip the clone entirely and serve from cache.
        with timed_stage("cache_lookup"):
            remote_sha = resolve_remote_head_sha(url)
        if remote_sha and _serve_from_cache(job_id, remote_sha):
            return
        cache_lookups_total.labels(result="miss").inc()

        with timed_stage("clone"):
            with cloned_repo(url) as (repo_path, commit_sha):
                # A cache entry might exist under the *actual* clone SHA even
                # if the ls-remote lookup above failed or raced with a push.
                if _serve_from_cache(job_id, commit_sha):
                    return

                job_store.update(job_id, status=JobStatus.ANALYZING)
                with timed_stage("analyze"):
                    analysis, chunks = analyze_repo_with_chunks(
                        repo_path, url, commit_sha, max_files=MAX_FILES
                    )
        # repo_path is deleted here (cloned_repo's finally block). Everything
        # downstream works only from the typed `analysis` object and the
        # already-extracted `chunks` — never the filesystem again.

        chat_available = False
        if chunks:
            job_store.update(job_id, status=JobStatus.EMBEDDING)
            try:
                with timed_stage("embed"):
                    vectors = embed_texts([c.text for c in chunks])
                chunk_store.save(commit_sha, chunks, vectors)
                chat_available = True
            except EmbeddingError as e:
                # Chat is a bonus feature layered on top of the guide; if
                # embedding fails (e.g. no API key, transient outage), the
                # onboarding guide should still be delivered rather than
                # failing the whole job.
                logger.warning("Embedding failed for job %s, continuing without chat: %s", job_id, e)

        diagram = build_dependency_mermaid(analysis)

        job_store.update(job_id, status=JobStatus.GENERATING_GUIDE)
        with timed_stage("generate_guide"):
            guide = generate_onboarding_guide(analysis)

        condensed_bytes = len(condensed_payload_json(analysis).encode("utf-8"))
        raw_bytes = analysis.total_source_bytes
        reduction_pct = round(100 * (1 - condensed_bytes / raw_bytes), 1) if raw_bytes else 0.0

        stats = {
            "files_included": analysis.total_files_included,
            "files_skipped": len(analysis.skipped_files),
            "raw_source_bytes": raw_bytes,
            "llm_payload_bytes": condensed_bytes,
            "payload_reduction_pct": reduction_pct,
            "chunks_indexed": len(chunks),
            "cache_hit": False,
        }

        analysis_cache.save(commit_sha, url, analysis, guide, diagram, stats)

        job_store.update(
            job_id,
            status=JobStatus.DONE,
            repo_analysis=analysis,
            markdown_guide=guide,
            dependency_diagram=diagram,
            stats=stats,
            chat_available=chat_available,
        )
        jobs_total.labels(status="done").inc()
    except (InvalidRepoUrlError, RepoTooLargeError) as e:
        job_store.update(job_id, status=JobStatus.ERROR, error=str(e))
        jobs_total.labels(status="error").inc()
    except GeminiClientError as e:
        job_store.update(job_id, status=JobStatus.ERROR, error=f"LLM generation failed: {e}")
        jobs_total.labels(status="error").inc()
    except Exception as e:
        logger.exception("Unexpected pipeline failure for job %s", job_id)
        job_store.update(job_id, status=JobStatus.ERROR, error=f"Unexpected error: {e}")
        jobs_total.labels(status="error").inc()
