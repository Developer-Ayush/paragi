const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    cache: "no-store",
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const message = payload?.detail || payload?.message || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return payload;
}

export function getApiBase() {
  return API_BASE;
}

export function register(payload) {
  return request("/auth/register", { method: "POST", body: JSON.stringify(payload) });
}

export function login(payload) {
  return request("/auth/login", { method: "POST", body: JSON.stringify(payload) });
}

export function logout(token) {
  return request("/auth/logout", { method: "POST", body: JSON.stringify({ token }) });
}

export function session(token) {
  return request(`/auth/session?token=${encodeURIComponent(token)}`);
}

export function query(payload) {
  return request("/query", { method: "POST", body: JSON.stringify(payload) });
}

export function graphSummary({ scope, userId, nodeLimit = 80, edgeLimit = 180, minStrength = 0 }) {
  const params = new URLSearchParams({
    scope,
    user_id: userId,
    node_limit: String(nodeLimit),
    edge_limit: String(edgeLimit),
    min_strength: String(minStrength),
  });
  return request(`/graph/summary?${params.toString()}`);
}

export function userImpact(userId, limit = 40) {
  return request(`/users/${encodeURIComponent(userId)}/impact?limit=${limit}`);
}

export function historyByUser(userId, limit = 100, scope = "all") {
  const params = new URLSearchParams({ limit: String(limit), scope });
  return request(`/query/history/user/${encodeURIComponent(userId)}?${params.toString()}`);
}

export function health() {
  return request("/health");
}

export function llmStatus() {
  return request("/llm/status");
}
