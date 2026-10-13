import { RiskLevel, RISK_COLORS, RISK_LABELS } from '@/lib/risk-colors'

export function RiskLegend() {
  const levels = [
    RiskLevel.Low,
    RiskLevel.Moderate,
    RiskLevel.High,
    RiskLevel.Severe,
    RiskLevel.NoTravel,
  ]

  return (
    <div className="bg-card/90 backdrop-blur-xs border border-border rounded-lg p-2.5 shadow-md text-xs">
      <div className="font-semibold text-foreground mb-1.5 flex items-center justify-between">
        <span>Weather Risk Scale</span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {levels.map((lvl) => (
          <div key={lvl} className="flex items-center gap-1.5">
            <span
              className="inline-block w-3 h-3 rounded-full shadow-xs"
              style={{ backgroundColor: RISK_COLORS[lvl] }}
            />
            <span className="font-medium text-muted-foreground">{RISK_LABELS[lvl]}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
