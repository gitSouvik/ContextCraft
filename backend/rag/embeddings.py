"""
Wraps Gemini's embed_content endpoint (free tier: gemini-embedding-001, ~10M
tokens/minute as of writing — generous enough that batching, not quota, is
the main design concern here).

Batching matters because embed_content accepts a *list* of contents per call:
embedding all of a repo's ~50-200 chunks in a handful of batched calls costs
a fraction of the free tier's per-minute request ceiling compared to one call
per chunk.
"""
import os
from typing import List, Optional

from google import genai
from google.genai import types

from ..llm.backoff import TransientCallFailure, call_with_backoff

EMBED_MODEL = os.environ.get("CONTEXTCRAFT_EMBED_MODEL", "gemini-embedding-001")
EMBED_DIMENSIONS = 768  # Matryoshka-truncated; ample for a <=50-file repo's chunk set
BATCH_SIZE = 32


class EmbeddingError(RuntimeError):
    pass


def _client(api_key: Optional[str] = None) -> genai.Client:
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise EmbeddingError(
            "No Gemini API key found. Set the GEMINI_API_KEY environment variable "
            "(get a free key at https://aistudio.google.com/apikey)."
        )
    return genai.Client(api_key=key)


def embed_texts(texts: List[str], api_key: Optional[str] = None,
                 task_type: str = "RETRIEVAL_DOCUMENT", max_retries: int = 4) -> List[List[float]]:
    """Embeds a batch of texts, returning one vector per input in the same order."""
    if not texts:
        return []
    client = _client(api_key)
    vectors: List[List[float]] = []

    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]

        def _call(batch=batch):
            return client.models.embed_content(
                model=EMBED_MODEL,
                contents=batch,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=EMBED_DIMENSIONS,
                ),
            )

        try:
            response = call_with_backoff(_call, max_retries=max_retries)
        except TransientCallFailure as e:
            raise EmbeddingError(f"Embedding call failed after {max_retries} attempt(s): {e}") from e
        vectors.extend(list(e.values) for e in response.embeddings)

    return vectors


def embed_query(text: str, api_key: Optional[str] = None) -> List[float]:
    """Embeds a single chat question. Uses RETRIEVAL_QUERY so it shares the same
    vector space as the RETRIEVAL_DOCUMENT-embedded chunks but is optimized
    for the query side of the asymmetric search."""
    return embed_texts([text], api_key=api_key, task_type="RETRIEVAL_QUERY")[0]
