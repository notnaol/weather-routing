import { CheckCircle2, Clock, Navigation2, ShieldAlert } from 'lucide-react'
import { RiskBadge } from './RiskBadge'
import type { RouteAnalysis } from '@/features/trip/types'

interface RouteCardProps {
  route: RouteAnalysis
  isSelected: boolean
  isRecommended: boolean
  onSelect: (id: string) => void
}

function formatDuration(minutes: number): string {
  const hrs = Math.floor(minutes / 60)
  const mins = Math.round(minutes % 60)
  if (hrs === 0) return `${mins}m`
  return `${hrs}h ${mins}m`
}

export function RouteCard({
  route,
  isSelected,
  isRecommended,
  onSelect,
}: RouteCardProps) {
  const s = route.summary
  const hasNoTravel = s.no_travel_miles > 0

  return (
    <div
      onClick={() => onSelect(route.id)}
      className={`p-3.5 rounded-xl border transition-all cursor-pointer relative ${
        isSelected
          ? 'border-primary ring-2 ring-primary/20 bg-card shadow-md'
          : 'border-border bg-card/60 hover:bg-card hover:border-muted-foreground/30 shadow-xs'
      }`}
    >
      {/* Header with Title and Badges */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div>
          <div className="flex items-center gap-1.5">
            <h3 className="font-bold text-sm text-foreground">{route.name}</h3>
            {isRecommended && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-600 text-white shadow-xs">
                <CheckCircle2 className="w-3 h-3" /> Recommended
              </span>
            )}
            {hasNoTravel && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-700 text-white shadow-xs">
                <ShieldAlert className="w-3 h-3" /> Blocked
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
            <span className="flex items-center gap-1">
              <Navigation2 className="w-3 h-3" /> {route.distance_miles.toFixed(1)} mi
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" /> {formatDuration(route.duration_minutes)}
            </span>
          </div>
        </div>

        <div className="text-right">
          <RiskBadge level={Math.round(s.average_risk)} size="sm" />
          <div className="text-[10px] text-muted-foreground mt-0.5 font-medium">
            Avg Risk {s.average_risk.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Exposure Mileage Grid */}
      <div className="grid grid-cols-3 gap-1.5 pt-2 border-t border-border/60 text-center">
        <div className="bg-muted/50 rounded-md py-1 px-1">
          <div className="text-[10px] text-muted-foreground">Severe</div>
          <div
            className={`text-xs font-bold ${
              s.severe_miles > 0 ? 'text-rose-600' : 'text-emerald-600'
            }`}
          >
            {s.severe_miles.toFixed(1)} mi
          </div>
        </div>
        <div className="bg-muted/50 rounded-md py-1 px-1">
          <div className="text-[10px] text-muted-foreground">High</div>
          <div
            className={`text-xs font-bold ${
              s.high_miles > 0 ? 'text-amber-600' : 'text-emerald-600'
            }`}
          >
            {s.high_miles.toFixed(1)} mi
          </div>
        </div>
        <div className="bg-muted/50 rounded-md py-1 px-1">
          <div className="text-[10px] text-muted-foreground">No Travel</div>
          <div
            className={`text-xs font-bold ${
              s.no_travel_miles > 0 ? 'text-rose-800' : 'text-muted-foreground'
            }`}
          >
            {s.no_travel_miles.toFixed(1)} mi
          </div>
        </div>
      </div>
    </div>
  )
}
