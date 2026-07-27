import { IconDocument } from './icons'

export default function DriverLogs({ logImages, logSheets }) {
  const sheets =
    logSheets?.length > 0
      ? logSheets
      : (logImages || []).map((url, i) => ({ day: i + 1, url, date: '' }))

  if (!sheets.length) return null

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {sheets.map((sheet) => (
        <figure
          key={sheet.url || sheet.day}
          className="group overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm transition hover:shadow-lg hover:ring-1 hover:ring-brand-200"
        >
          <figcaption className="flex items-center justify-between border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white px-4 py-3">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-100 text-brand-700">
                <IconDocument className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-900">Day {sheet.day}</p>
                {sheet.date && <p className="text-xs text-slate-500">{sheet.date}</p>}
              </div>
            </div>
            <a
              href={sheet.url}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white opacity-0 transition group-hover:opacity-100 hover:bg-brand-700"
            >
              Open full size
            </a>
          </figcaption>
          <a href={sheet.url} target="_blank" rel="noreferrer" className="relative block">
            <img
              src={sheet.url}
              alt={`Driver log day ${sheet.day}`}
              className="w-full bg-white object-contain transition group-hover:brightness-[0.98]"
              loading="lazy"
            />
            <div className="absolute inset-0 flex items-center justify-center bg-brand-900/0 opacity-0 transition group-hover:bg-brand-900/5 group-hover:opacity-100">
              <span className="rounded-full bg-white/90 px-4 py-2 text-sm font-medium text-slate-700 shadow-lg">
                View log sheet
              </span>
            </div>
          </a>
        </figure>
      ))}
    </div>
  )
}
