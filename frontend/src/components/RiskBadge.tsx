import { RiskLevel, RISK_COLORS, RISK_LABELS } from '@/lib/risk-colors'

interface RiskBadgeProps {
  level: RiskLevel | number
  className?: string
  size?: 'sm' | 'md'
}

export function RiskBadge({ level, className = '', size = 'md' }: RiskBadgeProps) {
  const safeLevel = (level in RiskLevel ? level : RiskLevel.Low) as RiskLevel
  const label = RISK_LABELS[safeLevel] ?? 'Unknown'
  const color = RISK_COLORS[safeLevel] ?? '#737373'

  const sizeClasses =
    size === 'sm' ? 'px-1.5 py-0.5 text-xs font-semibold' : 'px-2.5 py-1 text-xs font-bold'

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full text-white shadow-xs ${sizeClasses} ${className}`}
      style={{ backgroundColor: color }}
    >
      {label}
    </span>
  )
}
