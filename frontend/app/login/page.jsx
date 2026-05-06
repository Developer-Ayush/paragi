"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { getApiBase, login, register } from "@/lib/api";
import { setAuthSession } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState("login");
  const [userId, setUserId] = useState("guest");
  const [password, setPassword] = useState("pass1234");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const apiBase = useMemo(() => getApiBase(), []);

  async function submit() {
    const cleanUser = userId.trim();
    if (!cleanUser || !password.trim()) {
      setError("User ID and password are required.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const payload = { user_id: cleanUser, password };
      const data = mode === "register" ? await register(payload) : await login(payload);
      setAuthSession({
        token: data.token,
        userId: data.user_id,
        tier: data.tier,
        sessionExpiresAt: data.session_expires_at,
      });
      router.replace("/chat");
    } catch (err) {
      setError(err.message || "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page login-page">
      <section className="login-card">
        <h1>Paragi Studio</h1>
        <p>Sign in to keep local chat sessions and graph memory views.</p>

        <div className="mode-switch">
          <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Login</button>
          <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>Register</button>
        </div>

        <label>User ID</label>
        <input value={userId} onChange={(event) => setUserId(event.target.value)} />

        <label>Password</label>
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") submit();
          }}
        />

        {error && <div className="panel-error">{error}</div>}

        <button className="primary" onClick={submit} disabled={loading}>
          {loading ? "Please wait..." : mode === "register" ? "Create account" : "Sign in"}
        </button>

        <small>Backend: {apiBase}</small>
      </section>
    </main>
  );
}
