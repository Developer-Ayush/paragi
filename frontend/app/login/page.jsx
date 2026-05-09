"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { getApiBase, googleLogin } from "@/lib/api";
import { setAuthSession } from "@/lib/auth";
import { GoogleOAuthProvider, GoogleLogin } from "@react-oauth/google";

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const apiBase = useMemo(() => getApiBase(), []);
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

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
          <h1>Paragi Studio</h1>
          <p>Sign in to keep local chat sessions and graph memory views.</p>

          {error && <div className="panel-error">{error}</div>}

          <div style={{ marginTop: "2rem", display: "flex", justifyContent: "center" }}>
            {loading ? (
              <p>Signing in...</p>
            ) : (
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={() => setError("Google login widget failed to load or connect.")}
                useOneTap
              />
            )}
          </div>

          <small style={{ marginTop: "2rem", display: "block" }}>Backend: {apiBase}</small>
          {!clientId && (
            <small style={{ color: "red", display: "block", marginTop: "0.5rem" }}>
              Missing NEXT_PUBLIC_GOOGLE_CLIENT_ID in environment!
            </small>
          )}
        </section>
      </main>
    </GoogleOAuthProvider>
  );
}
