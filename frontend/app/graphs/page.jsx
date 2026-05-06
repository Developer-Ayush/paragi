"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import GraphPanel from "@/components/GraphPanel";
import { historyByUser, session } from "@/lib/api";
import { clearAuthSession, getAuthSession } from "@/lib/auth";

export default function GraphsPage() {
  const router = useRouter();
  const [userId, setUserId] = useState("");
  const [records, setRecords] = useState([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function boot() {
      const local = getAuthSession();
      if (!local?.token || !local?.userId) {
        router.replace("/login");
        return;
      }
      try {
        const s = await session(local.token);
        if (cancelled) return;
        setUserId(s.user_id);
        const history = await historyByUser(s.user_id, 25, "all");
        if (cancelled) return;
        setRecords(history.items);
        setReady(true);
      } catch {
        clearAuthSession();
        router.replace("/login");
      }
    }

    boot();
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (!ready) {
    return <main className="page center">Loading graph dashboard...</main>;
  }

  return (
    <main className="page graphs-page">
      <div className="graphs-header">
        <h1>Graph Dashboard</h1>
        <div className="graphs-actions">
          <button onClick={() => router.push("/chat")}>Back to Chat</button>
        </div>
      </div>

      <div className="graphs-grid">
        <GraphPanel userId={userId} refreshSignal={0} />

        <section className="history-card">
          <h3>Recent Stored Queries</h3>
          {records.length === 0 && <p>No history yet.</p>}
          {records.map((item) => (
            <article key={item.id} className="history-row wide">
              <strong>{item.raw_text}</strong>
              <div>{item.frozen_snapshot}</div>
              <small>
                scope={item.scope} | domain={item.domain} | benefits_main_graph={String(item.benefits_main_graph)}
              </small>
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}
