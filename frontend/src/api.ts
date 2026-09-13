import type {
  Insured,
  NotifyRequest,
  ProactiveNotification,
  Rule,
  WeatherSnapshot,
} from "./types";

const API_BASE = import.meta.env.DEV ? "/api" : "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    let detail = `${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep status code */
    }
    throw new Error(`Erro na API (${path}): ${detail}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  weather: (latitude: number, longitude: number) =>
    request<WeatherSnapshot>(
      `/weather?latitude=${latitude}&longitude=${longitude}`,
    ),

  notify: (payload: NotifyRequest) =>
    request<ProactiveNotification[]>("/notify", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  insureds: () => request<Insured[]>("/insureds"),

  rules: () => request<Rule[]>("/rules"),
};
