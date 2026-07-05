import { useState, useRef, useCallback } from 'react'
import type { DragEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Zap, Thermometer, Droplets, Building2, Truck,
  CheckCircle2, XCircle, AlertTriangle,
  ChevronDown, ChevronUp, Loader2, ImageIcon, RefreshCw
} from 'lucide-react'
import { inspectApi } from '../api'
import type { InspectionResult, InspectionItem } from '../api'
import { GRADE_BG, FRESHNESS_BG, DECISION_BG } from '../utils'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function ScoreRing({ value, label, color }: { value: number; label: string; color: string }) {
  const r = 28, circ = 2 * Math.PI * r
  const offset = circ - (value / 100) * circ
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="72" height="72" viewBox="0 0 72 72">
        <circle cx="36" cy="36" r={r} fill="none" stroke="#252b40" strokeWidth="6"/>
        <circle cx="36" cy="36" r={r} fill="none" stroke={color} strokeWidth="6"
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
          transform="rotate(-90 36 36)" style={{transition:'stroke-dashoffset 0.8s ease'}}/>
        <text x="36" y="40" textAnchor="middle" fill="white" fontSize="13" fontWeight="600" fontFamily="monospace">
          {value.toFixed(0)}%
        </text>
      </svg>
      <span className="text-xs text-muted">{label}</span>
    </div>
  )
}

function DecisionIcon({ d }: { d: string }) {
  if (d === 'Accept')          return <CheckCircle2 className="w-5 h-5 text-brand"/>
  if (d === 'Reject')          return <XCircle className="w-5 h-5 text-red-400"/>
  if (d === 'Priority Dispatch') return <Zap className="w-5 h-5 text-sky-400"/>
  return <AlertTriangle className="w-5 h-5 text-amber-400"/>
}

