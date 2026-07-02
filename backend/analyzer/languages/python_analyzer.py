from ...models import FileAnalysis
from ..ast_visitor import analyze_source


class PythonAnalyzer:
    language_id = "python"
    
    def analyze(self, source: str, rel_path: str) -> FileAnalysis:
        analysis = analyze_source(source, rel_path)
        analysis.language = self.language_id
        return analysis
