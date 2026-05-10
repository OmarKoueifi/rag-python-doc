// Mirrors backend Pydantic schemas. Keep in sync with app/schemas/*.py.

export type SourceRef = {
  rank: number;
  source_url: string;
  heading_path: string;
  module: string;
  anchor: string;
  similarity: number;
};

export type QuestionSummary = {
  id: number;
  session_id: string;
  question: string;
  answer: string | null;
  moderation_blocked: boolean;
  avg_similarity: number | null;
  retrieval_count: number;
  created_at: string;
};

export type QuestionDetail = QuestionSummary & {
  sources: SourceRef[];
};

export type QuestionList = {
  items: QuestionSummary[];
  total: number;
  limit: number;
  offset: number;
};

export type FlaggedRow = {
  id: number;
  session_id: string;
  question: string;
  flag_type: "moderation" | "injection" | string;
  flag_detail: string;
  blocked: boolean;
  created_at: string;
};

export type FlaggedList = {
  items: FlaggedRow[];
  total: number;
};

export type DailyCount = {
  day: string;
  count: number;
};

export type TopSource = {
  source_url: string;
  heading_path: string;
  module: string;
  count: number;
};

export type Metrics = {
  total_questions: number;
  total_blocked: number;
  total_flagged: number;
  mean_similarity: number | null;
  questions_per_day: DailyCount[];
  top_sources: TopSource[];
};

export type AuthStatus = { authenticated: boolean };
