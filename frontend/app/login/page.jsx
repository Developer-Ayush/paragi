"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
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
      setError("Credentials required.");
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

  return (
    <GoogleOAuthProvider clientId={clientId}>
      <main className="page center" style={{flexDirection:'column', gap:'40px'}}>
        <motion.div 
          initial={{opacity:0, y:-20}} 
          animate={{opacity:1, y:0}}
          style={{width:'100%', maxWidth:'420px'}}
        >
          <div style={{display:'flex', justifyContent:'flex-end', marginBottom:'20px'}}>
             <ThemeToggle theme={theme} setTheme={setTheme} />
          </div>

          <div className="card-container" style={{padding:'40px'}}>
            <Logo theme={theme} className="login-logo" style={{marginBottom:'32px'}} />
            
            <div className="mono" style={{textAlign:'center', fontSize:'11px', color:'var(--muted)', marginBottom:'32px', letterSpacing:'0.1em'}}>
               COGNITIVE ARCHITECTURE RUNTIME
            </div>

            {error && <div className="panel-error mono" style={{marginBottom:'20px', fontSize:'12px', padding:'10px', borderRadius:'8px', background:'var(--accent-soft)', border:'1px solid var(--accent-muted)', color:'var(--accent)'}}>{error}</div>}

            <form onSubmit={handleNativeAuth} style={{display:'grid', gap:'20px'}}>
               <div style={{display:'grid', gap:'8px'}}>
                  <label className="mono" style={{fontSize:'10px', opacity:0.6}}>TENANT_ID</label>
                  <input 
                    type="text" 
                    value={userId}
                    onChange={e => setUserId(e.target.value)}
                    placeholder="Username"
                    style={{padding:'12px', borderRadius:'8px', border:'1px solid var(--border)', background:'var(--bg-dark)', color:'var(--text)'}}
                  />
               </div>
               <div style={{display:'grid', gap:'8px'}}>
                  <label className="mono" style={{fontSize:'10px', opacity:0.6}}>ACCESS_KEY</label>
                  <input 
                    type="password" 
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="Password"
                    style={{padding:'12px', borderRadius:'8px', border:'1px solid var(--border)', background:'var(--bg-dark)', color:'var(--text)'}}
                  />
               </div>

               <button type="submit" disabled={loading} style={{background:'var(--accent)', color:'#fff', border:'none', padding:'14px', borderRadius:'8px', fontWeight:'bold', cursor:'pointer', marginTop:'10px'}}>
                  {loading ? "INITIALIZING..." : (mode === 'login' ? "SIGN IN" : "REGISTER")}
               </button>
            </form>

            <div style={{display:'flex', justifyContent:'center', gap:'16px', marginTop:'24px', fontSize:'13px'}}>
               <span style={{color:'var(--muted)'}}>{mode === 'login' ? "New to Paragi?" : "Already a tenant?"}</span>
               <button onClick={() => setMode(mode === 'login' ? 'register' : 'login')} style={{background:'none', border:'none', color:'var(--accent)', cursor:'pointer', fontWeight:'bold'}}>
                  {mode === 'login' ? "Register Account" : "Sign In"}
               </button>
            </div>

            <div style={{marginTop:'32px', borderTop:'1px solid var(--border)', paddingTop:'24px'}}>
               <GoogleLogin
                  onSuccess={res => console.log(res)}
                  onError={() => setError("Google auth failed")}
                  theme={theme === "dark" ? "filled_black" : "outline"}
                  shape="pill"
                  width="100%"
               />
            </div>
          </div>
          
          <div className="mono" style={{textAlign:'center', marginTop:'24px', fontSize:'10px', opacity:0.4}}>
             ENDPOINT: {apiBase}
          </div>
        </motion.div>
      </main>
    </GoogleOAuthProvider>
  );
}
