# ContextCraft

Paste a public GitHub Python repo URL and get back an architecture map, an onboarding guide, and a chat interface to ask follow-up questions about the code — all generated from a deterministic static analysis, with tightly scoped, auditable boundaries on what ever reaches an LLM.

## Why it's built this way

There are two separate LLM-input paths here, and they make different privacy trade-offs on purpose:

1. **Onboarding guide.** A FastAPI backend clones the repo, walks it with Python's `ast` module to build a typed structural map (imports, classes, functions, call names, cyclomatic complexity, detected entry points), and sends only that condensed JSON — never the source itself — to Gemini. The dependency diagram is built entirely from the import graph, deterministically, with no LLM involved, so it can't hallucinate a relationship that isn't actually in the code.
2. **Repo chat (RAG).** Every function, method, class, and file gets embedded (Gemini's free `gemini-embedding-001`) and indexed. A chat question is embedded the same way, the top-k most relevant chunks are retrieved by cosine similarity, and *only those specific snippets* — never the whole codebase — are sent to Gemini to answer. This is a narrower, more targeted disclosure than "no source ever leaves this process": it's "no source leaves this process except the few lines relevant to the question you actually asked."

The temp clone is deleted the moment the analysis + chunking pass finishes; nothing about the raw source persists on disk past that scope.

## Quickstart

### Option A — Docker Compose (recommended)

```bash
cp .env.example .env
# edit .env and paste in a free key from https://aistudio.google.com/apikey

docker compose up --build
```

Backend: `http://localhost:8000` · Frontend: `http://localhost:8501`. Job data, the analysis cache, and the chat index all persist in a named Docker volume across restarts.

### Option B — Local Python

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and paste in a free key from https://aistudio.google.com/apikey

# terminal 1 — backend
export $(cat .env | xargs)
uvicorn backend.main:app --reload --port 8000

# terminal 2 — frontend
streamlit run frontend/app.py
```

Open the Streamlit URL it prints, paste a public GitHub repo URL (e.g. `https://github.com/pallets/flask`), click **Analyze**, then use the **💬 Ask about this repo** tab once it's done.

## Running tests / lint / type-check

```bash
pip install -r requirements-dev.txt
ruff check .          # lint
mypy backend/         # type-check
pytest tests/ -v      # 41 tests, no network required — Gemini calls are never hit directly
```

`.github/workflows/ci.yml` runs all three on every push/PR, plus a Docker build sanity check for both images.

Tests cover: the AST visitor (entry-point detection, complexity scoring, call extraction, nested-scope handling, syntax-error resilience), the file scanner (exclusions, caps), the dependency diagram builder, the repo URL allowlist, the RAG chunker (correct line-slicing, chunk granularity), the SQLite job store (including persistence across a simulated restart), the content-addressed analysis cache, the GCRA rate limiter, and cosine-similarity chunk retrieval.

## Architecture

```
frontend/app.py                  Streamlit UI — polls the API, renders the guide, diagram, and chat
backend/main.py                   FastAPI app: /analyze, /jobs/{id}, /jobs/{id}/chat, /metrics, /health
backend/pipeline.py                 Orchestrates: cache check -> clone -> analyze -> embed -> diagram -> guide
backend/jobs.py                      SQLite-backed job store (create/update/get — same interface, real persistence)
backend/cache.py                      Content-addressed cache of full results, keyed by commit SHA
backend/storage.py                     Shared SQLite-backed singletons (jobs / cache / chunks share one DB file)
backend/observability.py                JSON structured logging + Prometheus metrics (GET /metrics)
backend/middleware/rate_limit.py         GCRA rate limiter protecting the shared Gemini free-tier quota
backend/analyzer/
  repo_cloner.py                          URL allowlist, ls-remote cache pre-check, shallow clone, size cap
  scanner.py                               os.walk with directory exclusions, file-count cap, per-file size cap
  ast_visitor.py                            Core static analysis: imports, classes, functions, complexity
  chunker.py                                 Builds RAG chunks (file/class/function) with exact source slices
  repo_analyzer.py                            Aggregates file analyses; builds the Mermaid dependency graph
backend/llm/
  gemini_client.py                             Condenses analysis to minimal JSON, generates the guide
  backoff.py                                    Shared exponential-backoff retry used by every Gemini call site
backend/rag/
  embeddings.py                                  Batched Gemini embed_content calls
  store.py                                        SQLite chunk store + numpy cosine-similarity top-k search
  chat.py                                          RAG orchestration: retrieve -> bound context -> generate
backend/models.py                Shared Pydantic contracts used across every layer above
```

### Request flow

1. Streamlit POSTs a repo URL to `/analyze`. The API checks a per-IP GCRA rate limit, then returns a `job_id` immediately — the full pipeline is too slow for one synchronous request.
2. A background task validates the URL against a `github.com` allowlist, then does a `git ls-remote` to get the current commit SHA **without cloning anything**. If that SHA is already in the analysis cache, the job completes instantly with the cached guide, diagram, and chat index — clone, AST pass, embedding, and the LLM call are all skipped.
3. On a cache miss: shallow-clones (`--depth 1`) into a temp dir, aborting with cleanup if it exceeds a size cap.
4. `scanner.py` walks the clone, skipping `venv`/`node_modules`/`tests`/etc. and capping at 50 files.
5. `ast_visitor.py` parses each file into a typed `FileAnalysis` (imports, classes, functions, per-function cyclomatic complexity, a lightweight call list, entry-point detection). `chunker.py` runs in the same pass, slicing exact source snippets per function/class/method by `lineno`/`end_lineno` while the file content is already in hand.
6. The temp clone is deleted the instant this pass finishes. Everything downstream works only from the typed `RepoAnalysis` object and the extracted chunks — never the filesystem again.
7. Chunks are batch-embedded and written to the SQLite chunk store, keyed by commit SHA.
8. `repo_analyzer.py` builds a Mermaid `graph TD` straight from the import graph — no LLM involved.
9. `gemini_client.py` condenses the analysis into a minimal JSON dict and generates the 3-section guide. The full result (analysis, guide, diagram, stats) is written to the content-addressed cache.
10. Streamlit polls `/jobs/{id}` and renders the guide, a live Mermaid diagram, the raw JSON structure, and — once `chat_available` is true — a chat tab. Each chat turn hits `/jobs/{id}/chat`, which embeds the question, retrieves the top-6 chunks by cosine similarity, and sends only those to Gemini, returning the answer plus which files/functions it drew from.

## MVP constraints (by design)

- Supports Python, JavaScript/TypeScript, Go, Java, Rust, C/C++, and Ruby. Context files (README, Dockerfile, etc.) are also extracted.
- 50-file cap per repo, 500KB per-file size cap, 200MB total clone size cap.
- `venv`, `node_modules`, `.git`, `tests`, `__pycache__`, `build`, `dist`, and similar are excluded.
- The Gemini guide output is constrained to exactly 3 sections: Core Entry Points, Data Flow, Key Dependencies.
- Chat retrieval is a plain numpy cosine-similarity scan, not an ANN index — appropriate at "at most a few hundred chunks per repo" scale; would need FAISS/pgvector past that.

## Known limitations

- **The dependency diagram is a heuristic, not a full import resolver.** It matches imported module names against scanned file paths; deeply dynamic imports (`importlib.import_module(some_variable)`) won't resolve. Currently, diagram resolution is scoped to Python and JS/TS files. Imports for Go, Java, Rust, C/C++, and Ruby are extracted and queryable via RAG chat, but won't be plotted on the Mermaid graph.
- **The job store, cache, and chunk index are all SQLite, single-writer.** That's a deliberate, load-bearing choice at this scale — zero infrastructure to stand up, real persistence across restarts, and each store's interface was kept narrow enough that swapping to Postgres later (if this ever ran behind multiple app servers) wouldn't touch calling code.
- **Cache invalidation is a non-problem here, not a solved one** — it's keyed by immutable commit SHA, so there's nothing to invalidate. Note that this only works because the key is content-addressed; a cache keyed by repo URL alone would need a real invalidation strategy.
- **The rate limiter is in-memory and per-process.** Fine behind a single backend container; horizontally scaling the API would need the GCRA state moved to something shared (Redis is the obvious next step) — same "swap the store, not the interface" pattern as the job store.
- **Cyclomatic complexity is a simplified branch-count**, not a full McCabe implementation over a real control-flow graph — deliberately kept dependency-free.
- **Free-tier Gemini rate limits are tight and change without much notice.** Generation and embedding calls both retry with exponential backoff (`llm/backoff.py`), and `/analyze` + `/jobs/{id}/chat` are both rate-limited per IP specifically to protect that shared quota — but sustained/production use would need a paid tier.
- **Chat retrieval has no reranking step** — it's single-stage cosine similarity over the embedding space. A production RAG system would typically add a cross-encoder reranker on the top-N candidates before generation; skipped here as a scale/cost trade-off, serving as a clear future improvement.

