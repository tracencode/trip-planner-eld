# Trip Planner & ELD Log Generator

A simple full-stack MVP that plans a trucking trip, applies basic Hours of Service (HOS) rules, shows the route on a map, and generates daily driver log sheet PNGs.

**Stack:** Django + Django REST Framework · React (Vite) · Tailwind CSS · SQLite · OpenRouteService · React Leaflet

---

## Features

- Enter current, pickup, and dropoff locations plus current cycle hours
- Route calculation via OpenRouteService Directions API
- Interactive map (React Leaflet) with pickup, dropoff, fuel, break, and rest markers
- Simplified HOS schedule:
  - 11-hour max driving / 14-hour duty window
  - 30-minute break after 8 hours of cumulative driving
  - 10-hour overnight rest when limits are reached
  - Fuel stop every 1,000 miles
  - 1 hour pickup + 1 hour dropoff
  - 70-hour / 8-day cycle tracking
- Daily FMCSA-style driver log sheet PNGs (graph + totals + remarks)
- Deployment-ready for **Render** (backend) and **Vercel** (frontend)

---

## Project structure

```
trip-planner-eld/
├── backend/                 # Django API
│   ├── config/              # Settings, URLs, WSGI
│   ├── trips/
│   │   ├── services/
│   │   │   ├── routing.py       # OpenRouteService
│   │   │   ├── schedule.py      # HOS schedule
│   │   │   └── log_generator.py # PNG log sheets
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   ├── media/logs/          # Generated log images
│   ├── requirements.txt
│   ├── Procfile
│   └── build.sh
└── frontend/                # React + Vite SPA
    ├── src/
    │   ├── components/
    │   ├── hooks/
    │   └── services/
    └── vercel.json
```

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- Free [OpenRouteService API key](https://openrouteservice.org/dev/#/signup)

---

## Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set OPENROUTESERVICE_API_KEY

python manage.py migrate
python manage.py runserver
```

API runs at `http://127.0.0.1:8000`

### Health check

```bash
curl http://127.0.0.1:8000/api/health/
```

### Plan trip

```bash
curl -X POST http://127.0.0.1:8000/api/plan-trip/ \
  -H "Content-Type: application/json" \
  -d '{
    "current_location": "Chicago, IL",
    "pickup_location": "Indianapolis, IN",
    "dropoff_location": "Dallas, TX",
    "current_cycle_hours": 40
  }'
```

### Run schedule unit tests

```bash
cd backend
source .venv/bin/activate
python manage.py test trips
```

---

## Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
# VITE_API_URL=http://127.0.0.1:8000

npm run dev
```

App runs at `http://localhost:5173`

In local development you can also leave `VITE_API_URL` empty and rely on the Vite proxy (`/api` and `/media` → Django). Log image URLs still use `PUBLIC_BASE_URL` from the backend `.env`.

---

## Environment variables

### Backend (`backend/.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret | long random string |
| `DEBUG` | Debug mode | `True` / `False` |
| `ALLOWED_HOSTS` | Comma-separated hosts | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | Frontend origins | `http://localhost:5173` |
| `PUBLIC_BASE_URL` | Absolute URL for media links | `http://127.0.0.1:8000` |
| `OPENROUTESERVICE_API_KEY` | ORS API key | from openrouteservice.org |

### Frontend (`frontend/.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | Backend base URL (no trailing slash) | `http://127.0.0.1:8000` |

### OpenRouteService API key

1. Sign up at [https://openrouteservice.org/dev/#/signup](https://openrouteservice.org/dev/#/signup)
2. Create a free token under **API Keys**
3. Put it in `backend/.env` as `OPENROUTESERVICE_API_KEY`

---

## API response shape

`POST /api/plan-trip/`

```json
{
  "route": {
    "geometry": { "type": "LineString", "coordinates": [[lat, lon], ...] },
    "waypoints": []
  },
  "distance": 0,
  "duration": 0,
  "schedule": [
    {
      "day": 1,
      "time": "08:00",
      "end_time": "08:00",
      "date": "2026-07-28",
      "type": "start",
      "description": "Start trip",
      "duration_hours": 0,
      "status": "on_duty",
      "miles": 0,
      "miles_along_route": 0
    }
  ],
  "map_stops": [
    {
      "type": "fuel",
      "label": "Fuel stop",
      "lat": 0,
      "lon": 0,
      "day": 2,
      "time": "11:22"
    }
  ],
  "log_images": ["http://.../media/logs/log_xxx_day1.png"],
  "summary": {
    "distance_miles": 0,
    "driving_hours": 0,
    "fuel_stops": 0,
    "breaks": 0,
    "rest_stops": 0,
    "cycle_hours_used": 0,
    "cycle_hours_remaining": 0
  }
}
```

---

## Deployment

### Backend → Render

1. Push this repo to GitHub.
2. Create a **Web Service** on [Render](https://render.com).
3. Settings:
   - **Root Directory:** `backend`
   - **Runtime:** Python
   - **Build Command:** `chmod +x build.sh && ./build.sh`
   - **Start Command:** `gunicorn config.wsgi:application`
4. Environment variables on Render:
   - `SECRET_KEY` — generate a strong secret
   - `DEBUG` — `False`
   - `ALLOWED_HOSTS` — your Render hostname (e.g. `trip-planner-api.onrender.com`)
   - `CORS_ALLOWED_ORIGINS` — your Vercel URL (e.g. `https://your-app.vercel.app`)
   - `PUBLIC_BASE_URL` — `https://trip-planner-api.onrender.com`
   - `OPENROUTESERVICE_API_KEY` — your ORS key
5. Deploy. Confirm `https://<service>/api/health/` returns `{"status":"ok"}`.

> Note: Render’s free disk is ephemeral. Log PNGs are regenerated per request and may disappear after restarts — acceptable for this MVP.

### Frontend → Vercel

1. Import the repo in [Vercel](https://vercel.com).
2. Settings:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Vite
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
3. Environment variable:
   - `VITE_API_URL` — your Render backend URL (e.g. `https://trip-planner-api.onrender.com`)
4. Deploy.

`frontend/vercel.json` already configures SPA rewrites.

---

## HOS rules (implemented only)

| Rule | Value |
|------|--------|
| Max driving / day | 11 hours |
| Max duty window | 14 hours |
| Break after cumulative driving | 30 min after 8 hours |
| Overnight rest | 10 hours after 11 driving **or** 14 duty |
| Fuel | Every 1,000 miles (~30 min) |
| Pickup / Dropoff | 1 hour each |
| Cycle | 70 hours / 8 days (tracked from input) |

**Not implemented:** sleeper berth, adverse driving, short haul, 34-hour restart, exceptions, multi-driver, time zones.

---

## License

MIT — assessment / portfolio MVP.
