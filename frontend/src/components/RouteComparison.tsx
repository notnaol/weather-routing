import { CheckCircle2 } from 'lucide-react'
import type { RouteAnalysis } from '@/features/trip/types'

interface RouteComparisonProps {
  routes: RouteAnalysis[]
  selectedRouteId: string | null
  recommendedRouteId: string | null
  onSelectRoute: (id: string) => void
}

export function RouteComparison({
  routes,
  selectedRouteId,
  recommendedRouteId,
  onSelectRoute,
}: RouteComparisonProps) {
  if (routes.length < 2) return null

  // Find minimums to highlight best values
  const minSevere = Math.min(...routes.map((r) => r.summary.severe_miles))
  const minHigh = Math.min(...routes.map((r) => r.summary.high_miles))
  const minAvgRisk = Math.min(...routes.map((r) => r.summary.average_risk))
  const minDuration = Math.min(...routes.map((r) => r.duration_minutes))

  return (
    <div className="border border-border rounded-xl overflow-hidden bg-card text-xs shadow-xs">
      <div className="bg-muted/70 px-3 py-2 font-semibold text-foreground flex items-center justify-between border-b border-border">
        <span>Route Comparison</span>
        <span className="text-[10px] text-muted-foreground font-normal">
          Best values highlighted
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead className="bg-muted/30 text-[10px] text-muted-foreground uppercase border-b border-border/50">
            <tr>
              <th className="py-2 px-3">Route</th>
              <th className="py-2 px-2 text-right">Severe</th>
              <th className="py-2 px-2 text-right">High</th>
              <th className="py-2 px-2 text-right">Avg Risk</th>
              <th className="py-2 px-3 text-right">Travel Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/40">
            {routes.map((r) => {
              const isSelected = r.id === selectedRouteId
              const isRec = r.id === recommendedRouteId
              const isBestSevere = r.summary.severe_miles === minSevere
              const isBestHigh = r.summary.high_miles === minHigh
              const isBestAvg = r.summary.average_risk === minAvgRisk
              const isBestDuration = r.duration_minutes === minDuration

              return (
                <tr
                  key={r.id}
                  onClick={() => onSelectRoute(r.id)}
                  className={`cursor-pointer transition-colors ${
                    isSelected ? 'bg-primary/10 font-semibold' : 'hover:bg-muted/40'
                  }`}
                >
                  <td className="py-2 px-3 flex items-center gap-1.5">
                    <span>{r.name}</span>
                    {isRec && (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 inline" />
                    )}
                  </td>
                  <td
                    className={`py-2 px-2 text-right ${
                      isBestSevere ? 'text-emerald-600 font-bold' : 'text-muted-foreground'
                    }`}
                  >
                    {r.summary.severe_miles.toFixed(1)} mi
                  </td>
                  <td
                    className={`py-2 px-2 text-right ${
                      isBestHigh ? 'text-emerald-600 font-bold' : 'text-muted-foreground'
                    }`}
                  >
                    {r.summary.high_miles.toFixed(1)} mi
                  </td>
                  <td
                    className={`py-2 px-2 text-right ${
                      isBestAvg ? 'text-emerald-600 font-bold' : 'text-muted-foreground'
                    }`}
                  >
                    {r.summary.average_risk.toFixed(2)}
                  </td>
                  <td
                    className={`py-2 px-3 text-right ${
                      isBestDuration ? 'text-emerald-600 font-bold' : 'text-muted-foreground'
                    }`}
                  >
                    {Math.round(r.duration_minutes)} min
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
