"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { getApiBase, googleLogin, login, register } from "@/lib/api";
import { setAuthSession } from "@/lib/auth";
import { GoogleOAuthProvider, GoogleLogin } from "@react-oauth/google";

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState("login"); // 'login' or 'register'
  
  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");

  const apiBase = useMemo(() => getApiBase(), []);
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

  async function handleNativeAuth(e) {
    e.preventDefault();
    if (!userId.trim() || !password.trim()) {
      setError("Username and password are required.");
      return;
    }
    
    setLoading(true);
    setError("");
    try {
      if (mode === "register") {
        await register({ user_id: userId, password, tier: "free" });
        // Automatically login after successful registration
      }
      const data = await login({ user_id: userId, password });
      
      setAuthSession({
        token: data.token,
        userId: data.user_id,
        tier: data.tier,
        sessionExpiresAt: data.session_expires_at,
      });
      router.replace("/chat");
    } catch (err) {
      setError(err.message || "Authentication failed. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleSuccess(credentialResponse) {
    setLoading(true);
    setError("");
    try {
      const data = await googleLogin(credentialResponse.credential);
      setAuthSession({
        token: data.token,
        userId: data.user_id,
        tier: data.tier,
        sessionExpiresAt: data.session_expires_at,
      });
      router.replace("/chat");
    } catch (err) {
      setError(err.message || "Google authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <GoogleOAuthProvider clientId={clientId}>
      <main className="page login-page">
        <section className="login-card">
          <div style={{ textAlign: "center", marginBottom: "8px" }}>
            <h1 style={{ fontSize: "1.8rem", color: "#4a3520", marginBottom: "4px" }}>Paragi Studio</h1>
            <p style={{ fontSize: "0.9rem" }}>Your graph-native cognition engine.</p>
          </div>

          <div className="mode-switch">
            <button 
              type="button" 
              className={mode === "login" ? "active" : ""} 
              onClick={() => { setMode("login"); setError(""); }}
            >
              Sign In
            </button>
            <button 
              type="button" 
              className={mode === "register" ? "active" : ""} 
              onClick={() => { setMode("register"); setError(""); }}
            >
              Create Account
            </button>
          </div>

          {error && <div className="panel-error" style={{ margin: "4px 0" }}>{error}</div>}

          <form onSubmit={handleNativeAuth} style={{ display: "grid", gap: "12px" }}>
            <div style={{ display: "grid", gap: "4px" }}>
              <label htmlFor="userId">Username</label>
              <input 
                id="userId"
                type="text" 
                placeholder="Enter your username"
                value={userId}
                onChange={e => setUserId(e.target.value)}
                disabled={loading}
              />
            </div>
            
            <div style={{ display: "grid", gap: "4px" }}>
              <label htmlFor="password">Password</label>
              <input 
                id="password"
                type="password" 
                placeholder="Enter your password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                disabled={loading}
              />
            </div>

            <button type="submit" className="primary" disabled={loading} style={{ marginTop: "8px" }}>
              {loading ? "Authenticating..." : (mode === "login" ? "Sign In" : "Register")}
            </button>
          </form>

          <div style={{ display: "flex", alignItems: "center", gap: "12px", margin: "12px 0" }}>
            <hr style={{ flex: 1, borderTop: "1px solid rgba(215, 194, 160, 0.5)" }} />
            <span style={{ fontSize: "0.8rem", color: "var(--muted)" }}>OR</span>
            <hr style={{ flex: 1, borderTop: "1px solid rgba(215, 194, 160, 0.5)" }} />
          </div>

          <div style={{ display: "flex", justifyContent: "center" }}>
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => setError("Google login widget failed to load.")}
              useOneTap
              theme="outline"
              shape="pill"
            />
          </div>

          <small style={{ marginTop: "16px", display: "block", textAlign: "center", color: "#8b765c" }}>
            API Endpoint: {apiBase}
          </small>
        </section>
      </main>
    </GoogleOAuthProvider>
  );
}
