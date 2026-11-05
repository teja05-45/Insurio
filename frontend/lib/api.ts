import type {
  AuthResponse,
  Comparison,
  Conversation,
  ConversationDetail,
  DocumentDetail,
  DocumentPage,
  DocumentStatusResponse,
  DocumentSummary,
  Insight,
  Meta,
  Paginated,
  StreamEvent,
  Usage,
  User,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

const ACCESS_TOKEN_KEY = "insurio.access_token";
const REFRESH_TOKEN_KEY = "insurio.refresh_token";

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(message: string, status: number, code = "request_failed", details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function read(key: string): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(key);
}

export function getAccessToken(): string | null {
  return read(ACCESS_TOKEN_KEY);
}

export function setTokens(access: string, refresh: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, access);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function hasSession(): boolean {
  return Boolean(read(ACCESS_TOKEN_KEY));
}

let refreshInFlight: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  const refresh = read(REFRESH_TOKEN_KEY);
  if (!refresh) return false;
  refreshInFlight = (async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!response.ok) {
        clearTokens();
        return false;
      }
      const data = (await response.json()) as AuthResponse;
      setTokens(data.access_token, data.refresh_token);
      return true;
    } catch {
      clearTokens();
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

type ApiInit = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  auth?: boolean;
};

async function parseError(response: Response): Promise<ApiError> {
  let message = response.statusText || "Request failed.";
  let code = "request_failed";
  let details: unknown;
  try {
    const payload = (await response.json()) as {
      error?: { message?: string; code?: string; details?: unknown };
    };
    if (payload?.error) {
      message = payload.error.message ?? message;
      code = payload.error.code ?? code;
      details = payload.error.details;
    }
  } catch {
    // Non-JSON error bodies fall back to the status text.
  }
  return new ApiError(message, response.status, code, details);
}

async function request<T>(path: string, init: ApiInit = {}, retried = false): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers ?? {}) };
  let body: BodyInit | undefined;
  if (init.body instanceof FormData) {
    body = init.body;
  } else if (init.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(init.body);
  }
  if (init.auth !== false) {
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: init.method ?? "GET",
    headers,
    body,
    signal: init.signal,
    cache: "no-store",
  });

  if (response.status === 401 && init.auth !== false && !retried) {
    if (await refreshSession()) return request<T>(path, init, true);
  }
  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function download(path: string): Promise<Blob> {
  const token = getAccessToken();
  const response = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });
  if (response.status === 401 && (await refreshSession())) return download(path);
  if (!response.ok) throw await parseError(response);
  return response.blob();
}

function parseEventBlock(block: string): StreamEvent | null {
  let event = "";
  let data = "";
  for (const line of block.split("\n")) {
    if (line.startsWith("event: ")) event = line.slice(7);
    else if (line.startsWith("data: ")) data = line.slice(6);
  }
  if (!event || !data) return null;
  return { event, data: JSON.parse(data) } as StreamEvent;
}

export async function* streamAnswer(
  path: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const send = async (retried: boolean): Promise<Response> => {
    const token = getAccessToken();
    const response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      signal,
    });
    if (response.status === 401 && !retried && (await refreshSession())) return send(true);
    return response;
  };

  const response = await send(false);
  if (!response.ok) throw await parseError(response);
  if (!response.body) throw new ApiError("The answer stream was empty.", 502);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const event = parseEventBlock(block);
        if (event) yield event;
        boundary = buffer.indexOf("\n\n");
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export const api = {
  // Auth
  register: (payload: { email: string; password: string; full_name: string }) =>
    request<AuthResponse>("/auth/register", { method: "POST", body: payload, auth: false }),
  login: (payload: { email: string; password: string }) =>
    request<AuthResponse>("/auth/login", { method: "POST", body: payload, auth: false }),
  logout: () =>
    request<{ message: string }>("/auth/logout", {
      method: "POST",
      body: { refresh_token: read(REFRESH_TOKEN_KEY) ?? "" },
    }),
  forgotPassword: (email: string) =>
    request<{ message: string; reset_token: string | null }>("/auth/forgot-password", {
      method: "POST",
      body: { email },
      auth: false,
    }),
  resetPassword: (token: string, new_password: string) =>
    request<{ message: string }>("/auth/reset-password", {
      method: "POST",
      body: { token, new_password },
      auth: false,
    }),
  me: () => request<User>("/auth/me"),
  updateProfile: (full_name: string) =>
    request<User>("/auth/me", { method: "PATCH", body: { full_name } }),
  changePassword: (current_password: string, new_password: string) =>
    request<{ message: string }>("/auth/change-password", {
      method: "POST",
      body: { current_password, new_password },
    }),
  deleteAccount: (password: string) =>
    request<{ message: string }>("/auth/me", { method: "DELETE", body: { password } }),
  sessions: () =>
    request<{ id: string; created_at: string; expires_at: string; user_agent: string; ip_address: string }[]>(
      "/auth/sessions",
    ),

  // Deployment + usage
  meta: () => request<Meta>("/meta", { auth: false }),
  usage: () => request<Usage>("/usage"),

  // Documents
  listDocuments: (page = 1, pageSize = 20, status?: string) =>
    request<Paginated<DocumentSummary>>(
      `/documents?page=${page}&page_size=${pageSize}${status ? `&status=${status}` : ""}`,
    ),
  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentDetail>("/documents", { method: "POST", body: form });
  },
  getDocument: (id: string) => request<DocumentDetail>(`/documents/${id}`),
  documentStatus: (id: string) => request<DocumentStatusResponse>(`/documents/${id}/status`),
  documentPages: (id: string) => request<DocumentPage[]>(`/documents/${id}/pages`),
  deleteDocument: (id: string) =>
    request<{ message: string }>(`/documents/${id}`, { method: "DELETE" }),
  insights: (id: string) => request<Insight>(`/documents/${id}/insights`),
  refreshInsights: (id: string) =>
    request<Insight>(`/documents/${id}/insights/refresh`, { method: "POST" }),
  documentFile: (id: string) => download(`/documents/${id}/file`),

  // Conversations
  listConversations: (page = 1, pageSize = 20) =>
    request<Paginated<Conversation>>(`/conversations?page=${page}&page_size=${pageSize}`),
  createConversation: (document_id: string, title?: string) =>
    request<Conversation>("/conversations", {
      method: "POST",
      body: { document_id, title: title ?? null },
    }),
  getConversation: (id: string) => request<ConversationDetail>(`/conversations/${id}`),
  renameConversation: (id: string, title: string) =>
    request<Conversation>(`/conversations/${id}`, { method: "PATCH", body: { title } }),
  deleteConversation: (id: string) =>
    request<{ message: string }>(`/conversations/${id}`, { method: "DELETE" }),
  feedback: (messageId: string, rating: "up" | "down", comment?: string) =>
    request<{ message: string }>(`/messages/${messageId}/feedback`, {
      method: "POST",
      body: { rating, comment: comment ?? null },
    }),

  // Comparisons
  listComparisons: () => request<Paginated<Comparison>>("/comparisons"),
  createComparison: (document_ids: string[], title?: string) =>
    request<Comparison>("/comparisons", {
      method: "POST",
      body: { document_ids, title: title ?? null },
    }),
  getComparison: (id: string) => request<Comparison>(`/comparisons/${id}`),
  deleteComparison: (id: string) =>
    request<{ message: string }>(`/comparisons/${id}`, { method: "DELETE" }),
};
