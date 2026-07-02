"""
The ONLY place in this codebase that talks to an LLM, and the only place that
touches the network for AI inference. Two things are deliberate here:

1. We never send raw source code — only the condensed structural JSON built
   from the deterministic AST analysis. `_condense_analysis` is the actual
   mechanism behind the "reduced token payload vs raw code ingestion" claim,
   so keep it honest: if you add fields here, you're adding tokens.

2. As of mid-2026 the Gemini API free tier is tight (Flash-family models only,
   single-digit-to-low-teens requests/minute) and gets tightened further
   without much notice, so retrying on 429 with backoff isn't optional
   polish — without it this tool will fail intermittently under normal use.
"""
import json
import os
from typing import Optional

from google import genai
from google.genai import types

from ..models import RepoAnalysis
from .backoff import TransientCallFailure, call_with_backoff

# Gemini 2.5 Flash is free-tier eligible as of this writing; override via env
# var since Google's free-tier model lineup changes faster than this code will.
DEFAULT_MODEL = os.environ.get("CONTEXTCRAFT_GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_INSTRUCTION = """You are a senior software engineer writing an onboarding guide for a \
new teammate joining an unfamiliar Python codebase.

You are given a deterministic, structurally-derived JSON map of the repository \
(files, imports, classes, functions, the names each function calls, and \
detected entry points) — you have NOT been given the raw source code. Do not \
invent files, functions, or behavior that isn't present in the JSON. If \
something is ambiguous from structure alone, say so rather than guessing.

Respond ONLY in Markdown, structured into exactly these three sections, in \
this order, with these exact headings:

## 1. Core Entry Points
Where should a new developer start reading? Reference the files flagged as \
entry points and explain why (e.g. a `__main__` guard, route handlers, CLI \
commands).

## 2. Data Flow
Trace how data likely moves through the system based on the import graph and \
the function call names — which modules call into which, and what the \
probable request/data lifecycle looks like.

## 3. Key Dependencies
Summarize the most-imported internal modules and any notable third-party \
libraries visible in the imports, and what role each likely plays.

Keep it concise and skimmable. Use bullet points and inline code formatting \
for file, class, and function names."""


class GeminiClientError(RuntimeError):
    pass


def _condense_analysis(analysis: RepoAnalysis) -> dict:
    """
    Strips the full typed analysis down to only what the LLM needs to write
    the guide. This is the actual token-savings mechanism the project claims
    credit for — every field added here has a real token cost, so it's kept
    deliberately narrow (e.g. only the first 8 calls per function, no line
    numbers, no docstrings unless later found necessary).
    """
    files = []
    for f in analysis.files:
        if f.parse_error:
            continue
        files.append({
            "path": f.path,
            "language": f.language,
            "is_entry_point": f.is_entry_point,
            "entry_point_reasons": f.entry_point_reasons,
            "imports": sorted({imp.module for imp in f.imports if imp.module}),
            "classes": [
                {"name": c.name, "bases": c.bases, "methods": [m.name for m in c.methods]}
                for c in f.classes
            ],
            "functions": [
                {"name": fn.name, "calls": fn.calls[:8], "complexity": fn.complexity}
                for fn in f.functions
            ],
        })
    return {
        "repo_name": analysis.repo_name,
        "commit_sha": analysis.commit_sha[:12],
        "files": files,
    }


def condensed_payload_json(analysis: RepoAnalysis) -> str:
    """Exposed separately so callers (e.g. the pipeline) can report payload size."""
    return json.dumps(_condense_analysis(analysis), separators=(",", ":"))


def generate_onboarding_guide(analysis: RepoAnalysis, api_key: Optional[str] = None,
                               max_retries: int = 4) -> str:
    """
    Sends the condensed structural JSON to Gemini and returns the 3-section
    Markdown guide. Retries with exponential backoff on 429 (rate limit) and
    503 (transient overload) responses, since the free tier's RPM ceiling is
    low enough to hit in normal single-user usage.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise GeminiClientError(
            "No Gemini API key found. Set the GEMINI_API_KEY environment variable "
            "(get a free key at https://aistudio.google.com/apikey)."
        )

    client = genai.Client(api_key=key)
    payload = condensed_payload_json(analysis)
    prompt = (
        "Here is the structural JSON map of the repository:\n\n"
        f"{payload}\n\n"
        "Write the three-section onboarding guide now."
    )

    def _call():
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2,
            ),
        )
        if not response.text:
            raise GeminiClientError("Gemini returned an empty response.")
        return response.text

    try:
        return call_with_backoff(_call, max_retries=max_retries)
    except TransientCallFailure as e:
        raise GeminiClientError(f"Gemini API call failed after {max_retries} attempt(s): {e}") from e
