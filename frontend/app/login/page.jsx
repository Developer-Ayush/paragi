"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Shield, 
  Key, 
  User, 
  ArrowRight, 
  Globe, 
  Fingerprint,
  RefreshCw,
  LogIn
} from "lucide-react";
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
            padding: '56px 48px',
            border: '1px solid var(--border)',
            background: theme === 'dark' ? 'rgba(20, 20, 20, 0.8)' : 'rgba(255, 255, 255, 0.7)',
            backdropFilter: 'blur(24px)',
            boxShadow: '0 40px 100px rgba(0,0,0,0.15)',
            textAlign: 'center'
          }}>
            <header style={{ marginBottom: '48px' }}>
              <Logo theme={theme} className="login-logo" style={{ marginBottom: '24px', transform: 'scale(1.15)' }} />
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
                className="mono" 
                style={{ fontSize: '11px', color: 'var(--accent)', letterSpacing: '0.25em', fontWeight: 'bold' }}
              >
                SECURE COGNITIVE ACCESS
              </motion.div>
            </header>

            <AnimatePresence mode="wait">
              {error && (
                <motion.div 
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="mono" 
                  style={{
                    marginBottom: '32px',
                    fontSize: '12px',
                    padding: '12px 16px',
                    borderRadius: '8px',
                    background: 'rgba(192, 57, 43, 0.1)',
                    border: '1px solid var(--accent)',
                    color: 'var(--accent)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '10px'
                  }}
                >
                  <Shield size={16} /> {error.toUpperCase()}
                </motion.div>
              )}
            </AnimatePresence>

            <div style={{ marginBottom: '40px' }}>
               <p style={{ color: 'var(--muted)', fontSize: '15px', marginBottom: '32px' }}>
                  Authorize your session via the Federated Identity Gateway to access the Paragi Cognitive Runtime.
               </p>
               
               <div style={{ display: 'flex', justifyContent: 'center', width: '100%' }}>
                 {loading ? (
                   <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
                      <RefreshCw className="animate-spin" size={32} color="var(--accent)" />
                      <span className="mono" style={{ fontSize: '10px', opacity: 0.6 }}>VERIFYING IDENTITY...</span>
                   </div>
                 ) : (
                   <GoogleLogin
                      onSuccess={handleGoogleSuccess}
                      onError={() => setError("Federated link failed.")}
                      useOneTap
                      theme={theme === "dark" ? "filled_black" : "outline"}
                      shape="rectangular"
                      width="320"
                   />
                 )}
               </div>
            </div>

            <div style={{ borderTop: '1px solid var(--border)', paddingTop: '32px' }}>
               <div className="mono" style={{ fontSize: '10px', opacity: 0.4, textAlign: 'center' }}>
                  GATEWAY_SECURED_BY_GOOGLE_TLS
               </div>
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
