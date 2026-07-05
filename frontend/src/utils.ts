export const GRADE_BG: Record<string, string> = {
  Premium:   'bg-brand/20 text-brand',
  'Grade A': 'bg-green-500/20 text-green-400',
  'Grade B': 'bg-sky-500/20 text-sky-400',
  'Grade C': 'bg-amber-500/20 text-amber-400',
  Reject:    'bg-red-500/20 text-red-400',
}

export const FRESHNESS_BG: Record<string, string> = {
  Fresh:              'bg-brand/20 text-brand',
  Good:               'bg-green-500/20 text-green-400',
  'Needs Quick Sale': 'bg-amber-500/20 text-amber-400',
  'Near Expiry':      'bg-orange-500/20 text-orange-400',
  Spoiled:            'bg-red-500/20 text-red-400',
}

export const DECISION_BG: Record<string, string> = {
  Accept:                 'bg-brand/20 text-brand',
  Reject:                 'bg-red-500/20 text-red-400',
  'Manual Inspection':    'bg-amber-500/20 text-amber-400',
  'Priority Dispatch':    'bg-sky-500/20 text-sky-400',
  'Cold Storage Required':'bg-blue-500/20 text-blue-400',
  'Immediate Sale':       'bg-orange-500/20 text-orange-400',
}

export function fmtDate(ts: string) {
  return new Date(ts).toLocaleString()
}
