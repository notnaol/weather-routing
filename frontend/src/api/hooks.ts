/**
 * TanStack Query hooks and API calls for trip analysis, geocoding, and heatmap.
 */

import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from './client'
import type {
  GeocodingResult,
  HeatmapRequest,
  HeatmapResponse,
  TripAnalysisResponse,
  TripRequest,
} from '@/features/trip/types'

/**
 * Autocomplete address suggestions from the backend geocoding endpoint.
 */
export function useGeocodeQuery(query: string) {
  return useQuery({
    queryKey: ['geocode', query],
    queryFn: async () => {
      if (!query || query.trim().length < 2) return []
      const resp = await api.get<{ results: GeocodingResult[] }>(
        `/geocode?q=${encodeURIComponent(query.trim())}`,
      )
      return resp.results
    },
    enabled: query.trim().length >= 2,
    staleTime: 1000 * 60 * 60, // 1 hour client cache
  })
}

/**
 * Mutation to analyze routes and evaluate weather risks.
 */
export function useAnalyzeTripMutation() {
  return useMutation({
    mutationFn: (request: TripRequest) =>
      api.post<TripAnalysisResponse>('/trips/analyze', request),
  })
}

/**
 * Mutation to fetch 0-48h corridor heatmap weather data.
 */
export function useHeatmapMutation() {
  return useMutation({
    mutationFn: (request: HeatmapRequest) =>
      api.post<HeatmapResponse>('/trips/heatmap', request),
  })
}
