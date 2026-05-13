"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Shield, 
  Globe, 
  Fingerprint,
  RefreshCw,
  LogIn,
  Mail
} from "lucide-react";
import Logo from "@/components/Logo";
import ThemeToggle from "@/components/ThemeToggle";
import { useTheme } from "@/components/ThemeProvider";
import { getApiBase, googleLogin } from "@/lib/api";
import { setAuthSession } from "@/lib/auth";
import { auth, googleProvider, signInWithPopup } from "@/lib/firebase";

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { theme, setTheme } = useTheme();
  const apiBase = useMemo(() => getApiBase(), []);

  async function handleFirebaseLogin() {
    if (!auth) {
      setError("Firebase not configured.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await signInWithPopup(auth, googleProvider);
      const idToken = await result.user.getIdToken();
      
      // Send Firebase token to our backend
      const data = await googleLogin(idToken);
      
      setAuthSession({
        token: data.token,
        userId: data.user_id,
        tier: data.tier,
      });
      router.replace("/chat");
    } catch (err) {
      console.error("Firebase Login Error:", err);
      if (err.code === 'auth/popup-closed-by-user') {
        setError("Sign-in cancelled.");
      } else if (err.code === 'auth/configuration-not-found') {
        setError("Firebase config missing.");
      } else {
        setError(err.message || "Authentication failed.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
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
      
      <div style={{ position: "absolute", top: "32px", right: "32px", zIndex: 100 }}>
        <ThemeToggle theme={theme} setTheme={setTheme} />
      </div>

      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        style={{ width: '100%', maxWidth: '440px', zIndex: 10, position: 'relative' }}
      >
        <div className="card-container" style={{
          padding: '64px 48px',
          border: '1px solid var(--border)',
          background: theme === 'dark' ? 'rgba(20, 20, 20, 0.8)' : 'rgba(255, 255, 255, 0.7)',
          backdropFilter: 'blur(24px)',
          boxShadow: '0 40px 100px rgba(0,0,0,0.15)',
          textAlign: 'center'
        }}>
          <header style={{ marginBottom: '48px' }}>
            <Logo theme={theme} className="login-logo" style={{ marginBottom: '24px', transform: 'scale(1.15)' }} />
            <motion.div 
              className="mono" 
              style={{ fontSize: '11px', color: 'var(--accent)', letterSpacing: '0.25em', fontWeight: 'bold' }}
            >
              PARAGI COGNITIVE RUNTIME
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
             <p style={{ color: 'var(--muted)', fontSize: '15px', marginBottom: '32px', lineHeight: '1.6' }}>
                Secure federated identity gateway. Select an account to authorize your runtime session.
             </p>
             
             <div style={{ display: 'flex', justifyContent: 'center', width: '100%' }}>
               <button 
                  onClick={handleFirebaseLogin}
                  disabled={loading}
                  style={{
                    width: '100%',
                    background: theme === 'dark' ? '#fff' : '#1a1a1a',
                    color: theme === 'dark' ? '#000' : '#fff',
                    border: 'none',
                    padding: '16px 24px',
                    borderRadius: '12px',
                    fontWeight: '700',
                    fontSize: '15px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '12px',
                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                  }}
               >
                 {loading ? (
                    <RefreshCw className="animate-spin" size={20} />
                 ) : (
                    <>
                      <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" width="20" height="20" alt="G" />
                      <span>SIGN IN WITH GOOGLE</span>
                    </>
                 )}
               </button>
             </div>
          </div>

          <div style={{ borderTop: '1px solid var(--border)', paddingTop: '32px' }}>
             <div className="mono" style={{ fontSize: '10px', opacity: 0.4, textAlign: 'center' }}>
                SECURED_VIA_FIREBASE_AUTH
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
              <span>ENDPOINT: {apiBase}</span>
           </div>
           <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
              <Fingerprint size={10} />
              <span>STABLE_BUILD: v2.5.1-FIREBASE</span>
           </div>
        </div>
      </motion.div>
    </main>
  );
}
