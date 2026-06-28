export interface AuditEvent {
  event_type: "query" | "refusal" | "response";
  query_text: string | null;
  retrieved_ids: string[];
  withheld_ids: string[];
  refusal_ref: string | null;
  response_text: string | null;
  conflicts_found: { count: number; subjects: string[] } | null;
  latency_ms: number | null;
  created_at: string;
}

export interface AuditRow {
  correlation_id: string;
  user_id: string | null;
  first_event_at: string;
  latency_ms: number;
  had_refusal: boolean;
  had_conflict: boolean;
  event_count: number;
  events: AuditEvent[];
}

export interface AuditPage {
  rows: AuditRow[];
  next_cursor: string | null;
}

export interface AuditQuery {
  cursor?: string;
  user_id?: string;
  start?: string;
  end?: string;
  has_refusal?: boolean;
  has_conflict?: boolean;
  limit?: number;
}
