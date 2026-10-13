/**
 * Trip-related type definitions.
 * These mirror the backend API response shapes.
 */

export interface LatLng {
  lat: number
  lng: number
  label?: string
}

export interface GeocodingResult {
  label: string
  lat: number
  lng: number
}

export interface TripRequest {
  origin: LatLng
  destination: LatLng
  departure_time: string
  load_weight_lb: number
  checkpoint_interval_miles: 10 | 25 | 50
}

export interface WeatherData {
  wind_mph: number
  rain_in_per_hr: number
  snow_in_per_hr: number
  wind_gust_mph?: number | null
  temperature_f?: number | null
}

export interface Checkpoint {
  mile: number
  lat: number
  lng: number
  eta: string
  weather: WeatherData
  condition_levels: {
    wind: number
    rain: number
    snow: number
  }
  risk: number
  reason: string
  segment_miles: number
}

export interface RouteSummary {
  severe_miles: number
  high_miles: number
  no_travel_miles: number
  average_risk: number
  total_distance_miles?: number
  total_duration_minutes?: number
  worst_checkpoint: Checkpoint | null
}

export interface RouteAnalysis {
  id: string
  name: string
  distance_miles: number
  duration_minutes: number
  geometry: string // encoded polyline
  summary: RouteSummary
  checkpoints: Checkpoint[]
}

export interface TripAnalysisResponse {
  routes: RouteAnalysis[]
  recommended_route_id: string
  recommendation_reason: string
  ranked_route_ids: string[]
  all_routes_blocked: boolean
}

export interface HeatmapRequest {
  origin: LatLng
  destination: LatLng
  departure_time: string
  load_weight_lb: number
}

export interface HeatmapPoint {
  lat: number
  lng: number
}

export interface HeatmapResponse {
  points: HeatmapPoint[]
  risk: number[][] // risk[hour][point]
  weather: {
    wind: number[][]
    rain: number[][]
    snow: number[][]
  }
  start_hour: string
}
