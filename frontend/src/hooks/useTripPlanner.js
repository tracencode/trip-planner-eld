import { useState } from 'react'
import { planTrip, getErrorMessage } from '../services/api'
import { SAMPLE } from '../components/TripForm'

const INITIAL = {
  current_location: '',
  pickup_location: '',
  dropoff_location: '',
  current_cycle_hours: 0,
}

export function useTripPlanner() {
  const [form, setForm] = useState(INITIAL)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  function updateField(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }))
    setError(null)
  }

  function fillSample() {
    setForm(SAMPLE)
    setError(null)
  }

  async function submit(e) {
    e?.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const payload = {
        ...form,
        current_cycle_hours: Number(form.current_cycle_hours) || 0,
      }
      const data = await planTrip(payload)
      setResult(data)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setForm(INITIAL)
    setResult(null)
    setError(null)
  }

  return { form, updateField, fillSample, submit, reset, result, loading, error }
}
