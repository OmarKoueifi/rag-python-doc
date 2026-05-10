import type {
  AuthStatus,
  FlaggedList,
  Metrics,
  QuestionDetail,
  QuestionList,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const resp = await fetch(path, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, resp.status);
  }
  return (await resp.json()) as T;
}

export function adminLogin(password: string) {
  return request<AuthStatus>("/api/admin/login", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
}

export function adminLogout() {
  return request<AuthStatus>("/api/admin/logout", { method: "POST" });
}

export function adminMe() {
  return request<AuthStatus>("/api/admin/me");
}

export function getMetrics() {
  return request<Metrics>("/api/admin/metrics");
}

export type QuestionListFilters = {
  limit?: number;
  offset?: number;
  session_id?: string;
  blocked?: boolean;
};

export function listQuestions(f: QuestionListFilters = {}) {
  const qs = new URLSearchParams();
  if (f.limit !== undefined) qs.set("limit", String(f.limit));
  if (f.offset !== undefined) qs.set("offset", String(f.offset));
  if (f.session_id) qs.set("session_id", f.session_id);
  if (f.blocked !== undefined) qs.set("blocked", String(f.blocked));
  const q = qs.toString();
  return request<QuestionList>(`/api/admin/questions${q ? `?${q}` : ""}`);
}

export function getQuestion(id: number) {
  return request<QuestionDetail>(`/api/admin/questions/${id}`);
}

export function listFlagged(
  flagType?: "moderation" | "injection",
  limit = 50,
) {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (flagType) qs.set("flag_type", flagType);
  return request<FlaggedList>(`/api/admin/flagged?${qs.toString()}`);
}
