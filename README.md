# 🚛 Weather-Aware Truck Routing Platform

[![Backend CI / CD](https://img.shields.io/badge/backend-Django%205.2%20LTS-092E20?style=flat&logo=django)](https://www.djangoproject.com/)
[![API Framework](https://img.shields.io/badge/API-Django%20REST%20Framework-red?style=flat)](https://www.django-rest-framework.org/)
[![Frontend](https://img.shields.io/badge/frontend-React%2019%20%2B%20TypeScript-61DAFB?style=flat&logo=react)](https://react.dev/)
[![Styling](https://img.shields.io/badge/styling-Tailwind%20CSS%20v4-38B2AC?style=flat&logo=tailwind-css)](https://tailwindcss.com/)
[![Map Engine](https://img.shields.io/badge/map-MapLibre%20GL%20JS-3969EC?style=flat&logo=maplibre)](https://maplibre.org/)
[![Tests](https://img.shields.io/badge/tests-93%20passed%20(100%25)-brightgreen?style=flat)](#testing--code-quality)
[![Code Quality](https://img.shields.io/badge/linter-Ruff%20%2B%20Oxlint-blueviolet?style=flat)](#testing--code-quality)

A production-grade, full-stack decision-support system that helps commercial truck drivers and fleet dispatchers select the safest, most time-efficient highway route. It evaluates real-time and forecasted weather (wind speed, rain, and snow intensity) against commercial vehicle gross weight, samples risk along route corridors at the truck's exact estimated time of arrival (ETA), and renders interactive GPU-accelerated heatmaps with 0–48 hour forecast time scrubbing.

---

## 📑 Table of Contents

1. [Architecture & System Design](#architecture--system-design)
2. [Requirements Traceability](#requirements-traceability)
3. [Core Logic & Algorithms](#core-logic--algorithms)
   - [Risk Classification Thresholds](#risk-classification-thresholds)
   - [Commercial Truck Load Rules](#commercial-truck-load-rules)
   - [Midpoint Segment Distance Weighting](#midpoint-segment-distance-weighting)
   - [Lexicographic Route Ranking](#lexicographic-route-ranking)
4. [Local Development & Quick Start](#local-development--quick-start)
   - [Prerequisites](#prerequisites)
   - [Manual Local Setup](#manual-local-setup)
   - [Docker Compose](#docker-compose-setup)
5. [API Reference & OpenAPI Specification](#api-reference--openapi-specification)
6. [Testing & Code Quality](#testing--code-quality)
7. [License](#license)

---

## 🏛️ Architecture & System Design

```
+-----------------------------------------------------------------------------------+
|                                     FRONTEND                                      |
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
|                                     BACKEND                                       |
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
- **Pure Functional Core**: The risk engine, load override classifier, midpoint segment integrator, and lexicographic ranking algorithm are pure Python functions with zero I/O or network dependencies.
- **Provider Pattern**: Upstream routing, geocoding, and weather providers are encapsulated behind abstract interfaces with automated fallbacks to keep tests reproducible and services resilient.
- **Stateless & Database-Light**: The application computes route risk dynamically based on real-time routing geometry and forecasted atmospheric conditions; no persistent trip data storage is required.
- **Client-Side Zero-Latency Scrubbing**: The corridor heatmap matrix (48 hours $\times$ $N$ points) is fetched once and cached in memory, allowing responsive slider scrubbing and auto-play animations without redundant network requests.

---

## ✅ Requirements Traceability

| ID | Requirement | Implementation Location | Test Verification | Status |
|:---|:------------|:------------------------|:------------------|:------:|
| **R1** | User inputs: Origin, Destination, Departure Time, Load Weight, Interval | [`TripForm.tsx`](frontend/src/components/TripForm.tsx), [`serializers.py`](backend/apps/trips/serializers.py) | Form Zod validation & serializer tests | ✅ Done |
| **R2** | 3 route options from a truck routing API | [`service.py`](backend/apps/routing/service.py) (`driving-hgv`, alternatives) | `test_routing_providers.py` | ✅ Done |
| **R3** | Weather sampled every 10 / 25 / 50 miles at truck's ETA | [`geometry.py`](backend/apps/routing/geometry.py), [`weather/service.py`](backend/apps/weather/service.py) | `test_geometry.py`, `test_weather_providers.py` | ✅ Done |
| **R4** | Risk from atmospheric thresholds table (Wind, Rain, Snow) | [`classifier.py`](backend/apps/risk/classifier.py) (`classify_condition`) | `test_classifier.py` | ✅ Done |
| **R5** | Commercial truck load override rules | [`classifier.py`](backend/apps/risk/classifier.py) (`apply_load_rules`) | `test_classifier.py` | ✅ Done |
| **R6** | Best route recommendation ranking | [`ranking.py`](backend/apps/risk/ranking.py) (`rank_routes`) | `test_ranking.py` | ✅ Done |
| **R7** | Interactive map with routes, checkpoints, risk levels, ETAs, summaries | [`TripMap.tsx`](frontend/src/components/TripMap.tsx), [`RouteCard.tsx`](frontend/src/components/RouteCard.tsx) | MapLibre vector layers & popups | ✅ Done |
| **R8** | Weather heatmap along corridor with 0–48 hour slider | [`HeatmapControls.tsx`](frontend/src/components/HeatmapControls.tsx), [`trips/views.py`](backend/apps/trips/views.py) | `test_api.py` (heatmap endpoint) | ✅ Done |
| **R9** | Clean repository and automated CI pipeline | GitHub Actions workflow, unit & integration test suites | Full test suites passing | ✅ Done |

---

## 🧠 Core Logic & Algorithms

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

To prevent sampling interval distortion when calculating total miles driven under each hazard level, the route distance is apportioned into segments using midpoint boundaries between adjacent checkpoints:

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
Health check endpoint for liveness probes.
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

## 📄 License

This project is licensed under the MIT License.
