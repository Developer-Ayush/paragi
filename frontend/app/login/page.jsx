"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, Key, User, ArrowRight, Globe, Fingerprint } from "lucide-react";
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
  const [mode, setMode] = useState("login");
  const { theme, setTheme } = useTheme();
  
  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");

  const apiBase = useMemo(() => getApiBase(), []);
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

  async function handleNativeAuth(e) {
    e.preventDefault();
    if (!userId.trim() || !password.trim()) {
      setError("Identification required.");
      return;
    }
    
    setLoading(true);
    setError("");
    try {
      if (mode === "register") {
        await register({ user_id: userId, password, tier: "free" });
      }
      const data = await login({ user_id: userId, password });
      
      setAuthSession({
        token: data.token,
        userId: data.user_id,
        tier: data.tier,
      });
      router.replace("/chat");
    } catch (err) {
      setError(err.message || "Authentication failed.");
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
      });
      router.replace("/chat");
    } catch (err) {
      setError(err.message || "Identity verification failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <GoogleOAuthProvider clientId={clientId}>
      <main className="page center" style={{
        position: 'relative',
        overflow: 'hidden',
        background: theme === 'dark' ? '#050505' : '#faf9f7',
        perspective: '1000px'
      }}>
        {/* Background Decorative Elements */}
        <div style={{
          position: 'absolute',
          top: '-10%',
          left: '-10%',
          width: '40%',
          height: '40%',
          background: 'radial-gradient(circle, var(--accent-soft) 0%, transparent 70%)',
          filter: 'blur(80px)',
          opacity: 0.4,
          zIndex: 0
        }} />
        <div style={{
          position: 'absolute',
          bottom: '-10%',
          right: '-10%',
          width: '50%',
          height: '50%',
          background: 'radial-gradient(circle, var(--secondary) 0%, transparent 70%)',
          filter: 'blur(100px)',
          opacity: 0.2,
          zIndex: 0
        }} />

        <div style={{ position: "absolute", top: "32px", right: "32px", zIndex: 100 }}>
          <ThemeToggle theme={theme} setTheme={setTheme} />
        </div>

        <motion.div 
          initial={{ opacity: 0, scale: 0.95, rotateX: 10 }}
          animate={{ opacity: 1, scale: 1, rotateX: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          style={{ width: '100%', maxWidth: '480px', zIndex: 10, position: 'relative' }}
        >
          <div className="card-container" style={{
            padding: '48px',
            border: '1px solid var(--border)',
            background: theme === 'dark' ? 'rgba(20, 20, 20, 0.8)' : 'rgba(255, 255, 255, 0.7)',
            backdropFilter: 'blur(20px)',
            boxShadow: '0 30px 60px rgba(0,0,0,0.12)',
          }}>
            <header style={{ textAlign: 'center', marginBottom: '40px' }}>
              <Logo theme={theme} className="login-logo" style={{ marginBottom: '24px', transform: 'scale(1.1)' }} />
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
                className="mono" 
                style={{ fontSize: '11px', color: 'var(--accent)', letterSpacing: '0.2em', fontWeight: 'bold' }}
              >
                SECURE COGNITIVE ACCESS
              </motion.div>
            </header>

            <AnimatePresence mode="wait">
              {error && (
                <motion.div 
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="mono" 
                  style={{
                    marginBottom: '24px',
                    fontSize: '12px',
                    padding: '12px 16px',
                    borderRadius: '8px',
                    background: 'rgba(192, 57, 43, 0.1)',
                    border: '1px solid var(--accent)',
                    color: 'var(--accent)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px'
                  }}
                >
                  <Shield size={16} /> {error.toUpperCase()}
                </motion.div>
              )}
            </AnimatePresence>

            <form onSubmit={handleNativeAuth} style={{ display: 'grid', gap: '24px' }}>
              <div style={{ display: 'grid', gap: '10px' }}>
                <label className="mono" style={{ fontSize: '10px', opacity: 0.5, display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <User size={12} /> TENANT_IDENTIFIER
                </label>
                <div style={{ position: 'relative' }}>
                  <input 
                    type="text" 
                    value={userId}
                    onChange={e => setUserId(e.target.value)}
                    placeholder="Enter Username"
                    style={{
                      width: '100%',
                      padding: '14px 16px',
                      borderRadius: '10px',
                      border: '1px solid var(--border)',
                      background: 'var(--bg)',
                      color: 'var(--text)',
                      fontSize: '15px',
                      transition: 'all 0.3s'
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gap: '10px' }}>
                <label className="mono" style={{ fontSize: '10px', opacity: 0.5, display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Key size={12} /> CRYPTOGRAPHIC_KEY
                </label>
                <input 
                  type="password" 
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Enter Password"
                  style={{
                    width: '100%',
                    padding: '14px 16px',
                    borderRadius: '10px',
                    border: '1px solid var(--border)',
                    background: 'var(--bg)',
                    color: 'var(--text)',
                    fontSize: '15px',
                    transition: 'all 0.3s'
                  }}
                />
              </div>

              <button 
                type="submit" 
                disabled={loading}
                style={{
                  background: 'var(--accent)',
                  color: '#fff',
                  border: 'none',
                  padding: '16px',
                  borderRadius: '10px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  marginTop: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '12px',
                  boxShadow: '0 10px 20px var(--accent-soft)',
                  transition: 'all 0.3s'
                }}
              >
                {loading ? (
                  <RefreshCw className="animate-spin" size={20} />
                ) : (
                  <>
                    <span>{mode === 'login' ? "INITIALIZE SESSION" : "REGISTER TENANT"}</span>
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
            </form>

            <div style={{ textAlign: 'center', marginTop: '24px' }}>
              <button 
                onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--muted)',
                  fontSize: '13px',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  textUnderlineOffset: '4px'
                }}
              >
                {mode === 'login' ? "Create a new cognitive identity" : "Sign in with existing credentials"}
              </button>
            </div>

            <div style={{ marginTop: '40px', borderTop: '1px solid var(--border)', paddingTop: '32px' }}>
               <div className="mono" style={{ fontSize: '10px', opacity: 0.4, textAlign: 'center', marginBottom: '20px' }}>
                  FEDERATED IDENTITY GATEWAY
               </div>
               <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={() => setError("Federated link failed.")}
                  useOneTap
                  theme={theme === "dark" ? "filled_black" : "outline"}
                  shape="rectangular"
                  width="100%"
               />
            </div>
          </div>
          
          <div className="mono" style={{ 
            textAlign: 'center', 
            marginTop: '32px', 
            fontSize: '10px', 
            opacity: 0.3,
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}>
             <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <Globe size={10} /> 
                <span>RUNTIME_ENDPOINT: {apiBase}</span>
             </div>
             <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <Fingerprint size={10} />
                <span>BUILD_VER: 2.4.0-PARAGI</span>
             </div>
          </div>
        </motion.div>
      </main>
    </GoogleOAuthProvider>
  );
}
