/**
 * Risk level definitions and color mapping.
 * Must stay in sync with the backend risk engine.
 */

export enum RiskLevel {
  Low = 0,
  Moderate = 1,
  High = 2,
  Severe = 3,
  NoTravel = 4,
}

export const RISK_LABELS: Record<RiskLevel, string> = {
  [RiskLevel.Low]: 'Low',
  [RiskLevel.Moderate]: 'Moderate',
  [RiskLevel.High]: 'High',
  [RiskLevel.Severe]: 'Severe',
  [RiskLevel.NoTravel]: 'No Travel',
}

export const RISK_COLORS: Record<RiskLevel, string> = {
  [RiskLevel.Low]: '#22c55e',
  [RiskLevel.Moderate]: '#eab308',
  [RiskLevel.High]: '#f97316',
  [RiskLevel.Severe]: '#ef4444',
  [RiskLevel.NoTravel]: '#7f1d1d',
}

export const RISK_BG_CLASSES: Record<RiskLevel, string> = {
  [RiskLevel.Low]: 'bg-risk-low',
  [RiskLevel.Moderate]: 'bg-risk-moderate',
  [RiskLevel.High]: 'bg-risk-high',
  [RiskLevel.Severe]: 'bg-risk-severe',
  [RiskLevel.NoTravel]: 'bg-risk-no-travel',
}

export function getWorstRiskLevel(levels: (RiskLevel | number)[]): RiskLevel {
  if (!levels.length) return RiskLevel.Low
  return Math.max(...levels) as RiskLevel
}

