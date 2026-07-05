import { useState } from 'react'
import type { FormEvent } from 'react'
import { motion } from 'framer-motion'
import { Lock, User, AlertCircle } from 'lucide-react'
import { authApi } from '../api'

function LeafIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z"/>
      <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>
    </svg>
  )
}

export default function LoginPage({ onLogin, onSwitchToRegister }: {
  onLogin: () => void
  onSwitchToRegister: () => void
}) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      const { data } = await authApi.login(username, password)
      localStorage.setItem('fv_token', data.access_token)
      onLogin()
    } catch { setError('Invalid username or password') }
    finally  { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-brand/5 rounded-full blur-[120px]"/>
      </div>
      <motion.div initial={{opacity:0,y:24}} animate={{opacity:1,y:0}} transition={{duration:0.4}}
        className="relative w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand/10 border border-brand/30 mb-4">
            <LeafIcon className="w-8 h-8 text-brand"/>
          </div>
          <h1 className="text-2xl font-bold text-white">FreshVision AI</h1>
          <p className="text-muted text-sm mt-1">Quality Inspection Platform</p>
        </div>
        <div className="card">
          <p className="text-xs text-muted mb-5 text-center">Sign in to your workspace</p>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="label block mb-1.5">Username</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted"/>
                <input value={username} onChange={e=>setUsername(e.target.value)}
                  className="w-full bg-surface-2 border border-surface-3 rounded-lg pl-9 pr-3 py-2.5 text-sm text-white focus:outline-none focus:border-brand/60 placeholder:text-muted"
                  placeholder="admin" required/>
              </div>
            </div>
            <div>
              <label className="label block mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted"/>
                <input type="password" value={password} onChange={e=>setPassword(e.target.value)}
                  className="w-full bg-surface-2 border border-surface-3 rounded-lg pl-9 pr-3 py-2.5 text-sm text-white focus:outline-none focus:border-brand/60 placeholder:text-muted"
                  placeholder="••••••••" required/>
              </div>
            </div>
            {error && (
              <div className="flex items-center gap-2 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0"/>{error}
              </div>
            )}
            <button type="submit" className="btn-primary w-full mt-2" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
          <p className="text-center text-xs text-muted mt-4">
            Don't have an account?{' '}
            <button onClick={onSwitchToRegister} className="text-brand hover:underline">Sign up</button>
          </p>
        </div>
      </motion.div>
    </div>
  )
}
