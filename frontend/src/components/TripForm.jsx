import { IconPin, IconClock } from './icons'

const fields = [
  {
    name: 'current_location',
    label: 'Current Location',
    placeholder: 'e.g. Chicago, IL',
    type: 'text',
    icon: IconPin,
    step: 1,
  },
  {
    name: 'pickup_location',
    label: 'Pickup Location',
    placeholder: 'e.g. Indianapolis, IN',
    type: 'text',
    icon: IconPin,
    step: 2,
  },
  {
    name: 'dropoff_location',
    label: 'Dropoff Location',
    placeholder: 'e.g. Dallas, TX',
    type: 'text',
    icon: IconPin,
    step: 3,
  },
  {
    name: 'current_cycle_hours',
    label: 'Current Cycle Used (Hours)',
    placeholder: 'e.g. 40',
    type: 'number',
    icon: IconClock,
    step: 4,
  },
]

const SAMPLE = {
  current_location: 'Chicago, IL',
  pickup_location: 'Indianapolis, IN',
  dropoff_location: 'Dallas, TX',
  current_cycle_hours: 40,
}

export default function TripForm({ form, onChange, onSubmit, loading, onFillSample }) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      {fields.map((field) => {
        const Icon = field.icon
        return (
          <div key={field.name} className="group">
            <label
              htmlFor={field.name}
              className="mb-1.5 flex items-center gap-2 text-sm font-medium text-slate-700"
            >
              <span className="flex h-5 w-5 items-center justify-center rounded-md bg-slate-100 text-xs font-bold text-brand-600 group-focus-within:bg-brand-100">
                {field.step}
              </span>
              {field.label}
            </label>
            <div className="relative">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                <Icon className="h-4 w-4" />
              </span>
              <input
                id={field.name}
                name={field.name}
                type={field.type}
                min={field.type === 'number' ? 0 : undefined}
                max={field.type === 'number' ? 70 : undefined}
                step={field.type === 'number' ? 0.5 : undefined}
                required
                value={form[field.name]}
                onChange={(e) => onChange(field.name, e.target.value)}
                placeholder={field.placeholder}
                className="w-full rounded-xl border border-slate-200 bg-slate-50/50 py-2.5 pl-10 pr-3.5 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-brand-500 focus:bg-white focus:ring-2 focus:ring-brand-500/20"
              />
            </div>
          </div>
        )
      })}

      <div className="flex flex-col gap-2 pt-1">
        <button
          type="submit"
          disabled={loading}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-brand-600 to-brand-700 px-4 py-3.5 text-sm font-semibold text-white shadow-lg shadow-brand-600/25 transition hover:from-brand-700 hover:to-brand-800 hover:shadow-brand-700/30 disabled:cursor-not-allowed disabled:opacity-60 disabled:shadow-none"
        >
          {loading ? (
            <>
              <Spinner />
              Generating trip…
            </>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Generate Trip
            </>
          )}
        </button>

        {onFillSample && (
          <button
            type="button"
            onClick={onFillSample}
            disabled={loading}
            className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-600 transition hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700 disabled:opacity-50"
          >
            Try sample: Chicago → Dallas
          </button>
        )}
      </div>
    </form>
  )
}

export { SAMPLE }

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  )
}