function ItemCard({ item }: { item: InspectionItem }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <motion.div initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} className="card space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <DecisionIcon d={item.decision}/>
          <span className="font-semibold capitalize text-white">{item.product_type.replace(/_/g,' ')}</span>
          <span className="text-xs text-muted">#{item.item_id}</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <span className={`badge border ${GRADE_BG[item.quality_grade]||'bg-surface-3 text-slate-300'}`}>{item.quality_grade}</span>
          <span className={`badge ${FRESHNESS_BG[item.freshness_label]||'bg-surface-3 text-slate-300'}`}>{item.freshness_label}</span>
          <span className={`badge ${DECISION_BG[item.decision]||'bg-surface-3 text-slate-300'}`}>{item.decision}</span>
        </div>
      </div>

      <div className="flex gap-4 justify-around py-2">
        <ScoreRing value={item.quality_score}  label="Quality"   color="#22c55e"/>
        <ScoreRing value={item.freshness_pct}  label="Freshness" color="#3b82f6"/>
        <ScoreRing value={Math.max(0,100-item.defect_coverage_pct*2)} label="Condition" color="#f59e0b"/>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {[
          {l:'Defect Cover', v:`${item.defect_coverage_pct.toFixed(1)}%`},
          {l:'Shelf Life',   v:`${item.shelf_life_days}d`},
          {l:'Detection',    v:`${(item.detection_confidence*100).toFixed(0)}%`},
        ].map(s=>(
          <div key={s.l} className="bg-surface-2 rounded-lg p-2 text-center">
            <div className="text-xs text-muted mb-0.5">{s.l}</div>
            <div className="text-sm font-mono font-semibold text-white">{s.v}</div>
          </div>
        ))}
      </div>

      {item.defects.length > 0 && (
        <div>
          <p className="label mb-1.5">Detected Defects ({item.defects.length})</p>
          <div className="flex flex-wrap gap-1.5">
            {item.defects.map((d,i)=>(
              <span key={i} className="badge bg-red-500/10 text-red-400 border border-red-500/20">
                {d.label.replace(/_/g,' ')} · {(d.area_ratio*100).toFixed(1)}%
              </span>
            ))}
          </div>
        </div>
      )}

      <button onClick={()=>setExpanded(e=>!e)}
        className="flex items-center gap-1 text-xs text-muted hover:text-brand transition-colors">
        {expanded ? <ChevronUp className="w-3.5 h-3.5"/> : <ChevronDown className="w-3.5 h-3.5"/>}
        AI Explanation
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div initial={{height:0,opacity:0}} animate={{height:'auto',opacity:1}}
            exit={{height:0,opacity:0}} className="overflow-hidden">
            <div className="bg-surface-2 rounded-lg p-3 text-xs text-slate-300 leading-relaxed border border-surface-3">
              {item.explanation}
            </div>
            {item.decision_reasons.length > 0 && (
              <ul className="mt-2 space-y-1">
                {item.decision_reasons.map((r,i)=>(
                  <li key={i} className="flex items-start gap-1.5 text-xs text-muted">
                    <span className="text-brand mt-0.5">›</span>{r}
                  </li>
                ))}
              </ul>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function PipelineStep({ label, delay }: { label: string; delay: number }) {
  return (
    <motion.div initial={{opacity:0,x:-8}} animate={{opacity:1,x:0}} transition={{delay,duration:0.4}}
      className="flex items-center gap-2 text-xs text-muted">
      <div className="w-1.5 h-1.5 rounded-full bg-brand animate-pulse"/>
      {label}
    </motion.div>
  )
}

export default function InspectPage() {
  const [file,     setFile]     = useState<File|null>(null)
  const [preview,  setPreview]  = useState<string|null>(null)
  const [dragging, setDragging] = useState(false)
  const [loading,  setLoading]  = useState(false)
  const [result,   setResult]   = useState<InspectionResult|null>(null)
  const [error,    setError]    = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const [warehouseId, setWarehouseId] = useState('WH-001')
  const [supplierId,  setSupplierId]  = useState('SUP-FARM-A')
  const [temp,        setTemp]        = useState(6)
  const [humidity,    setHumidity]    = useState(85)

  const pick = useCallback((f: File) => {
    setFile(f); setPreview(URL.createObjectURL(f)); setResult(null); setError('')
  }, [])

  const onDrop = (e: DragEvent) => {
    e.preventDefault(); setDragging(false)
    const f = e.dataTransfer.files[0]; if (f) pick(f)
  }

  const run = async () => {
    if (!file) return
    setLoading(true); setError('')
    try {
      const { data } = await inspectApi.upload(file, {
        warehouse_id: warehouseId, supplier_id: supplierId,
        storage_temp_c: temp, storage_humidity_pct: humidity,
      })
      setResult(data)
    } catch (e: unknown) {
      const msg = (e as {response?:{data?:{detail?:string}}})?.response?.data?.detail
      setError(msg || 'Inspection failed — is the API server running?')
    } finally { setLoading(false) }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Quality Inspection</h1>
        <p className="text-muted text-sm mt-0.5">Upload a produce image to run the full AI pipeline</p>
      </div>

      <div className="grid lg:grid-cols-5 gap-6">
        {/* Left — upload + options */}
        <div className="lg:col-span-2 space-y-4">
          <div onDragOver={e=>{e.preventDefault();setDragging(true)}} onDragLeave={()=>setDragging(false)}
            onDrop={onDrop} onClick={()=>fileRef.current?.click()}
            className={`relative rounded-xl border-2 border-dashed cursor-pointer transition-all min-h-[200px] flex flex-col items-center justify-center gap-3
              ${dragging?'border-brand bg-brand/5':'border-surface-3 hover:border-brand/50 bg-surface-1'}`}>
            <input ref={fileRef} type="file" accept="image/*" className="hidden"
              onChange={e=>e.target.files?.[0]&&pick(e.target.files[0])}/>
            {preview
              ? <img src={preview} alt="preview" className="max-h-48 object-contain rounded-lg"/>
              : <>
                  <div className="w-14 h-14 rounded-full bg-surface-2 flex items-center justify-center">
                    <ImageIcon className="w-7 h-7 text-muted"/>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-white font-medium">Drop image here</p>
                    <p className="text-xs text-muted mt-0.5">or click to browse · JPEG, PNG, WEBP</p>
                  </div>
                </>}
          </div>

          <div className="card space-y-3">
            <p className="label">Inspection Context</p>
            <div className="grid grid-cols-2 gap-2">
              {([
                {label:'Warehouse ID', Icon:Building2, val:warehouseId, set:setWarehouseId},
                {label:'Supplier ID',  Icon:Truck,     val:supplierId,  set:setSupplierId},
              ] as const).map(({label,Icon,val,set})=>(
                <div key={label}>
                  <label className="label block mb-1">{label}</label>
                  <div className="relative">
                    <Icon className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted"/>
                    <input value={val} onChange={e=>set(e.target.value)}
                      className="w-full bg-surface-2 border border-surface-3 rounded-lg pl-8 pr-2 py-2 text-xs text-white focus:outline-none focus:border-brand/60"/>
                  </div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="label block mb-1 flex items-center gap-1">
                  <Thermometer className="w-3 h-3"/> Temp (°C)
                </label>
                <input type="number" value={temp} onChange={e=>setTemp(+e.target.value)}
                  className="w-full bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-brand/60"/>
              </div>
              <div>
                <label className="label block mb-1 flex items-center gap-1">
                  <Droplets className="w-3 h-3"/> Humidity (%)
                </label>
                <input type="number" value={humidity} onChange={e=>setHumidity(+e.target.value)}
                  className="w-full bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-brand/60"/>
              </div>
            </div>
          </div>

          {error && (
            <div className="flex items-start gap-2 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2.5">
              <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0"/>{error}
            </div>
          )}

          <button onClick={run} disabled={!file||loading}
            className="btn-primary w-full flex items-center justify-center gap-2 py-3 disabled:opacity-40 disabled:cursor-not-allowed">
            {loading
              ? <><Loader2 className="w-4 h-4 animate-spin"/>Running AI Pipeline…</>
              : <><Zap className="w-4 h-4"/>Run Inspection</>}
          </button>

          {result && (
            <button onClick={()=>{setFile(null);setPreview(null);setResult(null)}}
              className="btn-ghost w-full flex items-center justify-center gap-2">
              <RefreshCw className="w-3.5 h-3.5"/>New Inspection
            </button>
          )}
        </div>

        {/* Right — results */}
        <div className="lg:col-span-3 space-y-4">
          <AnimatePresence mode="wait">
            {loading && (
              <motion.div key="loading" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}
                className="card flex flex-col items-center gap-4 py-16">
                <div className="relative w-16 h-16">
                  <div className="absolute inset-0 rounded-full border-2 border-t-brand border-transparent animate-spin"/>
                  <div className="w-full h-full rounded-full border-2 border-brand/20 flex items-center justify-center">
                    <Zap className="w-6 h-6 text-brand"/>
                  </div>
                </div>
                <div className="text-center">
                  <p className="text-white font-medium">Analysing…</p>
                  <p className="text-muted text-xs mt-1">Detection → Defects → Grading → Freshness → Decision</p>
                </div>
                {['Detecting produce items','Segmenting surface','Scoring defects','Predicting freshness','Running decision engine']
                  .map((s,i)=><PipelineStep key={s} label={s} delay={i*0.5}/>)}
              </motion.div>
            )}

            {result && !loading && (
              <motion.div key="result" initial={{opacity:0}} animate={{opacity:1}} className="space-y-4">
                <div className="card flex flex-wrap gap-4 items-center justify-between">
                  <div>
                    <p className="label">Inspection ID</p>
                    <p className="font-mono text-xs text-white mt-0.5">{result.inspection_id}</p>
                  </div>
                  <div>
                    <p className="label">Items</p>
                    <p className="stat-value text-xl text-white">{result.items.length}</p>
                  </div>
                  <div>
                    <p className="label">Storage</p>
                    <p className="text-xs text-white font-mono">{result.storage_temp_c}°C / {result.storage_humidity_pct}% RH</p>
                  </div>
                  <a href={`${BASE}/api/inspect/overlay/${result.inspection_id}`}
                    target="_blank" rel="noopener"
                    className="btn-ghost text-xs flex items-center gap-1">
                    <ImageIcon className="w-3.5 h-3.5"/>View Overlay
                  </a>
                </div>

                <div className="card p-0 overflow-hidden">
                  <div className="px-4 pt-3 pb-2 border-b border-surface-3 flex items-center justify-between">
                    <p className="text-sm font-medium text-white">AI Annotated Overlay</p>
                    <span className="badge bg-brand/20 text-brand">Live</span>
                  </div>
                  <img src={`${BASE}${result.overlay_url}`} alt="AI overlay"
                    className="w-full object-contain max-h-64 bg-surface-2"
                    onError={e=>{(e.target as HTMLImageElement).style.display='none'}}/>
                </div>

                {result.items.map(item=><ItemCard key={item.item_id} item={item}/>)}
              </motion.div>
            )}

            {!result && !loading && (
              <motion.div key="empty" className="card flex flex-col items-center gap-3 py-20 text-center">
                <Zap className="w-10 h-10 text-muted/40"/>
                <p className="text-muted text-sm">Upload an image and click <strong className="text-white">Run Inspection</strong></p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
