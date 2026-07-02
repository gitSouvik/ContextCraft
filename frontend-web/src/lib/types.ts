export interface ImportInfo {
  module: string;
  names: string[];
  is_from: boolean;
  lineno: number;
}

export interface FunctionInfo {
  name: string;
  args: string[];
  lineno: number;
  end_lineno: number;
  docstring?: string;
  decorators: string[];
  complexity: number;
  calls: string[];
}

export interface ClassInfo {
  name: string;
  bases: string[];
  lineno: number;
  end_lineno: number;
  docstring?: string;
  methods: FunctionInfo[];
  decorators: string[];
}

export interface FileAnalysis {
  path: string;
  language: string;
  imports: ImportInfo[];
  classes: ClassInfo[];
  functions: FunctionInfo[];
  is_entry_point: boolean;
  entry_point_reasons: string[];
  loc: number;
  source_bytes: number;
  parse_error?: string;
}

export interface RepoAnalysis {
  repo_url: string;
  repo_name: string;
  commit_sha: string;
  files: FileAnalysis[];
  total_files_scanned: number;
  total_files_included: number;
  skipped_files: string[];
  total_source_bytes: number;
}

export type JobStatus =
  | 'pending'
  | 'cloning'
  | 'analyzing'
  | 'embedding'
  | 'generating_guide'
  | 'done'
  | 'error';

export interface JobResponse {
  job_id: string;
  status: JobStatus;
}

export interface JobResult {
  job_id: string;
  status: JobStatus;
  repo_analysis?: RepoAnalysis;
  markdown_guide?: string;
  dependency_diagram?: string;
  error?: string;
  stats?: Record<string, any>;
  chat_available: boolean;
}

export interface ChatSource {
  path: string;
  name: string;
  kind: string;
  lineno: number;
  end_lineno: number;
  relevance: number;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
}
