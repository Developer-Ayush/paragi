"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Logo from "@/components/Logo";
import ThemeToggle from "@/components/ThemeToggle";
import { useTheme } from "@/components/ThemeProvider";
import { getApiBase, googleLogin, login, register } from "@/lib/api";
import { setAuthSession } from "@/lib/auth";
import { GoogleOAuthProvider, GoogleLogin } from "@react-oauth/google";

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState("login"); // 'login' or 'register'
  const { theme, setTheme } = useTheme();
  
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
        <div style={{ position: "absolute", top: "24px", right: "24px", zIndex: 100 }}>
          <ThemeToggle theme={theme} setTheme={setTheme} />
        </div>
        
        <section className="login-card">
          <header className="login-header">
            <Logo theme={theme} className="login-logo" />
            <p>Your graph-native cognition engine.</p>
          </header>

          <nav className="mode-switch">
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
          </nav>

          {error && <div className="panel-error" style={{ marginBottom: "20px" }}>{error}</div>}

          <form onSubmit={handleNativeAuth} className="auth-form">
            <div className="form-group">
              <label htmlFor="userId">Username</label>
              <input 
                id="userId"
                type="text" 
                placeholder="Enter your username"
                value={userId}
                onChange={e => setUserId(e.target.value)}
                disabled={loading}
                autoComplete="username"
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input 
                id="password"
                type="password" 
                placeholder="Enter your password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                disabled={loading}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
              />
            </div>

            <button type="submit" className="primary" disabled={loading}>
              {loading ? "Authenticating..." : (mode === "login" ? "Sign In" : "Register")}
            </button>
          </form>

          <div className="divider">
            <hr />
            <span>OR</span>
            <hr />
          </div>

          <div style={{ display: "flex", justifyContent: "center", width: "100%" }}>
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => setError("Google login widget failed to load.")}
              useOneTap
              theme={theme === "dark" ? "filled_black" : "outline"}
              shape="pill"
              width="100%"
            />
          </div>

          <div className="api-hint">
            API: {apiBase}
          </div>
        </section>
      </main>
    </GoogleOAuthProvider>
  );
}
