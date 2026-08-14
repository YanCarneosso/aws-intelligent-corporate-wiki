export interface Citation {
  document_id: string;
  chunk_id: string;
  source_file: string;
  score: number;
  excerpt: string;
  page?: number;
  source_row?: number;
  opportunity_id?: string;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  sufficient_evidence: boolean;
  correlation_id: string;
  latency_ms: number;
}

export interface Session {
  email: string;
  idToken: string;
}

export type QueryState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: QueryResponse }
  | { status: "error"; message: string; correlationId?: string };
