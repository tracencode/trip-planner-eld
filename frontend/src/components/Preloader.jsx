import { useEffect, useState } from 'react'
import { IconTruck } from './icons'

const MIN_MS = 1400

export default function Preloader({ onDone }) {
  const [progress, setProgress] = useState(0)
  const [leaving, setLeaving] = useState(false)

  useEffect(() => {
    const started = Date.now()
    const tick = setInterval(() => {
      const elapsed = Date.now() - started
      const pct = Math.min(100, (elapsed / MIN_MS) * 100)
      setProgress(pct)
      if (pct >= 100) {
        clearInterval(tick)
        setLeaving(true)
        setTimeout(() => onDone?.(), 380)
      }
    }, 40)
    return () => clearInterval(tick)
  }, [onDone])

  return (
    <div
      className={`fixed inset-0 z-[9999] flex items-center justify-center bg-[#0b1220] transition-opacity duration-350 ${
        leaving ? 'pointer-events-none opacity-0' : 'opacity-100'
      }`}
      aria-busy="true"
      aria-label="Loading application"
    >
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-24 top-1/4 h-72 w-72 rounded-full bg-brand-600/25 blur-3xl" />
        <div className="absolute -right-16 bottom-1/4 h-64 w-64 rounded-full bg-indigo-500/20 blur-3xl" />
      </div>

      <div className="relative z-10 flex w-full max-w-sm flex-col items-center px-8 text-center">
        <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-2xl shadow-brand-600/40 preloader-logo">
          <IconTruck className="h-8 w-8" />
        </div>

        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-300">
          Hours of Service
        </p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-white">
          Trip Planner & ELD
        </h1>
        <p className="mt-2 text-sm text-slate-400">
          Preparing route tools and log generator…
        </p>

        <div className="mt-8 w-full space-y-2">
          <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-gradient-to-r from-brand-400 via-brand-500 to-indigo-400 transition-[width] duration-100 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex justify-between text-[11px] text-slate-500">
            <span>Loading dashboard</span>
            <span className="tabular-nums text-slate-400">{Math.round(progress)}%</span>
          </div>
        </div>
      </div>
    </div>
  )
}
