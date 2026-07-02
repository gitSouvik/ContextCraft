from typing import Protocol

from ...models import FileAnalysis


class LanguageAnalyzer(Protocol):
    language_id: str  # "python", "javascript", "go", ...

    def analyze(self, source: str, rel_path: str) -> FileAnalysis: ...
