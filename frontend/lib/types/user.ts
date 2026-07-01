export interface RecentQueryItem {
  correlation_id: string;
  query: string;
  occurred_at: string;
  latency_ms: number | null;
}

export interface RecentQueriesResponse {
  items: RecentQueryItem[];
}
