export type User = {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
};

export type AuthResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
};

export type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type DocumentStatus = "queued" | "processing" | "ready" | "failed";

export type ProcessingJob = {
  id: string;
  status: DocumentStatus;
  progress: number;
  detail: string;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
};

export type DocumentSummary = {
  id: string;
  filename: string;
  status: DocumentStatus;
  page_count: number;
  chunk_count: number;
  size_bytes: number;
  error_message: string | null;
  has_insights: boolean;
  created_at: string;
  processed_at: string | null;
};

export type DocumentDetail = DocumentSummary & {
  latest_job: ProcessingJob | null;
};

export type DocumentStatusResponse = {
  id: string;
  status: DocumentStatus;
  error_message: string | null;
  page_count: number;
  chunk_count: number;
  job: ProcessingJob | null;
};

export type DocumentPage = {
  page_number: number;
  text: string;
  char_count: number;
  extraction_method: string;
};

export type InsightField = {
  key: string;
  label: string;
  category: string;
  value: string;
  quote: string;
  page: number | null;
  confidence: number;
  status: "found" | "ambiguous" | "missing";
};

export type Insight = {
  document_id: string;
  filename: string;
  fields: InsightField[];
  meta: Record<string, string | number | null>;
  extraction_method: string;
  llm_model: string | null;
  updated_at: string;
};

export type Citation = {
  source_id: string;
  page_start: number;
  page_end: number;
  quote: string;
  is_valid: boolean;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  status: "complete" | "streaming" | "failed";
  citations: Citation[];
  confidence: number | null;
  insufficient_evidence: boolean;
  citation_status: string | null;
  model: string | null;
  latency_ms: number | null;
  created_at: string;
  error_message?: string | null;
  stated?: string[];
  inferred?: string[];
  not_in_document?: string[];
};

export type Conversation = {
  id: string;
  document_id: string;
  document_filename: string | null;
  title: string;
  last_activity_at: string | null;
  created_at: string;
  message_count?: number;
  preview?: string | null;
};

export type ConversationDetail = Conversation & { messages: Message[] };

export type Usage = {
  documents: number;
  conversations: number;
  questions: number;
  comparisons: number;
  quota: number;
  quota_used_percent: number;
};

export type Meta = {
  app_version: string;
  environment: string;
  llm_configured: boolean;
  llm_model: string;
  embeddings_mode: string;
  ocr_enabled: boolean;
  max_upload_mb: number;
  max_pdf_pages: number;
  retrieval_top_k: number;
};

export type ComparisonValue = {
  document_id: string;
  value: string;
  status: string;
  page: number | null;
  quote: string;
  confidence: number;
};

export type ComparisonField = {
  key: string;
  label: string;
  category: string;
  values: ComparisonValue[];
  differs: boolean;
  missing_in: string[];
};

export type Comparison = {
  id: string;
  title: string;
  document_ids: string[];
  documents: { id: string; filename: string }[];
  fields: ComparisonField[];
  summary: { fields_compared: number; differences: number; fields_missing_somewhere: number };
  created_at: string;
};

export type StreamEvent =
  | {
      event: "meta";
      data: {
        conversation_id: string;
        user_message_id: string;
        assistant_id: string;
        retrieval_mode: string;
        sources: { source_id: string; page_start: number; page_end: number; heading: string }[];
        model: string;
      };
    }
  | { event: "delta"; data: { text: string } }
  | { event: "final"; data: { message: Message } }
  | { event: "error"; data: { code: string; message: string } };
