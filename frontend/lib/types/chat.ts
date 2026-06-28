export type Clearance = 'public' | 'restricted' | 'secret' | 'top_secret';

export interface AnswerOut {
  text: string;
  cited_chunk_ids: string[];
}

export interface CitationOut {
  marker: number;
  chunk_id: string;
  document_id: string;
  document_title: string;
  classification: Clearance;
  department: string;
  effective_date: string;
  snippet: string;
}

export interface PositionOut {
  marker: number;
  text: string;
}

export interface ConflictOut {
  subject: string;
  position_a: PositionOut;
  position_b: PositionOut;
}

export interface RefusalOut {
  reference_id: string;
  withheld_count: number;
}

export interface ChatResponse {
  query: string;
  answer: AnswerOut;
  citations: CitationOut[];
  conflicts: ConflictOut[];
  refusal: RefusalOut | null;
}
