export type ApiConfig = {
  base: string;
  token: string | null;
};

export type MetricItem = {
  period: string;
  revenue: number;
  expenses: number;
  cash_flow: number;
  online_share?: number;
};

export type ProfileResponse = {
  id: number;
  user_id: number;
  industry: string | null;
  revenue_band: string | null;
  employees: number | null;
  goals: string | null;
};

export type ProfileCreate = {
  user_email: string;
  password: string;
  industry?: string | null;
  revenue_band?: string | null;
  employees?: number | null;
  goals?: string | null;
};

export type ProductResponse = {
  id: number;
  name: string;
  type?: string | null;
  rate?: number | null;
  min_limit?: number | null;
  max_limit?: number | null;
  requirements_json?: unknown;
};

export type TokenResponse = {
  access_token: string;
  token_type?: string;
  expires_at?: string | null;
};

export type AccountResponse = {
  id: number;
  email: string;
  role: string;
  profile: {
    id: number;
    industry: string | null;
    revenue_band: string | null;
    employees: number | null;
    goals: string | null;
  } | null;
};

export type DashboardResponse = {
  profile_id: number;
  summary: unknown;
  stability_index: number;
};

export type RankResponse = {
  ranking_id: number;
  result: unknown;
};

export type RankRow = {
  productId: number;
  score: number;
  note: string;
};

function apiBase(): string {
  const env = import.meta.env as Record<string, string | undefined>;
  return (env.VITE_API_BASE || "http://127.0.0.1:8000").replace(/\/$/, "");
}

export function defaultApiBase(): string {
  return apiBase();
}

function joinUrl(base: string, path: string): string {
  return `${base.replace(/\/$/, "")}${path.startsWith("/") ? path : `/${path}`}`;
}

function errorMessage(data: unknown, status: number): string {
  if (!data || typeof data !== "object") return `Ошибка ${status}`;
  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const text = detail
      .map((item) => {
        if (!item || typeof item !== "object") return "";
        const row = item as { msg?: unknown; loc?: unknown };
        const msg = typeof row.msg === "string" ? row.msg : "";
        const loc = Array.isArray(row.loc) ? row.loc.filter((part) => part !== "body").join(".") : "";
        return loc && msg ? `${loc}: ${msg}` : msg;
      })
      .filter(Boolean)
      .join("; ");
    if (text) return text;
  }
  return `Ошибка ${status}`;
}

async function request<T>(config: ApiConfig, path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body != null) headers.set("Content-Type", "application/json");
  if (config.token) headers.set("Authorization", `Bearer ${config.token}`);
  let response: Response;
  try {
    response = await fetch(joinUrl(config.base, path), { ...init, headers });
  } catch {
    throw new Error("Нет связи с API. Проверьте, что бэкенд запущен.");
  }
  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text) as unknown;
    } catch {
      data = null;
    }
  }
  if (!response.ok) throw new Error(errorMessage(data, response.status));
  return data as T;
}

export function login(config: ApiConfig, body: { email: string; password: string }): Promise<TokenResponse> {
  return request(config, "/auth/login", { method: "POST", body: JSON.stringify(body) });
}

export function register(config: ApiConfig, body: { email: string; password: string }): Promise<TokenResponse> {
  return request(config, "/auth/register", { method: "POST", body: JSON.stringify(body) });
}

export function logout(config: ApiConfig): Promise<{ detail?: string }> {
  return request(config, "/auth/logout", { method: "POST" });
}

export function getMe(config: ApiConfig): Promise<AccountResponse> {
  return request(config, "/auth/me");
}

export function createProfile(config: ApiConfig, body: ProfileCreate): Promise<ProfileResponse> {
  return request(config, "/profile/", { method: "POST", body: JSON.stringify(body) });
}

export function uploadMetrics(
  config: ApiConfig,
  profileId: number,
  body: { metrics: MetricItem[] },
): Promise<{ count?: number }> {
  return request(config, `/metrics/${profileId}`, { method: "POST", body: JSON.stringify(body) });
}

export function getDashboard(config: ApiConfig, profileId: number): Promise<DashboardResponse> {
  return request(config, `/dashboard/${profileId}`);
}

export function listProducts(config: ApiConfig): Promise<ProductResponse[]> {
  return request(config, "/products/");
}

export function rankProducts(
  config: ApiConfig,
  body: { profile_id: number; products: number[] },
): Promise<RankResponse> {
  return request(config, "/rank/products", { method: "POST", body: JSON.stringify(body) });
}

export function createEvent(
  config: ApiConfig,
  body: { profile_id?: number | null; event_type: string; payload?: unknown },
): Promise<{ id?: number }> {
  return request(config, "/events/", { method: "POST", body: JSON.stringify(body) });
}

export function rub(value: number): string {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    maximumFractionDigits: 0,
  }).format(value);
}

export function readSummary(summary: unknown): string {
  if (typeof summary === "string") return summary;
  if (!summary || typeof summary !== "object") return "";
  const row = summary as Record<string, unknown>;
  if (typeof row.text === "string") return row.text;
  if (typeof row.message === "string") return row.message;
  const parts: string[] = [];
  if (typeof row.revenue === "number") parts.push(`выручка ${rub(row.revenue)}`);
  if (typeof row.expenses === "number") parts.push(`расходы ${rub(row.expenses)}`);
  if (typeof row.cash_flow === "number") parts.push(`поток ${rub(row.cash_flow)}`);
  if (typeof row.margin === "number") parts.push(`маржа ${Math.round(row.margin * 100)}%`);
  return parts.join(", ");
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function noteFrom(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    return value
      .map((item) => (typeof item === "string" ? item : ""))
      .filter(Boolean)
      .join(", ");
  }
  return "";
}

function unwrapRankList(result: unknown): unknown[] | null {
  if (Array.isArray(result)) return result;
  if (!result || typeof result !== "object") return null;
  const row = result as Record<string, unknown>;
  for (const key of ["result", "products", "ranking", "items", "scores"]) {
    if (Array.isArray(row[key])) return row[key] as unknown[];
  }
  return null;
}

export function readRanking(result: unknown): RankRow[] | null {
  const list = unwrapRankList(result);
  if (!list) return null;
  const rows: RankRow[] = [];
  for (const item of list) {
    if (!item || typeof item !== "object") continue;
    const row = item as Record<string, unknown>;
    const productId = asNumber(row.product_id ?? row.productId ?? row.id);
    if (productId == null) continue;
    const raw = asNumber(row.score ?? row.probability ?? row.proba) ?? 0;
    const score = raw >= 0 && raw <= 1 ? Math.round(raw * 100) : Math.round(raw);
    rows.push({
      productId,
      score,
      note: noteFrom(row.note ?? row.reason ?? row.explanation ?? row.factors),
    });
  }
  return rows;
}

export function requirementFacts(value: unknown): Array<{ label: string; value: string }> {
  if (typeof value === "string" && value.trim()) return [{ label: "Условия", value: value }];
  if (!value || typeof value !== "object" || Array.isArray(value)) return [];
  return Object.entries(value as Record<string, unknown>)
    .filter(([, item]) => item != null && item !== "")
    .map(([label, item]) => ({
      label,
      value: typeof item === "object" ? JSON.stringify(item) : String(item),
    }));
}
