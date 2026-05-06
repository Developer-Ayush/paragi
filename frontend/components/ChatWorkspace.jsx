"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import GraphPanel from "@/components/GraphPanel";
import { getAuthSession, clearAuthSession } from "@/lib/auth";
import { createSession, loadSessions, normalizeTitle, saveSessions, upsertSession } from "@/lib/chat-storage";
import { health, llmStatus, logout, query, session } from "@/lib/api";

function makeMessage(role, text, meta = null) {
  return {
    id: `${role}_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
    role,
    text,
    meta,
    timestamp: Date.now(),
  };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export default function ChatWorkspace() {
  const router = useRouter();
  const [auth, setAuth] = useState(null);
  const [checking, setChecking] = useState(true);
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState("");
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [status, setStatus] = useState("Ready");
  const [meta, setMeta] = useState({ health: "-", llm: "-" });
  const [refreshSignal, setRefreshSignal] = useState(0);

  const activeSession = useMemo(
    () => sessions.find((item) => item.id === activeId) || null,
    [sessions, activeId],
  );

  const messages = activeSession?.messages || [];

  useEffect(() => {
    let cancelled = false;

    async function boot() {
      const local = getAuthSession();
      if (!local?.token || !local?.userId) {
        router.replace("/login");
        return;
      }

      try {
        const sessionData = await session(local.token);
        if (cancelled) return;
        const normalized = {
          token: local.token,
          userId: sessionData.user_id,
          tier: sessionData.tier,
          sessionExpiresAt: sessionData.session_expires_at,
        };
        setAuth(normalized);

        const existing = loadSessions(sessionData.user_id);
        if (existing.length === 0) {
          const first = createSession("New chat");
          setSessions([first]);
          setActiveId(first.id);
        } else {
          setSessions(existing);
          setActiveId(existing[0].id);
        }

        await refreshSystemMeta();
      } catch {
        clearAuthSession();
        router.replace("/login");
        return;
      } finally {
        if (!cancelled) setChecking(false);
      }
    }

    boot();
    return () => {
      cancelled = true;
    };
  }, [router]);

  useEffect(() => {
    if (!auth?.userId) return;
    saveSessions(auth.userId, sessions);
  }, [auth, sessions]);

  async function refreshSystemMeta() {
    try {
      const [h, l] = await Promise.all([health(), llmStatus()]);
      setMeta({
        health: `${h.store} | ${h.persistent_memory ? "persistent" : "memory-only"}`,
        llm: `${l.backend}/${l.model} | policy=${l.policy} | ${l.reachable ? "reachable" : "offline"}`,
      });
    } catch {
      setMeta({ health: "offline", llm: "offline" });
    }
  }

  function withActiveSession(mutator) {
    setSessions((prev) => {
      const current = prev.find((item) => item.id === activeId);
      if (!current) return prev;
      const updated = mutator(current);
      return upsertSession(prev, updated);
    });
  }

  function appendMessage(role, text, metaPayload = null) {
    const message = makeMessage(role, text, metaPayload);
    withActiveSession((sessionItem) => {
      const isFirstUserMessage = role === "user" && (sessionItem.messages || []).length === 0;
      return {
        ...sessionItem,
        title: isFirstUserMessage ? normalizeTitle(text) : sessionItem.title,
        updatedAt: Date.now(),
        messages: [...(sessionItem.messages || []), message],
      };
    });
    return message.id;
  }

  function patchMessage(messageId, patch) {
    withActiveSession((sessionItem) => {
      const nextMessages = (sessionItem.messages || []).map((message) => {
        if (message.id !== messageId) return message;
        return { ...message, ...patch };
      });
      return {
        ...sessionItem,
        updatedAt: Date.now(),
        messages: nextMessages,
      };
    });
  }

  async function sendQuery() {
    const text = draft.trim();
    if (!text || sending || !auth?.userId) return;

    setDraft("");
    setSending(true);
    setStatus("Thinking...");
    appendMessage("user", text);

    try {
      const data = await query({
        text,
        user_id: auth.userId,
        scope: "auto",
        domain: "auto",
      });

      const botMessageId = appendMessage("assistant", "", {
        confidence: data.confidence,
        path: data.node_path,
        scope: data.scope,
        benefits_main_graph: data.benefits_main_graph,
        llm_mode: data.llm_mode,
        query_mode: data.query_mode,
        history_record_id: data.history_record_id,
      });

      const words = String(data.answer || "").split(/\s+/).filter(Boolean);
      let partial = "";
      for (const word of words) {
        partial = partial ? `${partial} ${word}` : word;
        patchMessage(botMessageId, { text: partial });
        await sleep(12);
      }

      patchMessage(botMessageId, {
        text: data.answer,
        meta: {
          confidence: data.confidence,
          path: data.node_path,
          scope: data.scope,
          benefits_main_graph: data.benefits_main_graph,
          llm_mode: data.llm_mode,
          query_mode: data.query_mode,
          history_record_id: data.history_record_id,
        },
      });

      setStatus(`Answered · scope=${data.scope} · mode=${data.query_mode}`);
      setRefreshSignal((value) => value + 1);
    } catch (err) {
      appendMessage("assistant", `Request failed: ${err.message}`);
      setStatus("Request failed");
    } finally {
      setSending(false);
    }
  }

  function createNewChat() {
    const fresh = createSession("New chat");
    setSessions((prev) => upsertSession(prev, fresh));
    setActiveId(fresh.id);
    setStatus("New chat started");
  }

  async function doLogout() {
    if (auth?.token) {
      try {
        await logout(auth.token);
      } catch {
        // Ignore logout failures and clear local session anyway.
      }
    }
    clearAuthSession();
    router.replace("/login");
  }

  if (checking) {
    return <main className="page center">Checking session...</main>;
  }

  return (
    <main className="page chat-layout">
      <aside className="left-rail">
        <div className="brand-box">
          <h1>Paragi Studio</h1>
          <p>Local-first memory agent with chat and graph introspection.</p>
        </div>

        <div className="meta-box">
          <div>user: <strong>{auth?.userId}</strong></div>
          <div>tier: <strong>{auth?.tier}</strong></div>
          <div>health: {meta.health}</div>
          <div>llm: {meta.llm}</div>
        </div>

        <div className="rail-actions">
          <button onClick={createNewChat}>New Chat</button>
          <button
            onClick={async () => {
              await refreshSystemMeta();
              setRefreshSignal((value) => value + 1);
              setStatus("Refreshed");
            }}
          >
            Refresh
          </button>
          <button onClick={() => router.push("/graphs")}>Open Graphs</button>
          <button onClick={doLogout}>Logout</button>
        </div>

        <div className="chat-session-list">
          {sessions.map((item) => (
            <button
              key={item.id}
              className={`session-item ${item.id === activeId ? "active" : ""}`}
              onClick={() => setActiveId(item.id)}
            >
              <span>{item.title}</span>
              <small>{new Date(item.updatedAt).toLocaleString()}</small>
            </button>
          ))}
        </div>

      </aside>

      <section className="chat-main">
        <header className="chat-header">
          <strong>{activeSession?.title || "Chat"}</strong>
          <span>{status}</span>
        </header>

        <section className="message-list">
          {messages.length === 0 && (
            <article className="bubble assistant">
              <div className="role">Paragi</div>
              <div className="body">Ready. Ask any question. Personal facts auto-store in personal memory.</div>
            </article>
          )}
          {messages.map((message) => (
            <article key={message.id} className={`bubble ${message.role === "user" ? "user" : "assistant"}`}>
              <div className="role">{message.role === "user" ? "You" : "Paragi"}</div>
              <div className="body">{message.text}</div>
              {message.meta && (
                <details className="trace-details">
                  <summary>Details</summary>
                  <div className="trace">
                    <div>scope: {message.meta.scope} | query_mode: {message.meta.query_mode}</div>
                    <div>confidence: {Number(message.meta.confidence || 0).toFixed(3)} | llm_mode: {message.meta.llm_mode}</div>
                    <div>benefits_main_graph: {String(message.meta.benefits_main_graph)}</div>
                    <div>path: {(message.meta.path || []).join(" -> ") || "-"}</div>
                  </div>
                </details>
              )}
            </article>
          ))}
        </section>

        <footer className="composer">
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") sendQuery();
            }}
            placeholder="Ask anything..."
          />
          <button onClick={sendQuery} disabled={sending}>{sending ? "Sending..." : "Send"}</button>
        </footer>
      </section>

      <aside className="right-rail">
        <GraphPanel userId={auth?.userId} refreshSignal={refreshSignal} />
      </aside>
    </main>
  );
}
