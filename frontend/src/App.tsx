import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Leaf, ScanLine, History, BarChart3,
  LogOut, Menu, X, ChevronRight, Wifi, WifiOff, Activity
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { authApi, analyticsApi } from './api'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import InspectPage from './pages/InspectPage'
import HistoryPage from './pages/HistoryPage'
import AnalyticsPage from './pages/AnalyticsPage'

type Page = 'inspect' | 'history' | 'analytics'

const NAV = [
  { id: 'inspect' as Page,   label: 'Inspect',   icon: ScanLine,  desc: 'Run AI inspection' },
  { id: 'history' as Page,   label: 'History',   icon: History,   desc: 'Past inspections'  },
  { id: 'analytics' as Page, label: 'Analytics', icon: BarChart3, desc: 'Trends & reports'  },
]

function LiveStatus() {
  const { isError } = useQuery({
    queryKey: ['health'],
    queryFn: () =>
      fetch((import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/health').then(r => r.json()),
    refetchInterval: 10_000, retry: 1,
  })
  return isError
    ? <span className="flex items-center gap-1.5 text-xs text-red-400"><WifiOff className="w-3.5 h-3.5"/>API Offline</span>
    : <span className="flex items-center gap-1.5 text-xs text-brand"><Wifi className="w-3.5 h-3.5"/>API Online</span>
}

function MiniKpis() {
  const { data } = useQuery({
    queryKey: ['analytics', 7],
    queryFn: () => analyticsApi.summary(7).then(r => r.data),
    refetchInterval: 30_000,
  })
  if (!data) return null
  const rate = data.total_items ? ((data.rejected_count / data.total_items)*100).toFixed(0) : '0'
  return (
    <div className="mt-auto px-3 pb-4 space-y-2">
      <p className="label px-1">Last 7 days</p>
      {[
        { l:'Inspections', v:data.total_inspections, c:'text-brand' },
        { l:'Items Scanned', v:data.total_items, c:'text-sky-400' },
        { l:'Reject Rate', v:`${rate}%`, c: +rate>20?'text-red-400':'text-green-400' },
      ].map(s=>(
        <div key={s.l} className="flex justify-between px-2 py-1.5 rounded-lg bg-surface-2">
          <span className="text-xs text-muted">{s.l}</span>
          <span className={`text-xs font-mono font-semibold ${s.c}`}>{s.v}</span>
        </div>
      ))}
    </div>
  )
}

export default function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem('fv_token'))
  const [authScreen, setAuthScreen] = useState<'login' | 'register'>('login')
  const [page, setPage]     = useState<Page>('inspect')
  const [open, setOpen]     = useState(false)

  const { data: user } = useQuery({
    queryKey: ['me'],
    queryFn: () => authApi.me().then(r => r.data),
    enabled: authed, retry: 0,
  })

  if (!authed) {
    return authScreen === 'login'
      ? <LoginPage onLogin={() => setAuthed(true)} onSwitchToRegister={() => setAuthScreen('register')} />
      : <RegisterPage onRegister={() => setAuthed(true)} onSwitchToLogin={() => setAuthScreen('login')} />
  }

  const ActivePage = page==='inspect' ? InspectPage : page==='history' ? HistoryPage : AnalyticsPage

  return (
    <div className="min-h-screen bg-surface flex">
      {/* Mobile overlay */}
      <AnimatePresence>
        {open && (
          <motion.div initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}
            className="fixed inset-0 bg-black/60 z-20 lg:hidden"
            onClick={()=>setOpen(false)}/>
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <aside className={`fixed top-0 left-0 h-full w-60 bg-surface-1 border-r border-surface-3 z-30 flex flex-col
        transition-transform duration-300 lg:translate-x-0 ${open?'translate-x-0':'-translate-x-full lg:translate-x-0'}`}>

        {/* Brand */}
        <div className="px-4 pt-5 pb-4 border-b border-surface-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-brand/10 border border-brand/30 flex items-center justify-center">
              <Leaf className="w-4 h-4 text-brand"/>
            </div>
            <div>
              <p className="text-sm font-bold text-white leading-none">FreshVision</p>
              <p className="text-xs text-muted mt-0.5">AI Quality Platform</p>
            </div>
          </div>
        </div>

        {/* Nav items */}
        <nav className="px-3 py-4 space-y-1">
          <p className="label px-2 mb-3">Navigation</p>
          {NAV.map(item=>{
            const Icon = item.icon
            const active = page===item.id
            return (
              <button key={item.id}
                onClick={()=>{setPage(item.id);setOpen(false)}}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all group
                  ${active?'bg-brand/10 border border-brand/20':'text-muted hover:text-white hover:bg-surface-2'}`}>
                <Icon className={`w-4 h-4 flex-shrink-0 ${active?'text-brand':'group-hover:text-white'}`}/>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium ${active?'text-brand':''}`}>{item.label}</p>
                  <p className="text-xs text-muted truncate">{item.desc}</p>
                </div>
                {active && <ChevronRight className="w-3.5 h-3.5 text-brand"/>}
              </button>
            )
          })}
          <div className="pt-4 mt-2 border-t border-surface-3">
            <div className="px-2"><LiveStatus/></div>
          </div>
        </nav>

        <MiniKpis/>

        {/* User footer */}
        <div className="border-t border-surface-3 px-3 py-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-brand/10 border border-brand/20 flex items-center justify-center text-brand text-xs font-bold">
              {user?.username?.[0]?.toUpperCase()||'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white truncate">{user?.username||'…'}</p>
              <p className="text-xs text-muted capitalize">{user?.role||'inspector'}</p>
            </div>
            <button onClick={()=>{localStorage.removeItem('fv_token');setAuthed(false)}}
              className="p-1.5 rounded-lg text-muted hover:text-red-400 hover:bg-red-500/10 transition-colors">
              <LogOut className="w-3.5 h-3.5"/>
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 lg:ml-60 flex flex-col min-h-screen">
        <header className="sticky top-0 z-10 bg-surface/80 backdrop-blur-xl border-b border-surface-3 px-4 py-3 flex items-center gap-3">
          <button className="lg:hidden p-2 rounded-lg text-muted hover:text-white hover:bg-surface-2 transition-colors"
            onClick={()=>setOpen(s=>!s)}>
            {open ? <X className="w-5 h-5"/> : <Menu className="w-5 h-5"/>}
          </button>
          <p className="text-sm font-semibold text-white flex-1">
            {NAV.find(n=>n.id===page)?.label}
          </p>
          <Activity className="w-4 h-4 text-brand animate-pulse"/>
          <span className="text-xs text-muted hidden sm:block">Live</span>
        </header>

        <main className="flex-1 p-4 sm:p-6">
          <AnimatePresence mode="wait">
            <motion.div key={page}
              initial={{opacity:0, y:8}} animate={{opacity:1, y:0}}
              exit={{opacity:0, y:-8}} transition={{duration:0.2}}>
              <ActivePage/>
            </motion.div>
          </AnimatePresence>
        </main>

        <footer className="border-t border-surface-3 px-6 py-3 flex items-center justify-between">
          <p className="text-xs text-muted">FreshVision AI · v1.0.0</p>
          <p className="text-xs text-muted hidden sm:block">YOLOv8 · OpenCV · FastAPI · React</p>
        </footer>
      </div>
    </div>
  )
}
