import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Clock, ChevronRight, Search, Package, Thermometer } from 'lucide-react'
import { inspectApi } from '../api'
import { fmtDate } from '../utils'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function HistoryPage() {
  const [search,   setSearch]   = useState('')
  const [selected, setSelected] = useState<string|null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['history'],
    queryFn: () => inspectApi.history({ limit: 100 }).then(r => r.data),
    refetchInterval: 15_000,
  })
  const { data: detail } = useQuery({
    queryKey: ['detail', selected],
    queryFn: () => selected ? inspectApi.detail(selected).then(r=>r.data) : null,
    enabled: !!selected,
  })

  const rows = (data||[]).filter(r =>
    !search ||
    r.inspection_id.includes(search) ||
    r.warehouse_id?.toLowerCase().includes(search.toLowerCase()) ||
    r.supplier_id?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="max-w-7xl mx-auto space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Inspection History</h1>
          <p className="text-muted text-sm mt-0.5">{data?.length??'…'} inspections recorded</p>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted"/>
          <input value={search} onChange={e=>setSearch(e.target.value)}
            placeholder="Search ID, warehouse, supplier…"
            className="bg-surface-1 border border-surface-3 rounded-lg pl-9 pr-3 py-2 text-sm text-white focus:outline-none focus:border-brand/60 w-64 placeholder:text-muted"/>
        </div>
      </div>

      <div className="grid lg:grid-cols-5 gap-5">
        {/* List */}
        <div className="lg:col-span-2 space-y-2">
          {isLoading && <p className="text-muted text-sm animate-pulse">Loading…</p>}
          {rows.length===0 && !isLoading && (
            <div className="card py-12 text-center">
              <Clock className="w-8 h-8 text-muted/40 mx-auto mb-2"/>
              <p className="text-muted text-sm">No inspections found</p>
            </div>
          )}
          {rows.map(row=>(
            <motion.button key={row.inspection_id} layout
              initial={{opacity:0}} animate={{opacity:1}}
              onClick={()=>setSelected(row.inspection_id)}
              className={`w-full text-left card transition-all hover:border-brand/40
                ${selected===row.inspection_id?'border-brand/60 bg-brand/5':''}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <Package className="w-4 h-4 text-brand flex-shrink-0"/>
                  <span className="font-mono text-xs text-white truncate">{row.inspection_id}</span>
                </div>
                <ChevronRight className="w-4 h-4 text-muted flex-shrink-0"/>
              </div>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
                <span className="text-xs text-muted flex items-center gap-1">
                  <Clock className="w-3 h-3"/>{fmtDate(row.timestamp)}
                </span>
                {row.warehouse_id && <span className="text-xs text-muted">{row.warehouse_id}</span>}
                {row.supplier_id  && <span className="text-xs text-muted">{row.supplier_id}</span>}
              </div>
              <div className="mt-2 flex items-center gap-3">
                <span className="badge bg-brand/10 text-brand">{row.item_count} item{row.item_count!==1?'s':''}</span>
                {row.storage_temp_c!=null && (
                  <span className="flex items-center gap-1 text-xs text-muted">
                    <Thermometer className="w-3 h-3"/>{row.storage_temp_c}°C
                  </span>
                )}
              </div>
            </motion.button>
          ))}
        </div>

        {/* Detail */}
        <div className="lg:col-span-3">
          {!selected && (
            <div className="card flex flex-col items-center gap-3 py-20 text-center">
              <ChevronRight className="w-8 h-8 text-muted/30"/>
              <p className="text-muted text-sm">Select an inspection to see details</p>
            </div>
          )}
          {selected && !detail && (
            <div className="card py-10 text-center text-muted text-sm animate-pulse">Loading…</div>
          )}
          {detail && (
            <motion.div initial={{opacity:0}} animate={{opacity:1}} className="space-y-4">
              <div className="card">
                <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
                  <p className="font-mono text-xs text-brand">{detail.inspection_id}</p>
                  <p className="text-xs text-muted">{fmtDate(detail.timestamp)}</p>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  {[
                    {l:'Warehouse', v:detail.warehouse_id||'—'},
                    {l:'Supplier',  v:detail.supplier_id||'—'},
                    {l:'Temp',      v:detail.storage_temp_c!=null?`${detail.storage_temp_c}°C`:'—'},
                    {l:'Items',     v:detail.item_count},
                  ].map(s=>(
                    <div key={s.l} className="bg-surface-2 rounded-lg p-2">
                      <p className="label">{s.l}</p>
                      <p className="text-white font-medium mt-0.5">{s.v}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card p-0 overflow-hidden">
                <img src={`${BASE}/api/inspect/overlay/${detail.inspection_id}`} alt="overlay"
                  className="w-full object-contain max-h-56 bg-surface-2"
                  onError={e=>(e.target as HTMLImageElement).style.display='none'}/>
              </div>

              {detail.items?.map((item, idx: number)=>(
                <div key={idx} className="card space-y-2">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <span className="font-medium text-white capitalize">{item.product_type?.replace(/_/g,' ')}</span>
                    <div className="flex gap-1.5">
                      <span className="badge bg-surface-3 text-slate-300">{item.quality_grade}</span>
                      <span className="badge bg-surface-3 text-slate-300">{item.decision}</span>
                    </div>
                  </div>
                  <p className="text-xs text-muted leading-relaxed">{item.explanation}</p>
                  <div className="flex flex-wrap gap-3 text-xs text-muted">
                    <span>Quality: <span className="text-white font-mono">{item.quality_score}</span></span>
                    <span>Freshness: <span className="text-white font-mono">{item.freshness_pct?.toFixed(1)}%</span></span>
                    <span>Shelf Life: <span className="text-white font-mono">{item.shelf_life_days}d</span></span>
                    <span>Defects: <span className="text-white font-mono">{item.defect_coverage_pct?.toFixed(1)}%</span></span>
                  </div>
                </div>
              ))}
            </motion.div>
          )}
        </div>
      </div>
    </div>
  )
}
