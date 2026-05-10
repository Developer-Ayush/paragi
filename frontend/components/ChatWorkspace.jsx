"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import GraphPanel from "@/components/GraphPanel";
import Logo from "@/components/Logo";
import ThemeToggle from "@/components/ThemeToggle";
import { useTheme } from "@/components/ThemeProvider";
import { getAuthSession, clearAuthSession } from "@/lib/auth";
import { createSession, loadSessions, normalizeTitle, saveSessions, upsertSession, deleteSession } from "@/lib/chat-storage";
import { health, llmStatus, logout, query, session, queryHistoryEvolution, getApiBase } from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";

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
  const searchParams = useSearchParams();
  const urlChatId = searchParams.get("chatId");
  const [auth, setAuth] = useState(null);
  const [checking, setChecking] = useState(true);
  const { theme, setTheme } = useTheme();
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

  const { lastMessage, isConnected } = useWebSocket(auth?.userId, getApiBase());

  // Handle cross-session synchronization via WebSocket
  useEffect(() => {
    if (!lastMessage || lastMessage.type !== "chat_update") return;
    
    const { chat_id, data } = lastMessage;
    
    // If the message is for a different session, update that session in the background
    // If it's for the current session, append it (unless we are already handling it)
    setSessions(prev => {
      const sessionToUpdate = prev.find(s => s.id === chat_id);
      if (!sessionToUpdate) {
        // If session not found locally, we might need to fetch it or just ignore if it's new
        return prev;
      }

      // Check if this message (by history_record_id) already exists to avoid duplicates
      const exists = (sessionToUpdate.messages || []).some(m => m.meta?.history_record_id === data.history_record_id);
      if (exists) return prev;

      // Also check if we are currently "sending" the same query to avoid double-appending our own response
      // This is a bit heuristic but works for basic sync
      const isOurOwnResponse = sending && data.input_text === draft;
      if (isOurOwnResponse) return prev;

      const botMsg = makeMessage("assistant", data.answer, {
        confidence: data.confidence,
        path: data.node_path,
        scope: data.scope,
        benefits_main_graph: data.benefits_main_graph,
        llm_mode: data.llm_mode,
        query_mode: data.query_mode,
        history_record_id: data.history_record_id,
        synced: true
      });

      // We might also need to append the user message if it's missing (syncing from another device)
      const hasUserMsg = (sessionToUpdate.messages || []).some(m => m.role === "user" && m.text === data.input_text);
      let newMessages = [...(sessionToUpdate.messages || [])];
      
      if (!hasUserMsg) {
        newMessages.push(makeMessage("user", data.input_text, { synced: true }));
      }
      newMessages.push(botMsg);

      return prev.map(s => s.id === chat_id ? { ...s, messages: newMessages, updatedAt: Date.now() } : s);
    });
  }, [lastMessage, sending, draft]);

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
          router.replace(`?chatId=${first.id}`);
        } else {
          setSessions(existing);
          if (urlChatId && existing.some(s => s.id === urlChatId)) {
            setActiveId(urlChatId);
          } else {
            setActiveId(existing[0].id);
            router.replace(`?chatId=${existing[0].id}`);
          }
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
        const nextMeta = patch.meta ? { ...(message.meta || {}), ...patch.meta } : message.meta;
        return { ...message, ...patch, meta: nextMeta };
      });
      return {
        ...sessionItem,
        updatedAt: Date.now(),
        messages: nextMessages,
      };
    });
  }

  async function checkEvolution(messageId, recordId) {
    if (!recordId) return;
    try {
      const data = await queryHistoryEvolution(recordId);
      patchMessage(messageId, {
        meta: {
          evolution: {
            changed: data.changed,
            updated_answer: data.updated_answer,
            frozen_snapshot: data.frozen_snapshot,
            confidence_delta: data.confidence_delta,
            checkedAt: Date.now(),
          },
        },
      });
    } catch (err) {
      console.error("Evolution check failed:", err);
    }
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
        chat_id: activeId,
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
    switchSession(fresh.id);
    setStatus("New chat started");
  }

  function switchSession(id) {
    setActiveId(id);
    router.push(`?chatId=${id}`);
  }

  function handleDeleteSession(id, event) {
    event.stopPropagation();
    const updated = deleteSession(sessions, id);
    setSessions(updated);
    if (updated.length === 0) {
      const first = createSession("New chat");
      setSessions([first]);
      switchSession(first.id);
    } else if (activeId === id) {
      switchSession(updated[0].id);
    }
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
          <Logo theme={theme} className="rail-logo" />
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
            <div
              key={item.id}
              className={`session-item ${item.id === activeId ? "active" : ""}`}
              onClick={() => switchSession(item.id)}
              style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}
            >
              <div style={{ display: "grid", gap: "3px", overflow: "hidden" }}>
                <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.title}</span>
                <small>{new Date(item.updatedAt).toLocaleString()}</small>
              </div>
              <button
                className="mini-button"
                style={{ marginLeft: "6px", flexShrink: 0, padding: "3px 6px", background: "transparent", border: "1px solid #dcc6a6", color: "#b83232" }}
                onClick={(e) => handleDeleteSession(item.id, e)}
                title="Delete Chat"
              >
                ✕
              </button>
            </div>
          ))}
        </div>

      </aside>

      <section className="chat-main">
        <header className="chat-header">
          <strong>{activeSession?.title || "Chat"}</strong>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span>{status}</span>
            <ThemeToggle theme={theme} setTheme={setTheme} />
          </div>
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
                    {message.meta.history_record_id && (
                      <div style={{ marginTop: "8px" }}>
                        <button
                          className="mini-button"
                          onClick={() => checkEvolution(message.id, message.meta.history_record_id)}
                        >
                          Check for updates
                        </button>
                      </div>
                    )}
                    {message.meta.evolution && (
                      <div className="evolution-panel">
                        <strong>
                          {message.meta.evolution.changed
                            ? "✨ Paragi knows more now!"
                            : "Memory is consistent."}
                        </strong>
                        {message.meta.evolution.changed && (
                          <div className="diff-view">
                            <div className="diff-box">
                              <small>Then:</small>
                              <p>{message.meta.evolution.frozen_snapshot}</p>
                            </div>
                            <div className="diff-box">
                              <small>Now:</small>
                              <p>{message.meta.evolution.updated_answer}</p>
                            </div>
                          </div>
                        )}
                        <div className="evolution-meta">
                          Confidence Δ: {message.meta.evolution.confidence_delta.toFixed(3)}
                        </div>
                      </div>
                    )}
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
