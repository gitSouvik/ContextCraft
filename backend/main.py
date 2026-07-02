"""
ContextCraft API.

POST /analyze            -> kicks off a background job for a repo URL, returns job_id immediately
GET  /jobs/{id}           -> poll for status/result
POST /jobs/{id}/chat       -> ask a question about that job's repo (RAG over indexed code chunks)
GET  /metrics              -> Prometheus scrape endpoint
GET  /health                -> liveness check

The clone+parse+embed+LLM pipeline routinely takes longer than a typical HTTP
timeout, so /analyze is deliberately job-based rather than synchronous: the
frontend polls /jobs/{id} rather than holding one long request open.
FastAPI runs sync background tasks in a worker thread automatically, so this
doesn't block the event loop for other concurrent requests.

/analyze and /jobs/{id}/chat are rate limited per client IP because both
spend a shared Gemini free-tier quota (Google's limits are per-project, not
per-caller) — see middleware/rate_limit.py.
"""
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .jobs import job_store
from .middleware.rate_limit import GCRARateLimiter
from .models import AnalyzeRequest, ChatRequest, ChatResponse, JobResponse, JobResult, JobStatus
from .observability import configure_logging, rate_limited_total
from .pipeline import run_pipeline
from .rag.chat import ChatError, answer_question
from .storage import chunk_store

configure_logging()

app = FastAPI(
    title="ContextCraft API",
    description="Automated architecture mapping, onboarding-guide generation, and RAG chat for public Python repos.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for local demo use; tighten before exposing this publicly
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5 analyses per 5 minutes per IP (burst of 2) — each /analyze can trigger a
# guide-generation call plus several batched embedding calls, against a free
# tier quota shared across every visitor to this deployment.
analyze_limiter = GCRARateLimiter(rate=5, period_seconds=300, burst=2)
# 15 chat turns per minute per IP (burst of 4) — each turn is one embed call
# plus one generate call, both much cheaper than a full /analyze.
chat_limiter = GCRARateLimiter(rate=15, period_seconds=60, burst=4)


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/analyze", response_model=JobResponse)
def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks, http_request: Request):
    key = _client_key(http_request)
    allowed, retry_after = analyze_limiter.allow(key)
    if not allowed:
        rate_limited_total.labels(route="analyze").inc()
        raise HTTPException(
            status_code=429,
            detail=f"Too many analyze requests. Try again in {retry_after:.0f}s.",
            headers={"Retry-After": f"{retry_after:.0f}"},
        )

    job_id = job_store.create()
    background_tasks.add_task(run_pipeline, job_id, request.repo_url)
    return JobResponse(job_id=job_id, status=JobStatus.PENDING)


@app.get("/jobs/{job_id}", response_model=JobResult)
def get_job(job_id: str):
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/jobs/{job_id}/chat", response_model=ChatResponse)
def chat(job_id: str, request: ChatRequest, http_request: Request):
    key = _client_key(http_request)
    allowed, retry_after = chat_limiter.allow(key)
    if not allowed:
        rate_limited_total.labels(route="chat").inc()
        raise HTTPException(
            status_code=429,
            detail=f"Too many chat requests. Try again in {retry_after:.0f}s.",
            headers={"Retry-After": f"{retry_after:.0f}"},
        )

    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.chat_available or job.repo_analysis is None:
        raise HTTPException(status_code=409, detail="This job's repo hasn't been indexed for chat.")

    try:
        answer, sources = answer_question(
            request.question, job.repo_analysis.commit_sha, chunk_store
        )
    except ChatError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return ChatResponse(answer=answer, sources=sources)
