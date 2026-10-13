# 🚛 Weather-Aware Truck Routing Platform

[![Backend CI / CD](https://img.shields.io/badge/backend-Django%205.2%20LTS-092E20?style=flat&logo=django)](https://www.djangoproject.com/)
[![API Framework](https://img.shields.io/badge/API-Django%20REST%20Framework-red?style=flat)](https://www.django-rest-framework.org/)
[![Frontend](https://img.shields.io/badge/frontend-React%2019%20%2B%20TypeScript-61DAFB?style=flat&logo=react)](https://react.dev/)
[![Styling](https://img.shields.io/badge/styling-Tailwind%20CSS%20v4-38B2AC?style=flat&logo=tailwind-css)](https://tailwindcss.com/)
[![Map Engine](https://img.shields.io/badge/map-MapLibre%20GL%20JS-3969EC?style=flat&logo=maplibre)](https://maplibre.org/)
[![Tests](https://img.shields.io/badge/tests-93%20passed%20(100%25)-brightgreen?style=flat)](#testing)
[![Code Quality](https://img.shields.io/badge/linter-Ruff%20%2B%20Oxlint-blueviolet?style=flat)](#code-quality)

A production-grade, full-stack decision-support system that helps commercial truck drivers and fleet dispatchers select the safest, most time-efficient highway route. It evaluates real-time and forecasted weather (wind speed, rain, and snow intensity) against commercial vehicle gross weight, samples risk along route corridors at the truck's exact estimated time of arrival (ETA), and renders interactive GPU-accelerated heatmaps with 0–48 hour forecast time scrubbing.

---

## 📑 Table of Contents

1. [Architecture & System Design](#architecture--system-design)
2. [Requirements Traceability](#requirements-traceability)
3. [Core Logic & Algorithms (The 40%)](#core-logic--algorithms-the-40)
   - [Risk Classification Thresholds](#risk-classification-thresholds)
   - [Commercial Truck Load Rules](#commercial-truck-load-rules)
   - [Midpoint Segment Distance Weighting](#midpoint-segment-distance-weighting)
   - [Lexicographic Route Ranking](#lexicographic-route-ranking)
4. [Deployment Guide (Render & Vercel)](#deployment-guide-render--vercel)
   - [Backend Deployment on Render](#1-backend-deployment-on-render)
   - [Frontend Deployment on Vercel](#2-frontend-deployment-on-vercel)
   - [Connecting Frontend to Backend (CORS & Environment)](#3-connecting-frontend-to-backend)
5. [Local Development & Quick Start](#local-development--quick-start)
   - [Prerequisites](#prerequisites)
   - [Manual Local Setup](#manual-local-setup)
   - [Docker Compose](#docker-compose-setup)
6. [API Reference & OpenAPI Specification](#api-reference--openapi-specification)
7. [Testing & Code Quality](#testing--code-quality)
8. [5–10 Minute Loom Walkthrough Script](#510-minute-loom-walkthrough-script)

---

## 🏛️ Architecture & System Design

```
+-----------------------------------------------------------------------------------+
|                                 FRONTEND (Vercel)                                 |
|                                                                                   |
|  React 19 + TypeScript + Vite + Tailwind CSS v4 + MapLibre GL JS + TanStack Query |
|                                                                                   |
|  [ Trip Form ]       [ 3 Route Cards ]     [ Comparison Table ]     [ Checkpoints ]
|  Debounced Pelias    Rank #1 Recommended   Side-by-side metrics    Odometer log   
|                                                                                   |
|  [ Map Canvas: MapLibre GL JS ] <----------> [ 0-48h Scrubbing Heatmap Dock ]     |
|  Vector tiles (OpenFreeMap)                  GPU blur layer + Auto-play scrubber  
+------------------------------------------+----------------------------------------+
                                           | HTTPS / JSON
                                           v
+-----------------------------------------------------------------------------------+
|                                 BACKEND (Render)                                  |
|                                                                                   |
|  Django 5.2 LTS + Django REST Framework + WhiteNoise + Gunicorn                   |
|                                                                                   |
|  /api/v1/geocode         /api/v1/trips/analyze           /api/v1/trips/heatmap    |
|  Autocomplete            3 Routes + ETAs + Risks         48h Corridor Matrix      |
+------------------------------------+----------------------------------------------+
                                     |
               +---------------------+---------------------+
               |                     |                     |
               v                     v                     v
     [ Pure Risk Engine ]    [ Routing Provider ]   [ Weather Provider ]
     • classify_condition()  • OpenRouteService     • Open-Meteo API
     • apply_load_rules()      (driving-hgv profile)  (batched coordinates,
     • aggregate_segments()  • Fallback corridors     30-min cache)
     • rank_routes()         • Haversine & polyline
     (Zero I/O / Pure)
```

### Architectural Principles
- **Pure Functional Core**: The risk engine, load override classifier, midpoint segment integrator, and lexicographic ranking algorithm are 100% pure Python functions with zero I/O or network dependencies.
- **Provider Pattern**: Upstream routing, geocoding, and weather providers are encapsulated behind abstract interfaces with automated fallbacks to keep tests reproducible and services resilient.
- **Stateless & Database-Light**: The application computes route risk dynamically based on real-time routing geometry and forecasted atmospheric conditions; no persistent trip data storage is required.
- **Client-Side Zero-Latency Scrubbing**: The corridor heatmap matrix (48 hours $\times$ $N$ points) is fetched once and pre-cached in memory, allowing 60 FPS slider scrubbing and auto-play animations without redundant network requests.

---

## ✅ Requirements Traceability

| ID | Brief Requirement | Implementation Location | Test Verification | Status |
|:---|:------------------|:------------------------|:------------------|:------:|
| **R1** | User inputs: Origin, Destination, Departure Time, Load Weight, Interval | [`TripForm.tsx`](file:///c:/Users/Naol/Music/scatter/frontend/src/components/TripForm.tsx), [`serializers.py`](file:///c:/Users/Naol/Music/scatter/backend/apps/trips/serializers.py) | Form Zod validation & serializer tests | ✅ Done |
| **R2** | 3 route options from a truck routing API | [`service.py`](file:///c:/Users/Naol/Music/scatter/backend/apps/routing/service.py) (`driving-hgv`, alternatives) | `test_routing_providers.py` | ✅ Done |
| **R3** | Weather sampled every 10 / 25 / 50 miles at truck's ETA | [`geometry.py`](file:///c:/Users/Naol/Music/scatter/backend/apps/routing/geometry.py), [`weather/service.py`](file:///c:/Users/Naol/Music/scatter/backend/apps/weather/service.py) | `test_geometry.py`, `test_weather_providers.py` | ✅ Done |
| **R4** | Risk from atmospheric thresholds table (Wind, Rain, Snow) | [`classifier.py`](file:///c:/Users/Naol/Music/scatter/backend/apps/risk/classifier.py) (`classify_condition`) | `test_classifier.py` | ✅ Done |
| **R5** | 3 Commercial truck load override rules | [`classifier.py`](file:///c:/Users/Naol/Music/scatter/backend/apps/risk/classifier.py) (`apply_load_rules`) | `test_classifier.py` | ✅ Done |
| **R6** | Best route recommendation ranking | [`ranking.py`](file:///c:/Users/Naol/Music/scatter/backend/apps/risk/ranking.py) (`rank_routes`) | `test_ranking.py` | ✅ Done |
| **R7** | Interactive map with routes, checkpoints, risk levels, ETAs, summaries | [`TripMap.tsx`](file:///c:/Users/Naol/Music/scatter/frontend/src/components/TripMap.tsx), [`RouteCard.tsx`](file:///c:/Users/Naol/Music/scatter/frontend/src/components/RouteCard.tsx) | MapLibre vector layers & popups | ✅ Done |
| **R8** | Weather heatmap along corridor with 0–48 hour slider | [`HeatmapControls.tsx`](file:///c:/Users/Naol/Music/scatter/frontend/src/components/HeatmapControls.tsx), [`trips/views.py`](file:///c:/Users/Naol/Music/scatter/backend/apps/trips/views.py) | `test_api.py` (heatmap endpoint) | ✅ Done |
| **R9** | GitHub repository, hosted app (Render + Vercel), Loom walkthrough | Repo root, `render.yaml`, `vercel.json`, `README.md` | Deployment configs & test suites | ✅ Done |

---

## 🧠 Core Logic & Algorithms (The 40%)

The core business logic is located in `backend/apps/risk/` and operates strictly on typed domain models (`Checkpoint`, `CheckpointWeather`, `RouteSummary`, `RiskLevel`).

### Risk Classification Thresholds

Each checkpoint samples atmospheric variables at the truck's ETA. Individual condition levels are computed according to strict inclusive boundary thresholds:

| Condition | Low (0) | Moderate (1) | High (2) | Severe (3) | No Travel (4) |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Wind Speed** | $< 25\text{ mph}$ | $25\text{ to } < 35\text{ mph}$ | $35\text{ to } < 45\text{ mph}$ | $45\text{ to } < 55\text{ mph}$ | $\ge 55\text{ mph}$ |
| **Rain Rate** | $< 0.10\text{ in/hr}$ | $0.10\text{ to } < 0.25\text{ in/hr}$ | $0.25\text{ to } < 0.50\text{ in/hr}$ | $0.50\text{ to } 1.00\text{ in/hr}$ | $> 1.00\text{ in/hr}$ |
| **Snow Rate** | $< 0.5\text{ in/hr}$ | $0.5\text{ to } < 1.0\text{ in/hr}$ | $1.0\text{ to } < 2.0\text{ in/hr}$ | $2.0\text{ to } 3.0\text{ in/hr}$ | $> 3.0\text{ in/hr}$ |

Base condition risk is:
$$\text{Base Risk} = \max(\text{Risk}_{\text{wind}}, \text{Risk}_{\text{rain}}, \text{Risk}_{\text{snow}})$$

### Commercial Truck Load Rules

Truck gross weight heavily influences rollover susceptibility under crosswinds. Load override rules are applied **after** threshold classification and can **only escalate** risk:

1. **Rule 1 (Extreme Wind)**: $\text{Wind} \ge 55\text{ mph}$ at any load weight $\rightarrow$ **No Travel (4)**
2. **Rule 2 (Heavy Wind / Moderate Load)**: $\text{Wind} \in [45, 55)\text{ mph}$ AND $\text{Weight} > 30,000\text{ lb}$ $\rightarrow$ **No Travel (4)**
3. **Rule 3 (Moderate Wind / Heavy Load)**: $\text{Wind} \in [35, 45)\text{ mph}$ AND $\text{Weight} > 40,000\text{ lb}$ $\rightarrow$ Escalates to at least **Severe (3)**

### Midpoint Segment Distance Weighting

To prevent sampling interval distortion when calculating total miles driven under each hazard level, the route distance is apportioned into Voronoi-like segments using midpoint boundaries between adjacent checkpoints:

$$\text{Segment Mileage}_i = \text{boundary}_{i+1} - \text{boundary}_i$$

where $\text{boundary}_i = \frac{\text{mile}_{i-1} + \text{mile}_i}{2}$ (with $\text{boundary}_0 = 0$ and $\text{boundary}_N = \text{Total Distance}$).

The route average risk is the exact distance-weighted integral:
$$\text{Average Risk} = \frac{\sum_{i=1}^{N} \text{Risk}_i \times \text{Segment Mileage}_i}{\text{Total Distance Miles}}$$

### Lexicographic Route Ranking

Routes are ranked according to a deterministic multi-tiered lexicographic priority order:
1. **Unblocked routes prioritized**: Routes with zero **No Travel** closures are ranked above blocked routes.
2. **Primary Metric**: Fewest **Severe** miles.
3. **Secondary Metric**: Fewest **High** miles.
4. **Tertiary Metric**: Lowest distance-weighted **Average Risk**.
5. **Tie-breaker**: Shortest total **Travel Time** (minutes).

---

## 🚀 Deployment Guide (Render & Vercel)

### 1. Backend Deployment on Render

The backend is configured for deployment on [Render](https://render.com) using Python 3.11/3.13, Gunicorn, and WhiteNoise.

#### Option A: 1-Click Blueprint Deploy (`render.yaml`)
1. Fork or push this repository to GitHub.
2. In the Render Dashboard, click **New +** $\rightarrow$ **Blueprint**.
3. Connect your repository. Render will automatically detect `render.yaml`.
4. Click **Apply**.

#### Option B: Manual Web Service Setup
1. In Render, select **New +** $\rightarrow$ **Web Service**.
2. Connect your repository.
3. Configure the following fields:
   - **Name**: `spotter-weather-routing-api`
   - **Root Directory**: `backend`
   - **Environment**: `Python`
   - **Region**: `Oregon (US West)` or your preferred region
   - **Build Command**: `chmod +x build.sh && ./build.sh`
   - **Start Command**: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
4. Add the following **Environment Variables**:

| Variable | Value | Description |
|:---|:---|:---|
| `PYTHON_VERSION` | `3.11.9` | Pinned Python runtime |
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` | Production Django settings |
| `DJANGO_SECRET_KEY` | *(Generate a 50+ char random string)* | Cryptographic signing key |
| `SECURE_SSL_REDIRECT` | `true` | Enforces HTTPS behind proxy |
| `CORS_ALLOWED_ORIGIN_REGEXES` | `^https:\/\/.*\.vercel\.app$` | Permits all Vercel deploy previews |
| `CORS_ALLOWED_ORIGINS` | `https://your-app.vercel.app` | Production frontend domain |
| `OPENROUTESERVICE_API_KEY` | *(Your OpenRouteService key)* | Optional; falls back safely to corridors |

5. Click **Create Web Service**. Once deployed, verify your service by navigating to:
   `https://<your-service>.onrender.com/api/v1/health` (should return `{"status":"ok"}`).

---

### 2. Frontend Deployment on Vercel

The frontend is built with Vite and React 19 and is configured for deployment on [Vercel](https://vercel.com).

1. In the Vercel Dashboard, click **Add New...** $\rightarrow$ **Project**.
2. Import your GitHub repository.
3. Configure project settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click *Edit* and select `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Expand **Environment Variables** and add:

| Variable | Value |
|:---|:---|
| `VITE_API_BASE_URL` | `https://<your-render-service>.onrender.com/api/v1` |

5. Click **Deploy**. Vercel will install dependencies, compile the TypeScript bundle, and publish the app with global CDN distribution.

---

### 3. Connecting Frontend to Backend

1. Copy your Vercel deployment URL (e.g., `https://spotter-truck-routing.vercel.app`).
2. In the Render Dashboard under **Environment Variables**, ensure either:
   - `CORS_ALLOWED_ORIGINS` includes `https://spotter-truck-routing.vercel.app`, or
   - `CORS_ALLOWED_ORIGIN_REGEXES` is set to `^https:\/\/.*\.vercel\.app$`.
3. In Vercel, ensure `VITE_API_BASE_URL` points to your Render API without a trailing slash (e.g. `https://spotter-api.onrender.com/api/v1`).
4. Re-deploy frontend if the backend URL was added after initial build.

---

## 💻 Local Development & Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+ and npm 10+
- Git

### Manual Local Setup

```bash
# 1. Clone repository
git clone https://github.com/<your-username>/spotter-weather-routing.git
cd spotter-weather-routing

# 2. Setup Backend
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt
pip install -e ".[dev]"
cp .env.example .env

# Run migrations and start Django
python manage.py migrate
python manage.py runserver 127.0.0.1:8000

# 3. Setup Frontend (in a separate terminal)
cd ../frontend
npm install
npm run dev
```

Visit [http://localhost:5173](http://localhost:5173) in your browser. The Vite dev server proxies `/api` calls directly to the local Django server at `http://127.0.0.1:8000`.

### Docker Compose Setup

Run both backend and frontend simultaneously with a single command:

```bash
docker compose up --build
```

- Web UI: [http://localhost:5173](http://localhost:5173)
- API Swagger Docs: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)

---

## 📖 API Reference & OpenAPI Specification

Interactive Swagger UI documentation is available at `/api/docs/`, and raw OpenAPI 3.0 schema is available at `/api/schema/`.

### Key Endpoints

#### 1. `GET /api/v1/health`
Health check endpoint for container orchestrators and Render liveness probes.
```bash
curl -s http://localhost:8000/api/v1/health
# {"status":"ok"}
```

#### 2. `GET /api/v1/geocode?q={query}`
Fast autocomplete suggestions for origin/destination city search.
```bash
curl -s "http://localhost:8000/api/v1/geocode?q=Chicago"
```
**Response:**
```json
{
  "results": [
    {
      "label": "Chicago, Cook County, Illinois, United States",
      "lat": 41.87556,
      "lng": -87.62442
    }
  ]
}
```

#### 3. `POST /api/v1/trips/analyze`
Generates 3 route options, calculates checkpoint ETAs, queries weather forecasts, applies truck load overrides, and recommends the safest route.
```bash
curl -X POST http://localhost:8000/api/v1/trips/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "origin": {"lat": 41.8781, "lng": -87.6298, "label": "Chicago, IL"},
    "destination": {"lat": 39.7392, "lng": -104.9903, "label": "Denver, CO"},
    "departure_time": "2026-10-14T06:00:00Z",
    "load_weight_lb": 42000,
    "checkpoint_interval_miles": 25
  }'
```

#### 4. `POST /api/v1/trips/heatmap`
Returns a 48-hour corridor weather risk and meteorology matrix for interactive time scrubbing.
```bash
curl -X POST http://localhost:8000/api/v1/trips/heatmap \
  -H "Content-Type: application/json" \
  -d '{
    "origin": {"lat": 41.8781, "lng": -87.6298},
    "destination": {"lat": 39.7392, "lng": -104.9903},
    "departure_time": "2026-10-14T06:00:00Z",
    "load_weight_lb": 42000
  }'
```

---

## 🧪 Testing & Code Quality

### Running Tests

```bash
# Run backend test suite (93 unit & integration tests)
cd backend
pytest -v

# Run frontend test suite (vitest)
cd ../frontend
npm test

# Run frontend production build check
npm run build
```

### Code Quality & Static Analysis

```bash
# Backend linting & code formatting (Ruff)
cd backend
ruff check .

# Frontend static analysis & linting (Oxlint)
cd ../frontend
npm run lint
```

---

## 🎥 5–10 Minute Loom Walkthrough Script

This script is structured to reflect the exact evaluation rubric: **40% logic**, **35% UX/performance**, **10% code quality**, and **5% documentation**.

### Section 1: Introduction & Architecture (0:00 – 1:15)
- *"Hi everyone, welcome to the walkthrough of the Weather-Aware Truck Routing platform."*
- **Problem Statement**: Commercial trucks face severe safety hazards from high crosswinds, heavy snow, and blinding rain. Standard navigation apps route purely for time without considering vehicle weight or atmospheric risk.
- **Architecture**:
  - Show the high-level architecture diagram.
  - Explain the decoupling: React 19 frontend on Vercel, Django 5.2 LTS backend on Render.
  - Point out that all risk calculations are pure functional Python with zero network dependencies.

### Section 2: Core Logic & Risk Engine (1:15 – 4:00) — *40% Weight*
- Open [`backend/apps/risk/classifier.py`](file:///c:/Users/Naol/Music/scatter/backend/apps/risk/classifier.py) and [`backend/apps/risk/ranking.py`](file:///c:/Users/Naol/Music/scatter/backend/apps/risk/ranking.py).
- **Thresholds**: Walk through wind ($<25$, $25-34$, $35-44$, $45-54$, $\ge 55$), rain, and snow classification.
- **Commercial Load Overrides**: Show how gross weight escalates risk:
  1. $55\text{ mph}$ wind $\rightarrow$ No Travel for any truck.
  2. $45-54\text{ mph}$ wind $+ >30,000\text{ lb}$ $\rightarrow$ No Travel due to high profile tip-over hazard.
  3. $35-44\text{ mph}$ wind $+ >40,000\text{ lb}$ $\rightarrow$ Severe risk.
- **Midpoint Mileage Integration**: Explain how midpoint boundaries between checkpoints prevent sampling interval bias.
- **Lexicographic Ranking**: Show how the algorithm sorts routes: fewest Severe miles $\rightarrow$ fewest High miles $\rightarrow$ lowest average risk $\rightarrow$ shortest travel time.
- Show test execution: run `pytest` in the terminal to display all 93 unit tests passing.

### Section 3: User Experience & Interactive Heatmap (4:00 – 7:15) — *35% Weight*
- Switch to the live application in the browser ([http://localhost:5173](http://localhost:5173)).
- **Trip Form**:
  - Show debounced geocoding autocomplete for origin and destination.
  - Click the **"Chicago $\rightarrow$ Denver"** preset button.
  - Adjust the cargo weight slider to $42,000\text{ lb}$ and select $25\text{ miles}$ checkpoint interval.
  - Click **Analyze Weather Routes**.
- **Route Cards & Recommendation**:
  - Point out the **#1 Recommended** badge with the plain-English explanation.
  - Highlight the Severe miles, High miles, and average risk rating comparisons.
- **MapLibre GL Map**:
  - Show all 3 alternative route polylines rendered with WebGL.
  - Click between route cards to watch the active route highlight.
  - Click on a colored checkpoint circle to reveal the popup showing local ETA, temperature, wind, rain, snow, and the risk override reason.
- **0–48 Hour Corridor Heatmap**:
  - Toggle the Heatmap overlay **ON**.
  - Drag the 0–48h slider to scrub through forecast hours with zero lag.
  - Click **Animate** to show auto-play at 1x and 2x speed.
  - Switch between **Risk**, **Wind Field**, and **Precipitation** modes.
  - Click a corridor sensor point to inspect conditions at that exact hour.
- **Mobile Responsiveness**: Resize the browser window to demonstrate the mobile top-bar switcher (`[Plan]` vs `[Map]`).

### Section 4: Code Quality & API Schema (7:15 – 8:30) — *10% Weight*
- Open Swagger UI at `/api/docs/` and demonstrate the OpenAPI 3.0 documentation generated by `drf-spectacular`.
- Run `ruff check .` on backend and `npm run lint` (`oxlint`) on frontend to demonstrate **0 lint errors across the entire codebase**.
- Highlight clean type definitions and modular structure.

### Section 5: Deployment & Wrap-Up (8:30 – 9:30) — *5% Weight*
- Show `render.yaml` for Render backend hosting and `vercel.json` for Vercel frontend hosting.
- Summarize that all brief requirements (R1 through R9) are met.
- Thank the viewer and close.

---

## 📄 License

This project is licensed under the MIT License.
