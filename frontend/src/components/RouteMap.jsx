import { useEffect, useMemo, useState } from 'react'
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import { IconMap } from './icons'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

const STOP_META = {
  current: { color: '#2563eb', label: 'Current' },
  start: { color: '#2563eb', label: 'Start' },
  pickup: { color: '#16a34a', label: 'Pickup' },
  arrive_pickup: { color: '#16a34a', label: 'Arrive Pickup' },
  dropoff: { color: '#dc2626', label: 'Dropoff' },
  arrive_dropoff: { color: '#dc2626', label: 'Arrive Dropoff' },
  end: { color: '#0f172a', label: 'End' },
  fuel: { color: '#ea580c', label: 'Fuel' },
  break: { color: '#ca8a04', label: 'Break' },
  rest: { color: '#7c3aed', label: 'Rest' },
}

const LOADING_STEPS = [
  { at: 0, label: 'Geocoding locations…' },
  { at: 22, label: 'Calculating route…' },
  { at: 48, label: 'Building HOS schedule…' },
  { at: 72, label: 'Generating driver logs…' },
  { at: 90, label: 'Finalizing trip…' },
]

function coloredIcon(color, size = 14) {
  return L.divIcon({
    className: '',
    html: `<span style="
      display:block;width:${size}px;height:${size}px;border-radius:50%;
      background:${color};border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,.35);
    "></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

function FitBounds({ positions }) {
  const map = useMap()
  useEffect(() => {
    if (positions?.length) {
      map.fitBounds(positions, { padding: [40, 40] })
    }
  }, [map, positions])
  return null
}

function MapLoadingProgress() {
  const [progress, setProgress] = useState(6)

  useEffect(() => {
    const started = Date.now()
    const id = setInterval(() => {
      const elapsed = Date.now() - started
      // Ease toward ~92% while waiting; never hit 100 until result arrives
      const target = Math.min(92, 8 + elapsed / 180)
      setProgress((prev) => {
        const next = prev + (target - prev) * 0.12
        return Math.min(92, Math.max(prev, next))
      })
    }, 120)
    return () => clearInterval(id)
  }, [])

  const stepLabel = [...LOADING_STEPS].reverse().find((s) => progress >= s.at)?.label
    || LOADING_STEPS[0].label

  return (
    <div className="flex h-80 flex-col items-center justify-center gap-6 rounded-2xl border border-brand-100 bg-gradient-to-br from-brand-50/80 via-white to-slate-50 px-8 md:h-[460px]">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-lg shadow-brand-500/30">
        <IconMap className="h-7 w-7" />
      </div>

      <div className="w-full max-w-md space-y-3 text-center">
        <div>
          <p className="text-base font-semibold text-slate-900">Generating your trip</p>
          <p className="mt-1 text-sm text-brand-700">{stepLabel}</p>
        </div>

        <div className="relative h-3 overflow-hidden rounded-full bg-slate-200/80 ring-1 ring-slate-200">
          <div
            className="progress-bar-fill absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-brand-500 via-brand-600 to-indigo-500 transition-[width] duration-300 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>Route · Schedule · ELD logs</span>
          <span className="font-semibold tabular-nums text-brand-700">{Math.round(progress)}%</span>
        </div>

        <div className="flex justify-center gap-2 pt-1">
          {LOADING_STEPS.map((s, i) => (
            <span
              key={s.label}
              className={`h-1.5 w-8 rounded-full transition-colors ${
                progress >= s.at ? 'bg-brand-500' : 'bg-slate-200'
              }`}
              title={s.label}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

export default function RouteMap({ route, locations, mapStops, loading = false }) {
  const positions = useMemo(() => route?.geometry?.coordinates || [], [route])
  const center = positions[0] || [39.8283, -98.5795]

  const primaryMarkers = useMemo(() => {
    return [
      locations?.current && { ...locations.current, type: 'current', label: locations.current.label },
      locations?.pickup && { ...locations.pickup, type: 'pickup', label: locations.pickup.label },
      locations?.dropoff && { ...locations.dropoff, type: 'dropoff', label: locations.dropoff.label },
    ].filter(Boolean)
  }, [locations])

  const intermediateStops = useMemo(() => {
    const skip = new Set(['start', 'end', 'arrive_pickup', 'arrive_dropoff', 'pickup', 'dropoff'])
    return (mapStops || []).filter((s) => !skip.has(s.type))
  }, [mapStops])

  if (loading) {
    return <MapLoadingProgress />
  }

  if (!positions.length) {
    return (
      <div className="flex h-80 flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed border-slate-200 bg-gradient-to-br from-slate-50 to-brand-50/30 md:h-[460px]">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white text-brand-500 shadow-md ring-1 ring-slate-200">
          <IconMap className="h-8 w-8" />
        </div>
        <div className="text-center">
          <p className="font-medium text-slate-700">Your route will appear here</p>
          <p className="mt-1 text-sm text-slate-500">Generate a trip to see the map with stops</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="relative h-80 overflow-hidden rounded-2xl border border-slate-200/80 shadow-md ring-1 ring-slate-200/50 md:h-[460px]">
        <div className="absolute left-3 top-3 z-[1000] rounded-lg bg-white/95 px-3 py-1.5 text-xs font-medium text-slate-700 shadow-md backdrop-blur">
          {intermediateStops.length} stop{intermediateStops.length === 1 ? '' : 's'} on route
        </div>
        <MapContainer center={center} zoom={5} scrollWheelZoom className="h-full w-full">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <Polyline positions={positions} pathOptions={{ color: '#2563eb', weight: 5, opacity: 0.9 }} />
          <FitBounds positions={positions} />

          {primaryMarkers.map((m) => (
            <Marker
              key={`primary-${m.type}`}
              position={[m.lat, m.lon]}
              icon={coloredIcon(STOP_META[m.type]?.color || '#2563eb', 18)}
            >
              <Popup>
                <strong>{STOP_META[m.type]?.label || m.type}</strong>
                <br />
                {m.label || m.name}
              </Popup>
            </Marker>
          ))}

          {intermediateStops.map((s, idx) => (
            <Marker
              key={`stop-${s.type}-${s.day}-${s.time}-${idx}`}
              position={[s.lat, s.lon]}
              icon={coloredIcon(STOP_META[s.type]?.color || '#64748b', 12)}
            >
              <Popup>
                <strong>{STOP_META[s.type]?.label || s.type}</strong>
                <br />
                Day {s.day} · {s.time}
                <br />
                {s.label}
                {s.duration_hours > 0 && (
                  <>
                    <br />
                    Duration: {s.duration_hours}h
                  </>
                )}
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      <div className="flex flex-wrap gap-2">
        {[
          ['current', 'Current'],
          ['pickup', 'Pickup'],
          ['dropoff', 'Dropoff'],
          ['fuel', 'Fuel'],
          ['break', 'Break'],
          ['rest', 'Rest'],
        ].map(([key, label]) => (
          <span
            key={key}
            className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-xs font-medium text-slate-600 ring-1 ring-slate-200"
          >
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ background: STOP_META[key].color }}
            />
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}
