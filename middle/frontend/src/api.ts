export type Envelope<T> = { code: number; message: string; data: T };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || r.statusText);
  }
  const body = (await r.json()) as Envelope<T>;
  if (body.code !== 0) throw new Error(body.message || "api error");
  return body.data;
}

export const api = {
  dashboard: () => request<Record<string, unknown>>("/api/v1/dashboard"),
  jobs: (status?: string) =>
    request<Record<string, unknown>[]>(`/api/v1/jobs${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  job: (id: number) => request<Record<string, unknown>>(`/api/v1/jobs/${id}`),
  pending: (channel: string) => request<Record<string, unknown>[]>(`/api/v1/pending/${channel}`),
  run: () => request<{ started: boolean }>("/api/v1/run", { method: "POST" }),
  runStatus: () => request<Record<string, unknown>>("/api/v1/run/status"),
  publish: (article_id: number, channel: string, note = "") =>
    request<Record<string, unknown>>("/api/v1/publish", {
      method: "POST",
      body: JSON.stringify({ article_id, channel, note }),
    }),
  publishingStats: (days = 30) =>
    request<Record<string, unknown>>(`/api/v1/publishing/stats?days=${days}`),
};
