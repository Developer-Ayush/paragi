"use client";

import { useEffect, useMemo, useState, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Send, 
  Network, 
  History, 
  LogOut, 
  Plus, 
  Zap, 
  ShieldCheck,
  BrainCircuit,
  PanelLeftClose,
  PanelLeftOpen,
  MessageSquare,
  Compass,
  Activity
} from "lucide-react";
import GraphPanel from "@/components/GraphPanel";
import Logo from "@/components/Logo";
import ThemeToggle from "@/components/ThemeToggle";
import { useTheme } from "@/components/ThemeProvider";
import { getAuthSession, clearAuthSession } from "@/lib/auth";
import { createSession, loadSessions, saveSessions, upsertSession } from "@/lib/chat-storage";
import { health, llmStatus, query, session, userProfile, getApiBase } from "@/lib/api";
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
  const [profile, setProfile] = useState(null);
  const [checking, setChecking] = useState(true);
  const { theme, setTheme } = useTheme();
  const pendingQueryRef = useRef("");
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState("");
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [status, setStatus] = useState("Operational");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [meta, setMeta] = useState({ health: "-", llm: "-" });
  const [refreshSignal, setRefreshSignal] = useState(0);

  const activeSession = useMemo(
    () => sessions.find((item) => item.id === activeId) || null,
    [sessions, activeId],
  );

  const { lastMessage } = useWebSocket(auth?.userId, getApiBase());

  useEffect(() => {
    if (!lastMessage || lastMessage.type !== "chat_update") return;
    const { chat_id, data } = lastMessage;
    setSessions(prev => {
      const sessionToUpdate = prev.find(s => s.id === chat_id);
      if (!sessionToUpdate) return prev;
      const exists = (sessionToUpdate.messages || []).some(m => m.meta?.history_record_id === data.history_record_id);
      if (exists) return prev;
      if (sending && data.input_text === pendingQueryRef.current) return prev;
      const botMsg = makeMessage("assistant", data.answer, {
        confidence: data.confidence,
        path: data.node_path,
        scope: data.scope,
        benefits_main_graph: data.benefits_main_graph,
        history_record_id: data.history_record_id,
        synced: true
      });
      const hasUserMsg = (sessionToUpdate.messages || []).some(m => m.role === "user" && m.text === data.input_text);
      let newMessages = [...(sessionToUpdate.messages || [])];
      if (!hasUserMsg) newMessages.push(makeMessage("user", data.input_text, { synced: true }));
      newMessages.push(botMsg);
      return prev.map(s => s.id === chat_id ? { ...s, messages: newMessages, updatedAt: Date.now() } : s);
    });
    refreshProfile();
  }, [lastMessage, sending]);

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
        setAuth({ token: local.token, userId: sessionData.user_id, tier: sessionData.tier });
        const existing = loadSessions(sessionData.user_id);
        if (existing.length === 0) {
          const first = createSession("Initial Protocol");
          setSessions([first]);
          setActiveId(first.id);
          router.replace(`?chatId=${first.id}`);
        } else {
          setSessions(existing);
          if (urlChatId && existing.some(s => s.id === urlChatId)) setActiveId(urlChatId);
          else {
            setActiveId(existing[0].id);
            router.replace(`?chatId=${existing[0].id}`);
          }
        }
        await Promise.all([refreshSystemMeta(), refreshProfile(sessionData.user_id)]);
      } catch (err) {
        clearAuthSession();
        router.replace("/login");
      } finally {
        if (!cancelled) setChecking(false);
      }
    }
    boot();
    return () => { cancelled = true; };
  }, [router, urlChatId]);

  useEffect(() => {
    if (auth?.userId) saveSessions(auth.userId, sessions);
  }, [auth, sessions]);

  async function refreshSystemMeta() {
    try {
      const [h, l] = await Promise.all([health(), llmStatus()]);
      setMeta({ health: h.store_kind, llm: l.model });
    } catch {
      setMeta({ health: "Offline", llm: "Offline" });
    }
  }

  async function refreshProfile(uid) {
    const targetUid = uid || auth?.userId;
    if (!targetUid) return;
    try {
      const data = await userProfile(targetUid);
      setProfile(data);
    } catch {}
  }

  function appendMessage(role, text, meta = null) {
    const msg = makeMessage(role, text, meta);
    setSessions((prev) => {
      return prev.map((s) => {
        if (s.id === activeId) {
          return { ...s, messages: [...(s.messages || []), msg], updatedAt: Date.now() };
        }
        return s;
      });
    });
    return msg.id;
  }

  function patchMessage(id, data) {
    setSessions((prev) => {
      return prev.map((s) => {
        if (s.id === activeId) {
          const newMessages = (s.messages || []).map((m) => (m.id === id ? { ...m, ...data } : m));
          return { ...s, messages: newMessages };
        }
        return s;
      });
    });
  }

  async function sendQuery() {
    const text = draft.trim();
    if (!text || sending || !auth?.userId) return;
    setDraft("");
    pendingQueryRef.current = text;
    setSending(true);
    setStatus("Traversing...");
    appendMessage("user", text);
    try {
      const data = await query({ text, user_id: auth.userId, scope: "auto", chat_id: activeId });
      const botMessageId = appendMessage("assistant", "", {
        confidence: data.confidence,
        path: data.node_path,
        scope: data.scope,
      });

      // Sleek streaming simulation
      const words = String(data.answer || "").split(" ");
      let currentText = "";
      for (const word of words) {
        currentText += (currentText ? " " : "") + word;
        patchMessage(botMessageId, { text: currentText });
        await sleep(15);
      }
      setStatus("Operational");
      setRefreshSignal((v) => v + 1);
      refreshProfile();
    } catch (err) {
      appendMessage("assistant", `Cognitive disruption: ${err.message}`);
      setStatus("Error");
    } finally {
      setSending(false);
      pendingQueryRef.current = "";
    }
  }

  if (checking) return (
    <div className="h-screen w-screen flex flex-col items-center justify-center bg-white dark:bg-stone-950">
      <Logo theme={theme} className="w-16 h-16 animate-pulse mb-8" />
      <div className="mono text-stone-400 animate-pulse">Initializing Paragi Core...</div>
    </div>
  );

  return (
    <div className="chat-layout font-serif">
      {/* LEFT RAIL */}
      <motion.aside
        initial={false}
        animate={{ width: sidebarOpen ? 280 : 0, opacity: sidebarOpen ? 1 : 0 }}
        className="card-container left-rail border-r border-stone-200 dark:border-stone-800"
      >
        <div className="p-6 flex items-center justify-between border-b border-stone-200 dark:border-stone-800">
          <Logo theme={theme} className="w-8" />
          <button onClick={() => setSidebarOpen(false)} className="text-stone-400 hover:text-stone-900 dark:hover:text-white">
            <PanelLeftClose size={18} />
          </button>
        </div>

        <div className="p-4 space-y-2 border-b border-stone-200 dark:border-stone-800">
          <button
            onClick={() => {
              const fresh = createSession("New Protocol");
              setSessions(p => upsertSession(p, fresh));
              setActiveId(fresh.id);
              router.push(`?chatId=${fresh.id}`);
            }}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg bg-stone-900 dark:bg-white text-white dark:text-stone-900 text-sm font-semibold shadow-sm hover:opacity-90"
          >
            <Plus size={18} /> New Session
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          <div className="px-3 py-2 text-[10px] font-mono text-stone-400 tracking-widest uppercase">Memory Clusters</div>
          {sessions.map(s => (
            <button
              key={s.id}
              onClick={() => { setActiveId(s.id); router.push(`?chatId=${s.id}`); }}
              className={`w-full text-left px-4 py-3 rounded-lg transition-all flex items-center gap-3 group ${s.id === activeId ? 'bg-stone-100 dark:bg-stone-900 text-stone-900 dark:text-white shadow-sm' : 'text-stone-500 hover:bg-stone-50 dark:hover:bg-stone-900/50'}`}
            >
              <MessageSquare size={16} className={s.id === activeId ? 'text-stone-900 dark:text-white' : 'text-stone-300 group-hover:text-stone-400'} />
              <div className="flex-1 truncate text-sm font-medium">{s.title}</div>
            </button>
          ))}
        </div>

        <div className="p-4 border-t border-stone-200 dark:border-stone-800 space-y-4">
          <div className="flex items-center justify-between px-2">
            <div className="flex items-center gap-2 text-stone-400">
              <Zap size={14} className="text-amber-500" />
              <span className="text-[10px] font-mono">{profile?.credit_balance ?? 0} Credits</span>
            </div>
            <div className="flex items-center gap-2 text-stone-400">
              <ShieldCheck size={14} className="text-stone-400" />
              <span className="text-[10px] font-mono">{profile?.tier}</span>
            </div>
          </div>
          <button
            onClick={() => { clearAuthSession(); router.replace("/login"); }}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg border border-stone-200 dark:border-stone-800 text-xs font-mono text-stone-500 hover:bg-stone-50 dark:hover:bg-stone-900 transition-colors"
          >
            <LogOut size={14} /> Terminate
          </button>
        </div>
      </motion.aside>

      {/* MAIN CHAT */}
      <main className="chat-main">
        <header className="h-16 border-b border-stone-200 dark:border-stone-800 flex items-center justify-between px-6 bg-white/80 dark:bg-stone-950/80 backdrop-blur-md sticky top-0 z-10">
          <div className="flex items-center gap-4">
            {!sidebarOpen && (
              <button onClick={() => setSidebarOpen(true)} className="text-stone-400 hover:text-stone-900 dark:hover:text-white">
                <PanelLeftOpen size={18} />
              </button>
            )}
            <h2 className="text-lg font-display flex items-center gap-2">
              <BrainCircuit size={20} className="text-red-600" />
              {activeSession?.title || "Active Reasoning"}
            </h2>
          </div>
          <div className="flex items-center gap-6">
            <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-stone-100 dark:bg-stone-900 border border-stone-200 dark:border-stone-800">
               <div className={`w-1.5 h-1.5 rounded-full ${status === 'Error' ? 'bg-red-500' : 'bg-emerald-500 animate-pulse'}`} />
               <span className="text-[10px] font-mono text-stone-500">{status}</span>
            </div>
            <ThemeToggle theme={theme} setTheme={setTheme} />
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-8 space-y-8 max-w-4xl mx-auto w-full">
          <AnimatePresence mode="popLayout">
            {activeSession?.messages.map((m) => (
              <motion.div
                key={m.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div className={`bubble ${m.role}`}>
                  <div className="bubble-meta">
                    <span>{m.role === 'user' ? 'Signal' : 'Inference'}</span>
                    <span>{new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                  <div className={`text-base leading-relaxed ${m.role === 'user' ? 'font-serif' : 'font-serif'}`}>
                    {m.text}
                  </div>
                  {m.meta?.path && m.meta.path.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-stone-100 dark:border-stone-800 flex items-center gap-3">
                      <Network size={12} className="text-red-600" />
                      <div className="text-[10px] font-mono text-stone-400 truncate">
                        {m.meta.path.join(' → ')}
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          {sending && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-start">
               <div className="bubble assistant">
                  <div className="bubble-meta">Resolving Semantic Paths...</div>
                  <div className="flex gap-1 py-2">
                    <div className="thinking-dot" style={{ animationDelay: '0ms' }} />
                    <div className="thinking-dot" style={{ animationDelay: '150ms' }} />
                    <div className="thinking-dot" style={{ animationDelay: '300ms' }} />
                  </div>
               </div>
            </motion.div>
          )}
          <div id="scroll-anchor" className="h-4" />
        </div>

        <footer className="p-6 bg-white dark:bg-stone-950 border-t border-stone-200 dark:border-stone-800 sticky bottom-0">
          <div className="max-w-4xl mx-auto relative group">
            <input
              value={draft}
              onChange={e => setDraft(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendQuery()}
              placeholder="Query the Collective Intelligence..."
              className="w-full pr-16 shadow-lg group-hover:ring-1 ring-stone-200 dark:ring-stone-800"
            />
            <button
              onClick={sendQuery}
              disabled={sending || !draft.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-md bg-stone-900 dark:bg-white text-white dark:text-stone-900 hover:opacity-90 disabled:bg-stone-100 dark:disabled:bg-stone-900 disabled:text-stone-400"
            >
              <Send size={18} />
            </button>
          </div>
          <div className="max-w-4xl mx-auto mt-4 flex justify-between px-2">
             <div className="text-[9px] font-mono text-stone-400 flex items-center gap-4">
                <span className="flex items-center gap-1"><Activity size={10} /> Latency: ~140ms</span>
                <span className="flex items-center gap-1"><Compass size={10} /> Mode: Relational</span>
             </div>
             <div className="text-[9px] font-mono text-stone-400 uppercase tracking-widest">Paragi AGI Protocol v11</div>
          </div>
        </footer>
      </main>

      {/* RIGHT RAIL */}
      <aside className="card-container right-rail border-l border-stone-200 dark:border-stone-800">
        <header className="h-16 flex items-center gap-3 px-6 border-b border-stone-200 dark:border-stone-800">
          <Network size={16} className="text-red-600" />
          <h3 className="mono text-[10px]">Cognitive Visualization</h3>
        </header>
        <div className="flex-1 overflow-hidden relative">
          <GraphPanel userId={auth?.userId} refreshSignal={refreshSignal} />
        </div>
        <div className="p-8 space-y-8 bg-stone-50/50 dark:bg-stone-900/20">
          <div>
            <h4 className="mono text-[9px] text-stone-400 mb-4">Intelligence Impact</h4>
            <div className="space-y-4">
              <div className="flex justify-between items-end">
                <span className="text-xs font-medium text-stone-500">Global Contributions</span>
                <span className="text-xl font-display text-red-600">{profile?.main_nodes_contributed ?? 0}</span>
              </div>
              <div className="w-full bg-stone-200 dark:bg-stone-800 h-1 rounded-full overflow-hidden">
                <div className="bg-red-600 h-full w-[15%]" />
              </div>
            </div>
          </div>

          <div className="pt-6 border-t border-stone-200 dark:border-stone-800">
             <h4 className="mono text-[9px] text-stone-400 mb-4">Core Telemetry</h4>
             <div className="space-y-3">
                <div className="flex justify-between text-[11px]">
                   <span className="text-stone-500">Storage</span>
                   <span className="font-mono text-stone-900 dark:text-stone-300">{meta.health}</span>
                </div>
                <div className="flex justify-between text-[11px]">
                   <span className="text-stone-500">LLM Brain</span>
                   <span className="font-mono text-stone-900 dark:text-stone-300 truncate max-w-[120px]">{meta.llm}</span>
                </div>
             </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
