import { describe, expect, it } from 'vitest'
import {
  RiskLevel,
  RISK_COLORS,
  RISK_LABELS,
  getWorstRiskLevel,
} from './risk-colors'
import { useTripStore } from '@/features/trip/store'

describe('Risk Colors & Definitions', () => {
  it('defines correct numerical ordering of RiskLevel enum', () => {
    expect(RiskLevel.Low).toBe(0)
    expect(RiskLevel.Moderate).toBe(1)
    expect(RiskLevel.High).toBe(2)
    expect(RiskLevel.Severe).toBe(3)
    expect(RiskLevel.NoTravel).toBe(4)
  })

  it('maps all risk levels to human labels', () => {
    expect(RISK_LABELS[RiskLevel.Low]).toBe('Low')
    expect(RISK_LABELS[RiskLevel.Moderate]).toBe('Moderate')
    expect(RISK_LABELS[RiskLevel.High]).toBe('High')
    expect(RISK_LABELS[RiskLevel.Severe]).toBe('Severe')
    expect(RISK_LABELS[RiskLevel.NoTravel]).toBe('No Travel')
  })

  it('maps all risk levels to distinct hex colors', () => {
    const colors = Object.values(RISK_COLORS)
    const unique = new Set(colors)
    expect(unique.size).toBe(5)
  })

  it('calculates worst risk level correctly', () => {
    expect(getWorstRiskLevel([RiskLevel.Low, RiskLevel.Moderate])).toBe(RiskLevel.Moderate)
    expect(getWorstRiskLevel([RiskLevel.Low, RiskLevel.Severe, RiskLevel.High])).toBe(RiskLevel.Severe)
    expect(getWorstRiskLevel([])).toBe(RiskLevel.Low)
  })
})

describe('Trip Store', () => {
  it('updates selectedRouteId and heatmapHour correctly', () => {
    const store = useTripStore.getState()
    expect(store.selectedRouteId).toBeNull()
    expect(store.heatmapHour).toBe(0)

    store.setSelectedRoute('route-1')
    expect(useTripStore.getState().selectedRouteId).toBe('route-1')

    store.setHeatmapHour(12)
    expect(useTripStore.getState().heatmapHour).toBe(12)

    // Clamps to 0-47
    store.setHeatmapHour(99)
    expect(useTripStore.getState().heatmapHour).toBe(47)

    const initialVisible = useTripStore.getState().heatmapVisible
    store.toggleHeatmap()
    expect(useTripStore.getState().heatmapVisible).toBe(!initialVisible)

    store.setHeatmapVisible(true)
    expect(useTripStore.getState().heatmapVisible).toBe(true)

    store.setHeatmapMetric('wind')
    expect(useTripStore.getState().heatmapMetric).toBe('wind')

    store.setIsPlaying(true)
    expect(useTripStore.getState().isPlaying).toBe(true)

    store.setPlaybackSpeed(2)
    expect(useTripStore.getState().playbackSpeed).toBe(2)
  })
})
