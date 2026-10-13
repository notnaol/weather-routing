/**
 * Zustand store for trip UI state.
 */

import { create } from 'zustand'

interface TripStore {
  selectedRouteId: string | null
  heatmapHour: number
  heatmapVisible: boolean
  heatmapMetric: 'risk' | 'wind' | 'precip'
  isPlaying: boolean
  playbackSpeed: number
  setSelectedRoute: (id: string) => void
  setHeatmapHour: (hour: number) => void
  setHeatmapVisible: (visible: boolean) => void
  toggleHeatmap: () => void
  setHeatmapMetric: (metric: 'risk' | 'wind' | 'precip') => void
  setIsPlaying: (isPlaying: boolean) => void
  setPlaybackSpeed: (speed: number) => void
}

export const useTripStore = create<TripStore>((set) => ({
  selectedRouteId: null,
  heatmapHour: 0,
  heatmapVisible: true, // Default to visible once a trip is loaded
  heatmapMetric: 'risk',
  isPlaying: false,
  playbackSpeed: 1,
  setSelectedRoute: (id) => set({ selectedRouteId: id }),
  setHeatmapHour: (hour) => set({ heatmapHour: Math.max(0, Math.min(47, hour)) }),
  setHeatmapVisible: (visible) => set({ heatmapVisible: visible }),
  toggleHeatmap: () => set((state) => ({ heatmapVisible: !state.heatmapVisible })),
  setHeatmapMetric: (metric) => set({ heatmapMetric: metric }),
  setIsPlaying: (isPlaying) => set({ isPlaying }),
  setPlaybackSpeed: (speed) => set({ playbackSpeed: speed }),
}))

