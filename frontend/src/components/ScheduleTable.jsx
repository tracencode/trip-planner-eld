const typeStyles = {
  start: { badge: 'bg-brand-100 text-brand-800', dot: 'bg-brand-500' },
  end: { badge: 'bg-slate-200 text-slate-700', dot: 'bg-slate-500' },
  driving: { badge: 'bg-blue-100 text-blue-800', dot: 'bg-blue-500' },
  break: { badge: 'bg-amber-100 text-amber-800', dot: 'bg-amber-500' },
  rest: { badge: 'bg-indigo-100 text-indigo-800', dot: 'bg-indigo-500' },
  fuel: { badge: 'bg-orange-100 text-orange-800', dot: 'bg-orange-500' },
  pickup: { badge: 'bg-green-100 text-green-800', dot: 'bg-green-500' },
  dropoff: { badge: 'bg-red-100 text-red-800', dot: 'bg-red-500' },
  arrive_pickup: { badge: 'bg-green-50 text-green-700', dot: 'bg-green-400' },
  arrive_dropoff: { badge: 'bg-red-50 text-red-700', dot: 'bg-red-400' },
  cycle_warning: { badge: 'bg-rose-100 text-rose-800', dot: 'bg-rose-500' },
}

function groupByDay(schedule) {
  const groups = {}
  for (const event of schedule) {
    if (!groups[event.day]) {
      groups[event.day] = { date: event.date, events: [] }
    }
    groups[event.day].events.push(event)
  }
  return Object.entries(groups).map(([day, data]) => ({ day: Number(day), ...data }))
}

export default function ScheduleTable({ schedule }) {
  if (!schedule?.length) return null

  const days = groupByDay(schedule)

  return (
    <div className="space-y-4">
      {days.map(({ day, date, events }) => (
        <div
          key={day}
          className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm"
        >
          <div className="flex items-center justify-between border-b border-slate-100 bg-gradient-to-r from-slate-50 to-brand-50/50 px-4 py-3">
            <div className="flex items-center gap-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-sm font-bold text-white">
                {day}
              </span>
              <div>
                <p className="font-semibold text-slate-900">Day {day}</p>
                <p className="text-xs text-slate-500">{date}</p>
              </div>
            </div>
            <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600 ring-1 ring-slate-200">
              {events.length} events
            </span>
          </div>

          <div className="custom-scroll max-h-80 overflow-y-auto">
            <div className="relative px-4 py-2">
              <div className="absolute bottom-4 left-[27px] top-4 w-0.5 bg-slate-200" />
              {events.map((event, idx) => {
                const style = typeStyles[event.type] || {
                  badge: 'bg-slate-100 text-slate-700',
                  dot: 'bg-slate-400',
                }
                return (
                  <div
                    key={`${event.day}-${event.time}-${event.type}-${idx}`}
                    className="relative flex gap-4 py-3 pl-1"
                  >
                    <div className="relative z-10 mt-1 flex flex-col items-center">
                      <span className={`h-3 w-3 rounded-full ring-4 ring-white ${style.dot}`} />
                    </div>
                    <div className="min-w-0 flex-1 rounded-xl bg-slate-50/80 px-4 py-3 transition hover:bg-slate-50">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-sm font-semibold text-slate-900">
                          {event.time}
                          {event.end_time && event.end_time !== event.time && (
                            <span className="font-normal text-slate-400"> → {event.end_time}</span>
                          )}
                        </span>
                        <span
                          className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${style.badge}`}
                        >
                          {event.type.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-slate-700">{event.description}</p>
                      <div className="mt-2 flex gap-4 text-xs text-slate-500">
                        {event.duration_hours > 0 && (
                          <span>⏱ {event.duration_hours}h</span>
                        )}
                        {event.miles > 0 && <span>📍 {event.miles} mi</span>}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
