import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, PieChart, Pie, Cell, LineChart, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import { TrendingUp, Package, AlertCircle, CheckCircle, Download } from 'lucide-react'
import { analyticsApi } from '../api'
import type { Analytics } from '../api'

const GRADE_COLORS: Record<string,string> = {
  Premium:'#22c55e','Grade A':'#4ade80','Grade B':'#38bdf8','Grade C':'#fbbf24',Reject:'#f87171',
}
const FRESH_COLORS: Record<string,string> = {
  Fresh:'#22c55e',Good:'#4ade80','Needs Quick Sale':'#fbbf24','Near Expiry':'#fb923c',Spoiled:'#f87171',
}
const DECISION_COLORS: Record<string,string> = {
  Accept:'#22c55e',Reject:'#f87171','Manual Inspection':'#fbbf24',
  'Priority Dispatch':'#38bdf8','Cold Storage Required':'#818cf8','Immediate Sale':'#fb923c',
}

function StatCard({label,value,sub,icon:Icon,accent}:
  {label:string;value:string|number;sub?:string;icon:React.FC<{className?:string}>;accent:string}) {
  return (
    <div className="card flex items-start gap-4">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${accent}`}>
        <Icon className="w-5 h-5"/>
      </div>
      <div>
        <p className="label">{label}</p>
        <p className="stat-value text-2xl text-white mt-0.5">{value}</p>
        {sub && <p className="text-xs text-muted mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

const Tip = ({active,payload,label}:{active?:boolean;payload?:{fill?:string;stroke?:string;name?:string;value?:number}[];label?:string}) => {
  if (!active||!payload?.length) return null
  return (
    <div className="bg-surface-2 border border-surface-3 rounded-lg px-3 py-2 text-xs shadow-xl">
      {label && <p className="text-muted mb-1">{label}</p>}
      {payload.map((p,i)=>(
        <p key={i} style={{color:p.fill||p.stroke||'#e2e8f0'}}>
          {p.name}: <span className="font-mono font-semibold">{typeof p.value==='number'?p.value.toFixed(1):p.value}</span>
        </p>
      ))}
    </div>
  )
}

export default function AnalyticsPage() {
  const [days, setDays] = useState(30)
  const { data, isLoading } = useQuery({
    queryKey: ['analytics', days],
    queryFn: () => analyticsApi.summary(days).then(r=>r.data),
    refetchInterval: 30_000,
  })

  if (isLoading||!data) return (
    <div className="flex items-center justify-center h-64">
      <p className="text-muted text-sm animate-pulse">Loading analytics…</p>
    </div>
  )

  const a: Analytics = data
  const gradeData    = Object.entries(a.grade_distribution).map(([name,value])=>({name,value}))
  const freshData    = Object.entries(a.freshness_distribution).map(([name,value])=>({name,value}))
  const decisionData = Object.entries(a.decision_distribution).map(([name,value])=>({name,value}))
  const trendData    = [...(a.recent_trend||[])].reverse()
  const supplierData = Object.entries(a.by_supplier).map(([id,v])=>({
    name:id, total:(v as {total:number}).total,
    quality:+((v as {avg_quality:number}).avg_quality?.toFixed(1)||0),
    rejected:(v as {rejected:number}).rejected||0,
  }))
  const rejectRate = a.total_items ? ((a.rejected_count/a.total_items)*100).toFixed(1) : '0.0'

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Analytics</h1>
          <p className="text-muted text-sm mt-0.5">Quality & freshness trends</p>
        </div>
        <div className="flex items-center gap-2">
          {[7,14,30,90].map(d=>(
            <button key={d} onClick={()=>setDays(d)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
                ${days===d?'bg-brand text-black':'bg-surface-2 text-muted hover:text-white'}`}>
              {d}d
            </button>
          ))}
          <a href={analyticsApi.exportCsv()} className="btn-ghost flex items-center gap-1.5 ml-2">
            <Download className="w-3.5 h-3.5"/>CSV
          </a>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard label="Total Inspections" value={a.total_inspections}
          sub={`Last ${days} days`} icon={Package} accent="bg-brand/10 text-brand"/>
        <StatCard label="Items Inspected" value={a.total_items}
          sub={`Avg ${a.avg_defect_coverage_pct.toFixed(1)}% defect cover`}
          icon={TrendingUp} accent="bg-blue-500/10 text-blue-400"/>
        <StatCard label="Reject Rate" value={`${rejectRate}%`}
          sub={`${a.rejected_count} rejected`}
          icon={AlertCircle} accent="bg-red-500/10 text-red-400"/>
        <StatCard label="Acceptance Rate" value={`${(100-+rejectRate).toFixed(1)}%`}
          sub={`${a.total_items-a.rejected_count} accepted`}
          icon={CheckCircle} accent="bg-green-500/10 text-green-400"/>
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        {[
          {title:'Grade Distribution',    data:gradeData,    colors:GRADE_COLORS},
          {title:'Freshness Distribution',data:freshData,    colors:FRESH_COLORS},
        ].map(({title,data:pd,colors})=>(
          <div key={title} className="card">
            <p className="text-sm font-semibold text-white mb-4">{title}</p>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pd} cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                  dataKey="value" nameKey="name" paddingAngle={3}>
                  {pd.map((e,i)=><Cell key={i} fill={colors[e.name]||'#64748b'}/>)}
                </Pie>
                <Tooltip content={<Tip/>}/>
                <Legend iconSize={8} wrapperStyle={{fontSize:11,color:'#94a3b8'}}/>
              </PieChart>
            </ResponsiveContainer>
          </div>
        ))}

        <div className="card">
          <p className="text-sm font-semibold text-white mb-4">Decision Outcomes</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={decisionData} layout="vertical">
              <XAxis type="number" tick={{fill:'#64748b',fontSize:10}} axisLine={false} tickLine={false}/>
              <YAxis dataKey="name" type="category" width={115}
                tick={{fill:'#94a3b8',fontSize:9}} axisLine={false} tickLine={false}/>
              <Tooltip content={<Tip/>}/>
              <Bar dataKey="value" radius={[0,4,4,0]}>
                {decisionData.map((e,i)=><Cell key={i} fill={DECISION_COLORS[e.name]||'#64748b'}/>)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {trendData.length>0 && (
        <div className="card">
          <p className="text-sm font-semibold text-white mb-4">Daily Trend & Avg Quality</p>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trendData}>
              <XAxis dataKey="day" tick={{fill:'#64748b',fontSize:10}} axisLine={false} tickLine={false}/>
              <YAxis yAxisId="left"  tick={{fill:'#64748b',fontSize:10}} axisLine={false} tickLine={false}/>
              <YAxis yAxisId="right" orientation="right" domain={[0,100]}
                tick={{fill:'#64748b',fontSize:10}} axisLine={false} tickLine={false}/>
              <Tooltip content={<Tip/>}/>
              <Legend iconSize={8} wrapperStyle={{fontSize:11,color:'#94a3b8'}}/>
              <Line yAxisId="left"  type="monotone" dataKey="cnt"         name="Inspections"
                stroke="#22c55e" strokeWidth={2} dot={{fill:'#22c55e',r:3}}/>
              <Line yAxisId="right" type="monotone" dataKey="avg_quality" name="Avg Quality"
                stroke="#38bdf8" strokeWidth={2} dot={{fill:'#38bdf8',r:3}} strokeDasharray="4 2"/>
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {supplierData.length>0 && (
        <div className="card">
          <p className="text-sm font-semibold text-white mb-4">Supplier Performance</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-surface-3">
                  {['Supplier','Items','Avg Quality','Rejected','Reject Rate'].map(h=>(
                    <th key={h} className="pb-2 text-left text-muted font-medium pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-3">
                {supplierData.map(s=>(
                  <tr key={s.name}>
                    <td className="py-2 pr-4 font-mono text-white">{s.name}</td>
                    <td className="py-2 pr-4 text-slate-300">{s.total}</td>
                    <td className="py-2 pr-4">
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-surface-2 rounded-full h-1.5">
                          <div className="h-1.5 rounded-full bg-brand" style={{width:`${s.quality}%`}}/>
                        </div>
                        <span className="font-mono text-white">{s.quality}</span>
                      </div>
                    </td>
                    <td className="py-2 pr-4 text-red-400">{s.rejected}</td>
                    <td className="py-2">
                      <span className={`badge ${s.total&&(s.rejected/s.total)>0.2?'bg-red-500/20 text-red-400':'bg-green-500/20 text-green-400'}`}>
                        {s.total?((s.rejected/s.total)*100).toFixed(1):0}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {a.total_inspections===0 && (
        <div className="card flex flex-col items-center gap-3 py-16 text-center">
          <TrendingUp className="w-10 h-10 text-muted/40"/>
          <p className="text-muted text-sm">No data yet — run your first inspection to populate analytics</p>
        </div>
      )}
    </div>
  )
}
