import { IconRoute, IconClock, IconFuel, IconShield } from './icons'

const STAT_CONFIG = [
  { key: 'distance', label: 'Distance', suffix: ' mi', icon: IconRoute, color: 'from-blue-500 to-blue-600' },
  { key: 'duration', label: 'Drive Time', suffix: ' h', icon: IconClock, color: 'from-violet-500 to-violet-600' },
  { key: 'fuel_stops', label: 'Fuel Stops', icon: IconFuel, color: 'from-orange-500 to-orange-600' },
  { key: 'breaks', label: 'Breaks', icon: IconClock, color: 'from-amber-500 to-amber-600' },
  { key: 'rest_stops', label: 'Rest Stops', icon: IconShield, color: 'from-indigo-500 to-indigo-600' },
  { key: 'days', label: 'Trip Days', icon: IconRoute, color: 'from-slate-500 to-slate-600' },
]

function StatCard({ label, value, icon: Icon, color, accent }) {
  return (
    <div
      className={`group relative overflow-hidden rounded-2xl p-4 transition hover:shadow-md ${
        accent
          ? 'bg-gradient-to-br from-amber-50 to-orange-50 ring-1 ring-amber-200'
          : 'bg-white ring-1 ring-slate-200/80 hover:ring-brand-200'
      }`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
          <p className="mt-1.5 text-2xl font-bold tracking-tight text-slate-900">{value}</p>
        </div>
        <div
          className={`flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br ${color} text-white shadow-sm`}
        >
          <Icon className="h-4 w-4" />
        </div>
      </div>
    </div>
  )
}

export default function TripSummary({ summary, distance, duration }) {
  if (!summary) return null

  const cyclePct = Math.min(
    100,
    (summary.cycle_hours_used / (summary.cycle_limit || 70)) * 100,
  )

  const values = {
    distance: distance ?? summary.distance_miles,
    duration: duration ?? summary.driving_hours,
    fuel_stops: summary.fuel_stops,
    breaks: summary.breaks,
    rest_stops: summary.rest_stops,
    days: summary.days,
  }

  return (
    <div className="space-y-4">
      {summary.cycle_exhausted && (
        <div className="flex gap-3 rounded-xl border border-amber-200 bg-gradient-to-r from-amber-50 to-orange-50 px-4 py-3 text-sm text-amber-900">
          <span className="text-lg">⚠️</span>
          <p>
            <strong>70-hour cycle limit reached.</strong> A 34-hour restart would be required in
            production; this MVP continues after overnight rest for demo purposes.
          </p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {STAT_CONFIG.map(({ key, label, suffix = '', icon, color }) => (
          <StatCard
            key={key}
            label={label}
            value={`${values[key]}${suffix}`}
            icon={icon}
            color={color}
          />
        ))}
      </div>

      <div className="rounded-2xl bg-white p-4 ring-1 ring-slate-200/80">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="font-medium text-slate-700">70-Hour Cycle</span>
          <span className="text-slate-500">
            <span className="font-semibold text-slate-900">{summary.cycle_hours_used}</span>
            {' / '}
            {summary.cycle_limit || 70}h used
          </span>
        </div>
        <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
          <div
            className={`h-full rounded-full transition-all duration-700 ${
              summary.cycle_exhausted
                ? 'bg-gradient-to-r from-amber-500 to-red-500'
                : 'bg-gradient-to-r from-brand-500 to-brand-600'
            }`}
            style={{ width: `${cyclePct}%` }}
          />
        </div>
        <p className="mt-2 text-xs text-slate-500">
          {summary.cycle_hours_remaining}h remaining in current 8-day cycle
        </p>
      </div>
    </div>
  )
}
