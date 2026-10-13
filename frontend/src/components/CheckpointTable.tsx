import { useState } from 'react'
import { ChevronDown, ChevronUp, CloudRain, CloudSnow, Wind } from 'lucide-react'
import { RiskBadge } from './RiskBadge'
import type { Checkpoint } from '@/features/trip/types'

interface CheckpointTableProps {
  checkpoints: Checkpoint[]
  routeName: string
  onSelectCheckpoint?: (cp: Checkpoint) => void
}

function formatEta(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

export function CheckpointTable({
  checkpoints,
  routeName,
  onSelectCheckpoint,
}: CheckpointTableProps) {
  const [isOpen, setIsOpen] = useState(false)

  if (!checkpoints || checkpoints.length === 0) return null

  return (
    <div className="border border-border rounded-xl overflow-hidden bg-card text-xs shadow-xs">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full bg-muted/60 px-3 py-2.5 font-semibold text-foreground flex items-center justify-between hover:bg-muted transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <span>{routeName} Checkpoints</span>
          <span className="text-[10px] bg-secondary text-secondary-foreground px-2 py-0.5 rounded-full font-medium">
            {checkpoints.length} stops
          </span>
        </div>
        {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {isOpen && (
        <div className="max-h-72 overflow-y-auto divide-y divide-border/40">
          {checkpoints.map((cp, idx) => (
            <div
              key={idx}
              onClick={() => onSelectCheckpoint?.(cp)}
              className="p-2.5 hover:bg-muted/40 transition-colors cursor-pointer space-y-1.5"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 font-semibold">
                  <span className="text-foreground">Mile {cp.mile.toFixed(1)}</span>
                  <span className="text-muted-foreground text-[10px]">
                    ETA {formatEta(cp.eta)}
                  </span>
                </div>
                <RiskBadge level={cp.risk} size="sm" />
              </div>

              {/* Weather Stats Row */}
              <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Wind className="w-3 h-3 text-sky-600" /> {cp.weather.wind_mph.toFixed(0)} mph
                </span>
                <span className="flex items-center gap-1">
                  <CloudRain className="w-3 h-3 text-blue-600" />{' '}
                  {cp.weather.rain_in_per_hr.toFixed(2)} in/h
                </span>
                <span className="flex items-center gap-1">
                  <CloudSnow className="w-3 h-3 text-cyan-600" />{' '}
                  {cp.weather.snow_in_per_hr.toFixed(2)} in/h
                </span>
                {cp.weather.temperature_f != null && (
                  <span>{Math.round(cp.weather.temperature_f)}°F</span>
                )}
              </div>

              {/* Reason */}
              <div className="text-[10px] text-muted-foreground italic bg-muted/40 px-2 py-1 rounded-sm">
                {cp.reason}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
