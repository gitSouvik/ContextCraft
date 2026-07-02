"""
Shared data contracts for ContextCraft.

These models are the backbone of the "deterministic first, LLM second" design:
everything the static analyzer produces is a typed Pydantic object, and only a
condensed version of it is ever serialized and sent to the LLM.
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ImportInfo(BaseModel):
    module: str
    names: List[str] = Field(default_factory=list)  # populated for `from x import a, b`
    is_from: bool = False
    lineno: int


class FunctionInfo(BaseModel):
    name: str
    args: List[str] = Field(default_factory=list)
    lineno: int
    end_lineno: int = 0  # 0 means "unknown" (older cached records); chunker falls back to lineno
    docstring: Optional[str] = None
    decorators: List[str] = Field(default_factory=list)
    complexity: int = 1  # McCabe cyclomatic complexity
    calls: List[str] = Field(default_factory=list)  # names called within the function body


class ClassInfo(BaseModel):
    name: str
    bases: List[str] = Field(default_factory=list)
    lineno: int
    end_lineno: int = 0
    docstring: Optional[str] = None
    methods: List[FunctionInfo] = Field(default_factory=list)
    decorators: List[str] = Field(default_factory=list)


class FileAnalysis(BaseModel):
    path: str  # relative to repo root
    language: str = "unknown"
    imports: List[ImportInfo] = Field(default_factory=list)
    classes: List[ClassInfo] = Field(default_factory=list)
    functions: List[FunctionInfo] = Field(default_factory=list)  # module-level only
    is_entry_point: bool = False
    entry_point_reasons: List[str] = Field(default_factory=list)
    loc: int = 0
    source_bytes: int = 0
    parse_error: Optional[str] = None


class RepoAnalysis(BaseModel):
    repo_url: str
    repo_name: str
    commit_sha: str
    files: List[FileAnalysis] = Field(default_factory=list)
    total_files_scanned: int = 0
    total_files_included: int = 0
    skipped_files: List[str] = Field(default_factory=list)
    total_source_bytes: int = 0


class AnalyzeRequest(BaseModel):
    repo_url: str


class JobStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    ANALYZING = "analyzing"
    EMBEDDING = "embedding"
    GENERATING_GUIDE = "generating_guide"
    DONE = "done"
    ERROR = "error"


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobResult(BaseModel):
    job_id: str
    status: JobStatus
    repo_analysis: Optional[RepoAnalysis] = None
    markdown_guide: Optional[str] = None
    dependency_diagram: Optional[str] = None  # Mermaid `graph TD` syntax
    error: Optional[str] = None
    stats: Optional[dict] = None
    chat_available: bool = False  # True once this job's chunks are embedded and queryable


# --- RAG chat -----------------------------------------------------------
# A CodeChunk is the unit of retrieval: one file-level summary, class, or
# function/method, paired with its exact source snippet (sliced by
# lineno/end_lineno while the clone was still on disk). Only chunks a chat
# *query* actually retrieves are ever sent to the LLM — never the whole repo.

class CodeChunk(BaseModel):
    chunk_id: str
    path: str
    language: str = "unknown"
    kind: str  # "file" | "class" | "function" | "method" | "context_file"
    name: str
    lineno: int
    end_lineno: int
    text: str  # structural summary + snippet — what gets embedded
    snippet: str  # the raw source snippet — what gets shown/sent on retrieval


class ChatSource(BaseModel):
    path: str
    name: str
    kind: str
    lineno: int
    end_lineno: int
    relevance: float


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[ChatSource] = Field(default_factory=list)
