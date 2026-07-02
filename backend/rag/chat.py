"""
Answers a natural-language question about a specific analyzed repo using
retrieval-augmented generation: embed the question, pull the top-k most
relevant code chunks (by cosine similarity) out of the SQLite chunk store,
and hand only those chunks — never the whole codebase — to Gemini as context.

This is the second and more targeted of the project's two LLM-input paths.
The onboarding guide (llm/gemini_client.py) sends a condensed structural
summary of the *entire* repo and never touches source. This path sends real
source, but strictly bounded to the handful of snippets retrieval selected
for one specific question.
"""
import os
from typing import List, Optional, Tuple

from google import genai
from google.genai import types

from ..llm.backoff import TransientCallFailure, call_with_backoff
from ..models import ChatSource
from .embeddings import EmbeddingError, embed_query
from .store import ChunkStore, top_k

CHAT_MODEL = os.environ.get("CONTEXTCRAFT_GEMINI_MODEL", "gemini-2.5-flash")
TOP_K = 6

CHAT_SYSTEM_INSTRUCTION = """You are answering a developer's question about a specific \
codebase using ONLY the retrieved code snippets provided below — you have not been given \
the rest of the repository. Reference file paths and function/class names using inline \
code formatting. If the retrieved snippets don't contain enough information to answer \
confidently, say so explicitly rather than guessing or inventing behavior that isn't \
shown."""


class ChatError(RuntimeError):
    pass


def answer_question(question: str, cache_key: str, store: ChunkStore,
                     api_key: Optional[str] = None, top_k_results: int = TOP_K,
                     max_retries: int = 4) -> Tuple[str, List[ChatSource]]:
    candidates = store.load(cache_key)
    if not candidates:
        raise ChatError("This repo hasn't been indexed for chat yet.")

    try:
        q_vector = embed_query(question, api_key=api_key)
    except EmbeddingError as e:
        raise ChatError(str(e)) from e

    ranked = top_k(q_vector, candidates, k=top_k_results)

    context_blocks = []
    sources: List[ChatSource] = []
    for score, chunk in ranked:
        block = f"### {chunk.path} (lines {chunk.lineno}-{chunk.end_lineno}) — {chunk.kind} `{chunk.name}`"
        if chunk.snippet:
            block += f"\n```{chunk.language}\n{chunk.snippet}\n```"
        else:
            block += f"\n{chunk.text}"
        context_blocks.append(block)
        sources.append(ChatSource(
            path=chunk.path, name=chunk.name, kind=chunk.kind,
            lineno=chunk.lineno, end_lineno=chunk.end_lineno, relevance=round(score, 3),
        ))

    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ChatError("No Gemini API key found. Set the GEMINI_API_KEY environment variable.")

    client = genai.Client(api_key=key)
    prompt = f"Question: {question}\n\nRetrieved code snippets:\n\n" + "\n\n".join(context_blocks)

    def _call():
        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=CHAT_SYSTEM_INSTRUCTION,
                temperature=0.2,
            ),
        )
        if not response.text:
            raise ChatError("Gemini returned an empty response.")
        return response.text

    try:
        answer = call_with_backoff(_call, max_retries=max_retries)
    except TransientCallFailure as e:
        raise ChatError(f"Chat generation failed after {max_retries} attempt(s): {e}") from e

    return answer, sources
