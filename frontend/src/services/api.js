import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || ''

const client = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 120000,
})

/**
 * Plan a trip with HOS schedule and log sheets.
 * @param {{ current_location: string, pickup_location: string, dropoff_location: string, current_cycle_hours: number }} payload
 */
export async function planTrip(payload) {
  const { data } = await client.post('/api/plan-trip/', payload)
  return data
}

export function getErrorMessage(error) {
  if (error.response?.data) {
    const d = error.response.data
    if (typeof d.detail === 'string') return d.detail
    if (d.errors) {
      const first = Object.values(d.errors).flat()[0]
      if (first) return String(first)
    }
  }
  if (error.code === 'ECONNABORTED') {
    return 'Request timed out. The route may be too complex — try again.'
  }
  if (!error.response) {
    return 'Cannot reach the server. Check that the API is running.'
  }
  return error.message || 'Something went wrong.'
}
