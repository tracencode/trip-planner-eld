import { useCallback, useState } from 'react'
import TripForm from './components/TripForm'
import RouteMap from './components/RouteMap'
import TripSummary from './components/TripSummary'
import ScheduleTable from './components/ScheduleTable'
import DriverLogs from './components/DriverLogs'
import ErrorAlert from './components/ErrorAlert'
import Preloader from './components/Preloader'
import { Card, CardHeader } from './components/ui/Card'
import { useTripPlanner } from './hooks/useTripPlanner'
import {
  IconMap,
  IconRoute,
  IconClock,
  IconDocument,
  IconFuel,
  IconTruck,
  IconShield,
} from './components/icons'

const HOS_RULES = [
  { icon: '⏱', text: '11h max driving / 14h duty' },
  { icon: '☕', text: '30 min break after 8h driving' },
  { icon: '🌙', text: '10h rest when limits hit' },
  { icon: '⛽', text: 'Fuel every 1,000 miles' },
  { icon: '📦', text: '1h pickup + 1h dropoff' },
  { icon: '📊', text: '70h / 8-day cycle' },
]

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-gradient-to-br from-white to-brand-50/40 px-8 py-20 text-center">
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-xl shadow-brand-500/30">
        <IconTruck className="h-10 w-10" />
      </div>
      <h3 className="text-xl font-semibold text-slate-900">Ready to plan your trip</h3>
      <p className="mt-2 max-w-sm text-sm text-slate-500">
        Enter your locations and cycle hours, or try the sample route to see the full
        experience — map, schedule, and ELD logs.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-6 text-sm text-slate-600">
        {['Route map', 'HOS schedule', 'Daily logs'].map((item, i) => (
          <div key={item} className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">
              {i + 1}
            </span>
            {item}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function App() {
  const { form, updateField, fillSample, submit, result, loading, error } = useTripPlanner()
  const [booting, setBooting] = useState(true)
  const finishBoot = useCallback(() => setBooting(false), [])

  return (
    <div className="relative min-h-screen">
      {booting && <Preloader onDone={finishBoot} />}

      {/* Background */}
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-[linear-gradient(160deg,#f8fafc_0%,#eef2ff_40%,#f1f5f9_100%)]" />
        <div className="absolute -left-32 top-0 h-96 w-96 rounded-full bg-brand-200/30 blur-3xl" />
        <div className="absolute -right-32 top-1/3 h-80 w-80 rounded-full bg-indigo-200/25 blur-3xl" />
      </div>

      <div
        className={`relative w-full px-4 py-6 sm:px-6 lg:px-8 lg:py-10 transition-opacity duration-500 ${
          booting ? 'opacity-0' : 'opacity-100'
        }`}
      >
        {/* Header */}
        <header className="mb-8 animate-fade-up">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-start gap-4">
              <div className="hidden h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-600 to-brand-800 text-white shadow-lg shadow-brand-600/30 sm:flex">
                <IconTruck className="h-7 w-7" />
              </div>
              <div>
                <div className="inline-flex items-center gap-2 rounded-full bg-brand-100/80 px-3 py-1 text-xs font-semibold text-brand-700">
                  <IconShield className="h-3.5 w-3.5" />
                  FMCSA HOS · 70hr / 8 day
                </div>
                <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
                  Trip Planner & ELD Log Generator
                </h1>
                <p className="mt-2 max-w-xl text-slate-600">
                  Plan routes, apply Hours of Service rules, and generate daily driver log sheets.
                </p>
              </div>
            </div>

            {result && (
              <div className="flex flex-wrap gap-2 lg:justify-end">
                {[
                  { label: 'Distance', value: `${result.distance} mi`, icon: IconRoute },
                  { label: 'Drive', value: `${result.duration} h`, icon: IconClock },
                  { label: 'Days', value: result.summary?.days, icon: IconDocument },
                ].map(({ label, value, icon: Icon }) => (
                  <div
                    key={label}
                    className="flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 shadow-sm ring-1 ring-slate-200/80"
                  >
                    <Icon className="h-4 w-4 text-brand-600" />
                    <div>
                      <p className="text-[10px] font-medium uppercase tracking-wide text-slate-400">
                        {label}
                      </p>
                      <p className="text-sm font-bold text-slate-900">{value}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-12 lg:gap-8">
          {/* Sidebar */}
          <aside className="lg:col-span-4 xl:col-span-3">
            <div className="sticky top-6 space-y-4">
              <Card className="animate-fade-up">
                <CardHeader
                  icon={IconMap}
                  title="Trip Details"
                  subtitle="Enter stops and current cycle hours"
                />
                <TripForm
                  form={form}
                  onChange={updateField}
                  onSubmit={submit}
                  onFillSample={fillSample}
                  loading={loading}
                />
                <div className="mt-4">
                  <ErrorAlert message={error} />
                </div>
              </Card>

              <Card className="animate-fade-up" style={{ animationDelay: '0.05s' }}>
                <CardHeader icon={IconShield} title="HOS Rules" subtitle="Applied to this trip" />
                <div className="grid gap-2">
                  {HOS_RULES.map(({ icon, text }) => (
                    <div
                      key={text}
                      className="flex items-center gap-3 rounded-xl bg-slate-50 px-3 py-2.5 text-sm text-slate-700"
                    >
                      <span className="text-base">{icon}</span>
                      {text}
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </aside>

          {/* Main content */}
          <main className="space-y-6 lg:col-span-8 xl:col-span-6">
            <Card padding={false} className="animate-fade-up overflow-hidden">
              <div className="border-b border-slate-100 px-5 py-4">
                <CardHeader
                  icon={IconMap}
                  title="Route Map"
                  subtitle="Pickup, dropoff, fuel, break & rest stops"
                  badge={result?.map_stops?.length ? `${result.map_stops.length} points` : null}
                />
              </div>
              <div className="p-4 pt-0">
                <RouteMap
                  route={result?.route}
                  locations={result?.locations}
                  mapStops={result?.map_stops}
                  loading={loading}
                />
              </div>
            </Card>

            {result && !loading && (
              <div className="space-y-6 animate-fade-up">
                <Card>
                  <CardHeader
                    icon={IconRoute}
                    title="Trip Summary"
                    subtitle="Distance, stops, and cycle usage"
                  />
                  <TripSummary
                    summary={result.summary}
                    distance={result.distance}
                    duration={result.duration}
                  />
                </Card>

                <Card padding={false}>
                  <div className="border-b border-slate-100 px-5 py-4">
                    <CardHeader
                      icon={IconClock}
                      title="Schedule"
                      subtitle="Day-by-day timeline of events"
                      badge={`${result.schedule?.length || 0} events`}
                    />
                  </div>
                  <div className="p-4">
                    <ScheduleTable schedule={result.schedule} />
                  </div>
                </Card>

                <Card padding={false}>
                  <div className="border-b border-slate-100 px-5 py-4">
                    <CardHeader
                      icon={IconDocument}
                      title="Driver Logs"
                      subtitle="Filled daily log sheets — click to enlarge"
                      badge={`${result.log_sheets?.length || result.log_images?.length || 0} sheets`}
                    />
                  </div>
                  <div className="p-4">
                    <DriverLogs
                      logImages={result.log_images}
                      logSheets={result.log_sheets}
                    />
                  </div>
                </Card>
              </div>
            )}

            {!result && !loading && <EmptyState />}
          </main>

          <aside className="hidden xl:col-span-3 xl:block">
            <div className="sticky top-6 space-y-4">
              <Card className="animate-fade-up">
                <CardHeader
                  icon={IconRoute}
                  title="Trip Insights"
                  subtitle="Live dashboard side panel"
                  badge={result ? 'Live' : 'Waiting'}
                />
                {!result ? (
                  <div className="space-y-3 text-sm text-slate-500">
                    <div className="rounded-xl bg-slate-50 p-3">
                      Generate a trip to populate this dashboard rail with KPI cards and operational insights.
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="rounded-xl border border-slate-200 bg-white p-3 text-center">
                        <p className="text-xs text-slate-400">Distance</p>
                        <p className="text-lg font-semibold text-slate-700">--</p>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-white p-3 text-center">
                        <p className="text-xs text-slate-400">Drive</p>
                        <p className="text-lg font-semibold text-slate-700">--</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {[
                      { label: 'Total Distance', value: `${result.distance} mi`, icon: IconRoute },
                      { label: 'Drive Duration', value: `${result.duration} h`, icon: IconClock },
                      { label: 'Fuel Stops', value: `${result.summary?.fuel_stops ?? 0}`, icon: IconFuel },
                      { label: 'Log Sheets', value: `${result.log_sheets?.length || 0}`, icon: IconDocument },
                    ].map(({ label, value, icon: Icon }) => (
                      <div
                        key={label}
                        className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2.5"
                      >
                        <div className="flex items-center gap-2">
                          <Icon className="h-4 w-4 text-brand-600" />
                          <span className="text-sm text-slate-600">{label}</span>
                        </div>
                        <span className="text-sm font-semibold text-slate-900">{value}</span>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          </aside>
        </div>

        <footer className="mt-12 border-t border-slate-200/80 pt-6 text-center text-xs text-slate-400">
          Trip Planner & ELD Log Generator — assessment MVP
        </footer>
      </div>
    </div>
  )
}
