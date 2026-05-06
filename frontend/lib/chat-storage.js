const PREFIX = "paragi_chats_v1_";

function keyFor(userId) {
  return `${PREFIX}${userId}`;
}

export function loadSessions(userId) {
  if (typeof window === "undefined") return [];
  const raw = window.localStorage.getItem(keyFor(userId));
  if (!raw) return [];
  try {
    const sessions = JSON.parse(raw);
    return Array.isArray(sessions) ? sessions : [];
  } catch {
    return [];
  }
}

export function saveSessions(userId, sessions) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(keyFor(userId), JSON.stringify(sessions));
}

export function createSession(seedText = "New chat") {
  const now = Date.now();
  return {
    id: `chat_${now}_${Math.random().toString(36).slice(2, 8)}`,
    title: normalizeTitle(seedText),
    createdAt: now,
    updatedAt: now,
    messages: [],
  };
}

export function normalizeTitle(text) {
  const clean = String(text || "").trim();
  if (!clean) return "New chat";
  if (clean.length <= 36) return clean;
  return `${clean.slice(0, 36)}...`;
}

export function upsertSession(sessions, nextSession) {
  const items = [...sessions];
  const idx = items.findIndex((item) => item.id === nextSession.id);
  if (idx >= 0) {
    items[idx] = nextSession;
  } else {
    items.unshift(nextSession);
  }
  return items.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
}
