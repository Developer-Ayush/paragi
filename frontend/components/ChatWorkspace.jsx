"use client";

import { useEffect, useMemo, useState, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Send, 
  Cpu, 
  Network, 
  History, 
  LogOut, 
  Plus, 
  RefreshCw, 
  Zap, 
  ShieldCheck,
  BrainCircuit,
  Settings
} from "lucide-react";
import GraphPanel from "@/components/GraphPanel";
import Logo from "@/components/Logo";
import ThemeToggle from "@/components/ThemeToggle";
import { useTheme } from "@/components/ThemeProvider";
import { getAuthSession, clearAuthSession } from "@/lib/auth";
import { createSession, loadSessions, normalizeTitle, saveSessions, upsertSession, deleteSession } from "@/lib/chat-storage";
import { health, llmStatus, logout, query, session, queryHistoryEvolution, getApiBase, userProfile } from "@/lib/api";
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
  const [status, setStatus] = useState("System Ready");
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
          const first = createSession("Initial Sequence");
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
  }, [router]);

  useEffect(() => {
    if (auth?.userId) saveSessions(auth.userId, sessions);
  }, [auth, sessions]);

  async function refreshSystemMeta() {
    try {
      const [h, l] = await Promise.all([health(), llmStatus()]);
      setMeta({ health: h.store, llm: l.model });
    } catch {
      setMeta({ health: "offline", llm: "offline" });
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

  async function sendQuery() {
    const text = draft.trim();
    if (!text || sending || !auth?.userId) return;
    setDraft("");
    pendingQueryRef.current = text;
    setSending(true);
    setStatus("Tracing paths...");
    appendMessage("user", text);
    try {
      const data = await query({ text, user_id: auth.userId, scope: "auto", chat_id: activeId });
      const botMessageId = appendMessage("assistant", "", {
        confidence: data.confidence,
        path: data.node_path,
        scope: data.scope,
        benefits_main_graph: data.benefits_main_graph,
        history_record_id: data.history_record_id,
      });
      const words = String(data.answer || "").split(" ");
      let currentText = "";
      for (const word of words) {
        currentText += (currentText ? " " : "") + word;
        patchMessage(botMessageId, { text: currentText });
        await sleep(10);
      }
      setStatus("Result Anchored");
      setRefreshSignal((v) => v + 1);
      refreshProfile();
    } catch (err) {
      appendMessage("assistant", `Cognitive blockage: ${err.message}`);
      setStatus("Sequence Error");
    } finally {
      setSending(false);
      pendingQueryRef.current = "";
    }
  }

  if (checking) return <div className="page center mono" style={{color:'var(--accent)'}}>BOOTING COGNITIVE RUNTIME...</div>;

  return (
    <div className="chat-layout">
      {/* SIDEBAR */}
      <aside className="card-container left-rail">
        <div className="brand-box">
          <Logo theme={theme} className="rail-logo" />
        </div>
        
        <div className="meta-box mono">
          <div style={{display:'flex', alignItems:'center', gap:'8px'}}>
             <Zap size={14} color="var(--accent)" />
             <span>BALANCE: <strong>{profile?.credit_balance ?? 0}</strong></span>
          </div>
          <div style={{display:'flex', alignItems:'center', gap:'8px'}}>
             <ShieldCheck size={14} color="var(--secondary)" />
             <span>TIER: {profile?.tier?.toUpperCase()}</span>
          </div>
        </div>

        <div className="rail-actions mono" style={{display:'grid', gap:'8px', padding:'12px 24px'}}>
           <button className="flex items-center gap-2" onClick={() => {
               const fresh = createSession("New Sequence");
               setSessions(p => upsertSession(p, fresh));
               setActiveId(fresh.id);
               router.push(`?chatId=${fresh.id}`);
           }}>
             <Plus size={16} /> NEW SESSION
           </button>
           <button className="flex items-center gap-2" onClick={() => router.push("/graphs")}>
              <Network size={16} /> DATA EXPLORER
           </button>
        </div>

        <div className="chat-history-container" style={{flex:1, overflow:'hidden'}}>
           <div className="history-header mono" style={{padding:'12px 24px', fontSize:'11px', borderBottom:'1px solid var(--border)'}}>
              <History size={12} style={{marginRight:'8px'}}/> PREVIOUS STATES
           </div>
           <div className="chat-session-list" style={{padding:'8px 12px'}}>
              {sessions.map(s => (
                <motion.div 
                  key={s.id} 
                  initial={{opacity:0}} animate={{opacity:1}}
                  className={`session-item ${s.id === activeId ? 'active' : ''}`}
                  onClick={() => { setActiveId(s.id); router.push(`?chatId=${s.id}`); }}
                  style={{padding:'10px 14px', borderRadius:'8px', cursor:'pointer', marginBottom:'4px'}}
                >
                  <div className="mono" style={{fontSize:'13px', fontWeight:600}}>{s.title}</div>
                  <div className="mono" style={{fontSize:'9px', opacity:0.5}}>{new Date(s.updatedAt).toLocaleTimeString()}</div>
                </motion.div>
              ))}
           </div>
        </div>

        <div className="brand-box" style={{borderTop:'1px solid var(--border)', borderBottom:'none', padding:'16px'}}>
           <button onClick={() => { clearAuthSession(); router.replace("/login"); }} 
                   style={{width:'100%', display:'flex', alignItems:'center', justifyContent:'center', gap:'8px', background:'transparent', border:'1px solid var(--border)', color:'var(--muted)', padding:'8px', borderRadius:'8px', fontSize:'12px'}}>
              <LogOut size={14} /> SYSTEM LOGOUT
           </button>
        </div>
      </aside>

      {/* MAIN CHAT */}
      <section className="card-container chat-main">
        <header className="chat-header">
          <div style={{display:'flex', alignItems:'center', gap:'12px'}}>
             <BrainCircuit size={20} color="var(--accent)" />
             <h2 style={{fontSize:'1.3rem'}}>{activeSession?.title || "Active Reasoning"}</h2>
          </div>
          <div className="mono" style={{fontSize:'11px', display:'flex', gap:'20px', alignItems:'center'}}>
             <span style={{color:'var(--muted)'}}>{status.toUpperCase()}</span>
             <ThemeToggle theme={theme} setTheme={setTheme} />
          </div>
        </header>

        <div className="message-list">
          <AnimatePresence>
          {activeSession?.messages.map((m, idx) => (
            <motion.div 
              key={m.id} 
              initial={{opacity:0, y:10}}
              animate={{opacity:1, y:0}}
              className={`bubble ${m.role}`}
            >
              <div className="bubble-meta mono" style={{display:'flex', justifyContent:'space-between'}}>
                 <span>{m.role === 'user' ? 'SIGNAL' : 'INFERENCE'}</span>
                 <span>{new Date(m.timestamp).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span>
              </div>
              <div className="bubble-text">{m.text}</div>
              {m.meta?.path && m.meta.path.length > 0 && (
                <div className="mono" style={{fontSize:'9px', marginTop:'12px', padding:'6px 10px', background:'rgba(0,0,0,0.03)', borderRadius:'4px', color:'var(--muted)'}}>
                  TRAVERSAL: {m.meta.path.join(' → ')}
                </div>
              )}
            </motion.div>
          ))}
          </AnimatePresence>
          {sending && (
            <motion.div initial={{opacity:0}} animate={{opacity:1}} className="bubble assistant thinking">
              <div className="bubble-meta mono">ACTIVATING SEMANTIC CLUSTERS...</div>
              <div className="bubble-text">● ● ●</div>
            </motion.div>
          )}
          <div id="scroll-anchor" />
        </div>

        <div className="composer">
          <div style={{flex:1, position:'relative'}}>
             <input 
               value={draft}
               onChange={e => setDraft(e.target.value)}
               onKeyDown={e => e.key === 'Enter' && sendQuery()}
               placeholder="Enter concept or query..."
               style={{width:'100%', paddingRight:'40px'}}
             />
             <div className="mono" style={{position:'absolute', right:'12px', top:'50%', transform:'translateY(-50%)', fontSize:'9px', opacity:0.3}}>
               ↵
             </div>
          </div>
          <button onClick={sendQuery} disabled={sending}>
             <Send size={18} />
          </button>
        </div>
      </section>

      {/* RIGHT RAIL */}
      <aside className="card-container right-rail">
        <header className="panel-header" style={{display:'flex', alignItems:'center', gap:'8px'}}>
           <Network size={14} /> SEMANTIC ACTIVATION
        </header>
        <GraphPanel userId={auth?.userId} refreshSignal={refreshSignal} />
        
        <div style={{padding:'24px', borderTop:'1px solid var(--border)'}} className="mono">
           <h4 style={{fontSize:'10px', color:'var(--muted)', marginBottom:'16px', letterSpacing:'0.1em'}}>KNOWLEDGE IMPACT</h4>
           <div style={{display:'grid', gap:'12px'}}>
              <div style={{display:'flex', justifyContent:'space-between', fontSize:'12px'}}>
                 <span>Main Nodes:</span>
                 <strong style={{color:'var(--accent)'}}>{profile?.main_nodes_contributed ?? 0}</strong>
              </div>
              <div style={{display:'flex', justifyContent:'space-between', fontSize:'12px'}}>
                 <span>Domain Depth:</span>
                 <strong>{Object.keys(profile?.domain_nodes_contributed ?? {}).length} Fields</strong>
              </div>
              <div style={{display:'flex', justifyContent:'space-between', fontSize:'12px', marginTop:'8px', paddingTop:'8px', borderTop:'1px dashed var(--border)'}}>
                 <span>CORE HEALTH:</span>
                 <span style={{color:'var(--ok)'}}>{meta.health?.toUpperCase()}</span>
              </div>
           </div>
        </div>
      </aside>
    </div>
  );
}
