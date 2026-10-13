import { useEffect, useMemo } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  CloudRain,
  Eye,
  EyeOff,
  Flame,
  Gauge,
  Pause,
  Play,
  RotateCcw,
  ShieldAlert,
  Wind,
} from 'lucide-react'
import { format, addHours } from 'date-fns'
import { useTripStore } from '@/features/trip/store'
import { RiskBadge } from './RiskBadge'
import type { HeatmapResponse } from '@/features/trip/types'

interface HeatmapControlsProps {
  heatmapData: HeatmapResponse | null
  isLoading?: boolean
}

export function HeatmapControls({ heatmapData, isLoading }: HeatmapControlsProps) {
  const {
    heatmapHour,
    setHeatmapHour,
    heatmapVisible,
    toggleHeatmap,
    heatmapMetric,
    setHeatmapMetric,
    isPlaying,
    setIsPlaying,
    playbackSpeed,
    setPlaybackSpeed,
  } = useTripStore()

  // Auto-play animation timer
  useEffect(() => {
    if (!isPlaying || !heatmapData) return

    const intervalMs = playbackSpeed === 2 ? 220 : 450
    const interval = setInterval(() => {
      setHeatmapHour((heatmapHour + 1) % 48)
    }, intervalMs)

    return () => clearInterval(interval)
  }, [isPlaying, heatmapHour, playbackSpeed, heatmapData, setHeatmapHour])

  const startHourStr = heatmapData?.start_hour
  const baseDate = useMemo(
    () => (startHourStr ? new Date(startHourStr) : new Date(0)),
    [startHourStr],
  )
  const currentDate = useMemo(() => addHours(baseDate, heatmapHour), [baseDate, heatmapHour])

  if (!heatmapData) {
    if (isLoading) {
      return (
        <div className="bg-card/95 backdrop-blur-md border border-border rounded-2xl p-4 shadow-xl text-xs flex items-center gap-3">
          <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-muted-foreground font-medium">
            Generating 48-hour corridor weather matrix...
          </span>
        </div>
      )
    }
    return null
  }


  // Corridor stats for this selected hour
  const currentRisks = heatmapData.risk[heatmapHour] ?? []
  const currentWinds = heatmapData.weather.wind[heatmapHour] ?? []
  const currentRains = heatmapData.weather.rain[heatmapHour] ?? []
  const currentSnows = heatmapData.weather.snow[heatmapHour] ?? []

  const maxRisk = currentRisks.length > 0 ? Math.max(...currentRisks) : 0
  const maxWind = currentWinds.length > 0 ? Math.max(...currentWinds) : 0
  const maxRain = currentRains.length > 0 ? Math.max(...currentRains) : 0
  const maxSnow = currentSnows.length > 0 ? Math.max(...currentSnows) : 0

  return (
    <div className="bg-card/95 backdrop-blur-md border border-border/80 rounded-2xl p-3.5 shadow-2xl w-[92vw] max-w-2xl text-foreground transition-all">
      {/* Top Controls Row */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-border/60">
        <div className="flex items-center gap-2">
          {/* Toggle Heatmap Visibility */}
          <button
            type="button"
            onClick={toggleHeatmap}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-colors border ${
              heatmapVisible
                ? 'bg-primary text-primary-foreground border-primary shadow-xs'
                : 'bg-muted text-muted-foreground border-border hover:bg-muted/80'
            }`}
            title={heatmapVisible ? 'Hide corridor heatmap' : 'Show corridor heatmap'}
          >
            {heatmapVisible ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            <span>Heatmap {heatmapVisible ? 'ON' : 'OFF'}</span>
          </button>

          {/* Metric Selector Tabs */}
          <div className="inline-flex items-center bg-muted/80 p-0.5 rounded-lg border border-border text-[11px] font-medium">
            <button
              type="button"
              onClick={() => setHeatmapMetric('risk')}
              className={`flex items-center gap-1 px-2 py-1 rounded-md transition-all ${
                heatmapMetric === 'risk'
                  ? 'bg-card text-foreground font-semibold shadow-xs'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <ShieldAlert className="w-3 h-3 text-red-500" />
              <span>Risk</span>
            </button>
            <button
              type="button"
              onClick={() => setHeatmapMetric('wind')}
              className={`flex items-center gap-1 px-2 py-1 rounded-md transition-all ${
                heatmapMetric === 'wind'
                  ? 'bg-card text-foreground font-semibold shadow-xs'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Wind className="w-3 h-3 text-sky-500" />
              <span>Wind</span>
            </button>
            <button
              type="button"
              onClick={() => setHeatmapMetric('precip')}
              className={`flex items-center gap-1 px-2 py-1 rounded-md transition-all ${
                heatmapMetric === 'precip'
                  ? 'bg-card text-foreground font-semibold shadow-xs'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <CloudRain className="w-3 h-3 text-blue-500" />
              <span>Precip</span>
            </button>
          </div>
        </div>

        {/* Time Playback Controls */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setHeatmapHour(0)}
            className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors"
            title="Reset to Departure Hour (0h)"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <button
            type="button"
            onClick={() => setHeatmapHour(Math.max(0, heatmapHour - 1))}
            disabled={heatmapHour === 0}
            className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-30 rounded-lg transition-colors"
            title="Step Back 1 Hour"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => setIsPlaying(!isPlaying)}
            className="flex items-center gap-1 px-2.5 py-1.5 bg-secondary text-secondary-foreground hover:bg-secondary/80 rounded-lg text-xs font-semibold transition-all border border-border shadow-xs"
            title={isPlaying ? 'Pause auto-scrubbing' : 'Play 48h forecast scrubbing'}
          >
            {isPlaying ? (
              <>
                <Pause className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
                <span>Pause</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 text-emerald-500 fill-emerald-500" />
                <span>Animate</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={() => setHeatmapHour(Math.min(47, heatmapHour + 1))}
            disabled={heatmapHour >= 47}
            className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-30 rounded-lg transition-colors"
            title="Step Forward 1 Hour"
          >
            <ChevronRight className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => setPlaybackSpeed(playbackSpeed === 1 ? 2 : 1)}
            className="px-1.5 py-1 text-[11px] font-bold text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors"
            title="Change Playback Speed"
          >
            {playbackSpeed}x
          </button>
        </div>
      </div>

      {/* Main Slider & Timestamp Section */}
      <div className="py-2.5 space-y-2">
        <div className="flex items-center justify-between text-xs font-medium">
          <div className="flex items-baseline gap-2">
            <span className="font-extrabold text-sm text-primary tracking-tight">
              +{heatmapHour}h
            </span>
            <span className="text-muted-foreground font-medium">
              {format(currentDate, 'EEE, MMM d • h:mm a')}
            </span>
            {heatmapHour === 0 && (
              <span className="text-[10px] font-bold bg-primary/10 text-primary px-1.5 py-0.5 rounded-sm">
                Departure
              </span>
            )}
          </div>

          {/* Corridor Peak Stats at Current Hour */}
          <div className="flex items-center gap-2 text-[11px]">
            <span className="text-muted-foreground">Corridor Peak:</span>
            <RiskBadge level={maxRisk} size="sm" />
            <span className="font-semibold text-foreground/80">{maxWind.toFixed(0)} mph</span>
            {(maxRain > 0 || maxSnow > 0) && (
              <span className="text-blue-500 font-semibold">
                {maxSnow > 0 ? `${maxSnow.toFixed(1)}" snow` : `${maxRain.toFixed(2)}" rain`}
              </span>
            )}
          </div>
        </div>

        {/* 0-48 Hour Slider */}
        <div className="relative flex items-center">
          <input
            type="range"
            min={0}
            max={47}
            step={1}
            value={heatmapHour}
            onChange={(e) => setHeatmapHour(parseInt(e.target.value, 10))}
            className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary focus:outline-hidden focus:ring-2 focus:ring-primary/40"
          />
        </div>

        {/* Quick-Jump Milestone Buttons */}
        <div className="flex justify-between items-center text-[10px] text-muted-foreground font-semibold px-0.5">
          {[0, 12, 24, 36, 47].map((h) => (
            <button
              key={h}
              type="button"
              onClick={() => setHeatmapHour(h)}
              className={`hover:text-primary transition-colors cursor-pointer ${
                heatmapHour === h ? 'text-primary font-black scale-105' : ''
              }`}
            >
              {h === 0 ? '0h (Start)' : `+${h}h`}
            </button>
          ))}
        </div>
      </div>

      {/* Heatmap Legend Bar */}
      <div className="pt-2 border-t border-border/60 flex items-center justify-between text-[10px] text-muted-foreground">
        <span className="font-medium flex items-center gap-1">
          {heatmapMetric === 'risk' && <Flame className="w-3 h-3 text-orange-500" />}
          {heatmapMetric === 'wind' && <Gauge className="w-3 h-3 text-sky-500" />}
          {heatmapMetric === 'precip' && <CloudRain className="w-3 h-3 text-blue-500" />}
          {heatmapMetric === 'risk'
            ? 'Risk Scale'
            : heatmapMetric === 'wind'
              ? 'Wind Speed (mph)'
              : 'Precipitation Intensity'}
        </span>

        {heatmapMetric === 'risk' ? (
          <div className="flex items-center gap-1.5">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500" /> Low
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-yellow-500" /> Mod
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-orange-500" /> High
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-red-500" /> Severe
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-purple-900" /> No Travel
            </span>
          </div>
        ) : heatmapMetric === 'wind' ? (
          <div className="flex items-center gap-1.5">
            <span>&lt; 25 mph</span>
            <div className="w-20 h-1.5 rounded-full bg-linear-to-r from-emerald-400 via-sky-400 to-red-500" />
            <span>&gt; 55 mph</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5">
            <span>Trace</span>
            <div className="w-20 h-1.5 rounded-full bg-linear-to-r from-cyan-300 via-blue-500 to-indigo-700" />
            <span>&gt; 1.0 in/h</span>
          </div>
        )}
      </div>
    </div>
  )
}
