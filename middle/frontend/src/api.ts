export type Envelope<T> = { code: number; message: string; data: T };

export type Theme = {
  id: string;
  label: string;
  description?: string;
  feed_kinds?: string[];
  accounts?: Record<string, { label?: string; handle?: string; note?: string }>;
};

export type Site = {
  code: string;
  label: string;
  description?: string;
  theme_id?: string;
  base_url?: string;
};

export type PlatformChannel = {
  id: string;
  label: string;
  kind: string;
};

export type ChannelAccount = {
  id: string;
  site_code: string;
  channel_id: string;
  label: string;
  handle: string;
  profile_url: string;
  login_hint: string;
  note: string;
  enabled: boolean;
  is_primary: boolean;
};

export type ChannelConfigOverview = {
  sites: Site[];
  channels: PlatformChannel[];
  accounts_by_site_channel: Record<string, Record<string, ChannelAccount[]>>;
};

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

function q(params: Record<string, string | number | undefined>) {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export const api = {
  themes: () => request<Theme[]>("/api/v1/themes"),
  dashboard: (theme?: string) => request<Record<string, unknown>>(`/api/v1/dashboard${q({ theme })}`),
  jobs: (status?: string, theme?: string) =>
    request<Record<string, unknown>[]>(`/api/v1/jobs${q({ status, theme })}`),
  job: (id: number) => request<Record<string, unknown>>(`/api/v1/jobs/${id}`),
  pending: (channel: string, theme?: string) =>
    request<Record<string, unknown>[]>(`/api/v1/pending/${channel}${q({ theme })}`),
  run: () => request<{ started: boolean }>("/api/v1/run", { method: "POST" }),
  runStatus: () => request<Record<string, unknown>>("/api/v1/run/status"),
  publish: (article_id: number, channel: string, note = "") =>
    request<Record<string, unknown>>("/api/v1/publish", {
      method: "POST",
      body: JSON.stringify({ article_id, channel, note }),
    }),
  patchTheme: (article_id: number, theme_id: string) =>
    request<Record<string, unknown>>(`/api/v1/jobs/${article_id}/theme`, {
      method: "PATCH",
      body: JSON.stringify({ theme_id }),
    }),
  publishingStats: (days = 30, theme?: string) =>
    request<Record<string, unknown>>(`/api/v1/publishing/stats${q({ days, theme })}`),
  channelConfig: () => request<ChannelConfigOverview>("/api/v1/channel-config"),
  saveChannelAccounts: (site_code: string, channel_id: string, accounts: ChannelAccount[]) =>
    request<{ saved: number; accounts: ChannelAccount[] }>("/api/v1/channel-config/accounts", {
      method: "PUT",
      body: JSON.stringify({ site_code, channel_id, accounts }),
    }),
  deleteChannelAccount: (account_id: string) =>
    request<{ deleted: string }>(`/api/v1/channel-config/accounts/${account_id}`, {
      method: "DELETE",
    }),
  publisherOverview: () => request<Record<string, unknown>>("/api/v1/publisher/overview"),
  publisherPublish: (article_id: number, channel_id: string, account_id = "", dry_run = false) =>
    request<Record<string, unknown>>("/api/v1/publisher/publish", {
      method: "POST",
      body: JSON.stringify({ article_id, channel_id, account_id, dry_run }),
    }),
  publisherLoginCheck: (account_id: string) =>
    request<Record<string, unknown>>("/api/v1/publisher/login-check", {
      method: "POST",
      body: JSON.stringify({ account_id }),
    }),
};
