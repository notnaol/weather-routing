import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster, toast } from 'sonner'
import {
  AlertTriangle,
  CheckCircle2,
  ListFilter,
  Map as MapIcon,
  Navigation,
  RefreshCw,
  Route,
  Sparkles,
  Truck,
} from 'lucide-react'
import { useAnalyzeTripMutation, useHeatmapMutation } from '@/api/hooks'
import { CheckpointTable } from '@/components/CheckpointTable'
import { HeatmapControls } from '@/components/HeatmapControls'
import { RiskBadge } from '@/components/RiskBadge'
import { RiskLegend } from '@/components/RiskLegend'
import { RouteCard } from '@/components/RouteCard'
import { RouteComparison } from '@/components/RouteComparison'
import { TripForm } from '@/components/TripForm'
import { TripMap } from '@/components/TripMap'
import { useTripStore } from '@/features/trip/store'
import { RiskLevel } from '@/lib/risk-colors'
import type {
  Checkpoint,
  HeatmapResponse,
  TripAnalysisResponse,
  TripRequest,
} from '@/features/trip/types'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function MainTripPlanner() {
  const [analysis, setAnalysis] = useState<TripAnalysisResponse | null>(null)
  const [heatmapData, setHeatmapData] = useState<HeatmapResponse | null>(null)
  const [activeCheckpoint, setActiveCheckpoint] = useState<Checkpoint | null>(null)
  const [mobileTab, setMobileTab] = useState<'panel' | 'map'>('panel')

  const {
    selectedRouteId,
    setSelectedRoute,
    heatmapHour,
    heatmapVisible,
    heatmapMetric,
    setHeatmapHour,
  } = useTripStore()

  const analyzeMutation = useAnalyzeTripMutation()
  const heatmapMutation = useHeatmapMutation()

  const handleTripSubmit = async (request: TripRequest) => {
    try {
      setHeatmapHour(0)
      const result = await analyzeMutation.mutateAsync(request)
      setAnalysis(result)
      setSelectedRoute(result.recommended_route_id)
      setActiveCheckpoint(null)

      // On mobile screens, automatically transition to map view to see route geometry
      setMobileTab('map')

      toast.success('Weather route analysis complete!', {
        description: `Found ${result.routes.length} route options. Recommended: Route ${
          result.routes.find((r) => r.id === result.recommended_route_id)?.name || ''
        }`,
      })

      // Fetch 0-48h corridor heatmap in parallel
      heatmapMutation
        .mutateAsync({
          origin: request.origin,
          destination: request.destination,
          departure_time: request.departure_time,
          load_weight_lb: request.load_weight_lb,
        })
        .then((heatData) => {
          setHeatmapData(heatData)
        })
        .catch((err: unknown) => {
          console.error('Heatmap generation failed:', err)
          toast.error('Corridor heatmap failed to load', {
            description: err instanceof Error ? err.message : 'Unknown error',
          })
        })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to analyze routes'
      toast.error('Analysis failed', { description: message })
    }
  }

  const selectedRoute =
    analysis?.routes.find((r) => r.id === selectedRouteId) || analysis?.routes[0]

  return (
    <div className="flex flex-col md:flex-row h-screen w-screen overflow-hidden bg-background text-foreground font-sans">
      {/* Mobile Top Navigation Switcher */}
      <div className="md:hidden flex items-center justify-between p-3 border-b border-border bg-card/95 backdrop-blur-md z-30">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-primary text-primary-foreground rounded-md shadow-xs">
            <Truck className="w-4 h-4" />
          </div>
          <span className="font-bold text-sm">Weather Truck Routing</span>
        </div>

        {/* Mobile Tab Pills */}
        <div className="inline-flex bg-muted/80 p-0.5 rounded-lg border border-border text-xs font-semibold">
          <button
            type="button"
            onClick={() => setMobileTab('panel')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
              mobileTab === 'panel'
                ? 'bg-card text-foreground shadow-xs font-bold'
                : 'text-muted-foreground'
            }`}
          >
            <ListFilter className="w-3.5 h-3.5" />
            <span>Plan</span>
          </button>
          <button
            type="button"
            onClick={() => setMobileTab('map')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
              mobileTab === 'map'
                ? 'bg-card text-foreground shadow-xs font-bold'
                : 'text-muted-foreground'
            }`}
          >
            <MapIcon className="w-3.5 h-3.5" />
            <span>Map</span>
          </button>
        </div>
      </div>

      {/* Left Sidebar / Plan Panel */}
      <aside
        className={`w-full md:w-110 lg:w-120 border-r border-border bg-card flex-col h-full z-10 shadow-lg ${
          mobileTab === 'panel' ? 'flex' : 'hidden md:flex'
        }`}
      >
        {/* Desktop Top Header */}
        <div className="hidden md:flex p-4 border-b border-border bg-card/90 backdrop-blur-xs items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-primary text-primary-foreground rounded-lg shadow-xs">
              <Truck className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-extrabold text-base leading-tight">Weather Route Planner</h1>
              <p className="text-xs text-muted-foreground">Truck Routing & Weather Risk Engine</p>
            </div>
          </div>
          <span className="text-[10px] font-bold uppercase tracking-wider bg-secondary px-2 py-1 rounded-md text-secondary-foreground border border-border">
            HGV Profile
          </span>
        </div>

        {/* Sidebar Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Trip Parameters Input Form */}
          <div className="bg-background/80 p-3.5 rounded-xl border border-border shadow-xs">
            <TripForm onSubmit={handleTripSubmit} isLoading={analyzeMutation.isPending} />
          </div>

          {/* Loading Skeleton Panel */}
          {analyzeMutation.isPending && (
            <div className="bg-card/95 border border-primary/30 rounded-xl p-4 shadow-sm space-y-3.5 animate-pulse">
              <div className="flex items-center gap-2.5 text-primary font-bold text-xs">
                <RefreshCw className="w-4 h-4 animate-spin text-primary shrink-0" />
                <span>Evaluating Truck Routes & Weather Risks...</span>
              </div>
              <div className="space-y-2 text-[11px] text-muted-foreground">
                <div className="flex items-center justify-between">
                  <span>1. Requesting 3 alternative HGV routes</span>
                  <span className="text-primary font-semibold">Done</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>2. Sampling checkpoints & ETAs</span>
                  <span className="text-primary font-semibold">In Progress</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>3. Querying Open-Meteo forecasts & load rules</span>
                  <span className="text-muted-foreground">Queued</span>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 pt-1">
                <div className="h-14 bg-muted/60 rounded-lg" />
                <div className="h-14 bg-muted/60 rounded-lg" />
                <div className="h-14 bg-muted/60 rounded-lg" />
              </div>
            </div>
          )}

          {/* Error Banner with Recovery Tip */}
          {analyzeMutation.isError && (
            <div className="bg-destructive/10 border border-destructive/30 rounded-xl p-3.5 text-xs text-destructive space-y-2">
              <div className="flex items-center gap-2 font-bold">
                <AlertTriangle className="w-4 h-4 text-destructive shrink-0" />
                <span>Routing Analysis Could Not Complete</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                {analyzeMutation.error instanceof Error
                  ? analyzeMutation.error.message
                  : 'An upstream routing or weather provider error occurred.'}
              </p>
              <div className="pt-1 text-[11px] text-muted-foreground">
                Tip: Try choosing highway-connected origin and destination cities or click one of the
                demo presets above.
              </div>
            </div>
          )}

          {/* Empty State / Quick Rules Reference */}
          {!analysis && !analyzeMutation.isPending && (
            <div className="bg-muted/40 border border-border/70 rounded-xl p-3.5 text-xs space-y-3">
              <div className="flex items-center gap-2 font-bold text-foreground">
                <Sparkles className="w-4 h-4 text-primary" />
                <span>Risk & Truck Load Engine Rules</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Weather conditions are evaluated along 3 alternative route options sampled every 10,
                25, or 50 miles at the truck&apos;s forecasted arrival time.
              </p>
              <div className="space-y-1.5 text-[11px]">
                <div className="flex items-center justify-between p-2 bg-background rounded-lg border border-border/50">
                  <span className="font-semibold text-foreground">Wind &ge; 55 mph (Any load)</span>
                  <RiskBadge level={RiskLevel.NoTravel} size="sm" />
                </div>
                <div className="flex items-center justify-between p-2 bg-background rounded-lg border border-border/50">
                  <span className="font-semibold text-foreground">Wind &ge; 45 mph + &gt; 30,000 lb</span>
                  <RiskBadge level={RiskLevel.NoTravel} size="sm" />
                </div>
                <div className="flex items-center justify-between p-2 bg-background rounded-lg border border-border/50">
                  <span className="font-semibold text-foreground">Wind &ge; 35 mph + &gt; 40,000 lb</span>
                  <RiskBadge level={RiskLevel.Severe} size="sm" />
                </div>
              </div>
            </div>
          )}

          {/* Results Section */}
          {analysis && (
            <div className="space-y-3.5 pt-1">
              {/* Recommendation Callout Banner */}
              <div
                className={`p-3 rounded-xl border text-xs shadow-xs flex items-start gap-2.5 ${
                  analysis.all_routes_blocked
                    ? 'bg-amber-500/10 border-amber-500/30 text-amber-950 dark:text-amber-200'
                    : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-950 dark:text-emerald-200'
                }`}
              >
                {analysis.all_routes_blocked ? (
                  <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                ) : (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                )}
                <div className="space-y-0.5">
                  <div className="font-bold text-foreground">
                    {analysis.all_routes_blocked
                      ? 'Severe Conditions on All Routes'
                      : 'Recommended Route'}
                  </div>
                  <p className="text-muted-foreground text-[11px] leading-relaxed">
                    {analysis.recommendation_reason}
                  </p>
                </div>
              </div>

              {/* Route Alternatives Header */}
              <div className="flex items-center justify-between text-xs font-bold text-muted-foreground px-0.5">
                <span className="flex items-center gap-1.5">
                  <Route className="w-3.5 h-3.5" /> Available Routes ({analysis.routes.length})
                </span>
                <span className="text-[11px] font-normal">Click a card to select</span>
              </div>

              {/* Route Cards */}
              <div className="space-y-2">
                {analysis.routes.map((route) => (
                  <RouteCard
                    key={route.id}
                    route={route}
                    isSelected={route.id === selectedRouteId}
                    isRecommended={route.id === analysis.recommended_route_id}
                    onSelect={(id) => {
                      setSelectedRoute(id)
                      setActiveCheckpoint(null)
                    }}
                  />
                ))}
              </div>

              {/* Side-by-side Comparison Table */}
              <RouteComparison
                routes={analysis.routes}
                selectedRouteId={selectedRouteId}
                recommendedRouteId={analysis.recommended_route_id}
                onSelectRoute={(id) => setSelectedRoute(id)}
              />

              {/* Checkpoint Details for Selected Route */}
              {selectedRoute && (
                <CheckpointTable
                  checkpoints={selectedRoute.checkpoints}
                  routeName={selectedRoute.name}
                  onSelectCheckpoint={(cp) => {
                    setActiveCheckpoint(cp)
                    setMobileTab('map')
                  }}
                />
              )}
            </div>
          )}
        </div>
      </aside>

      {/* Main Map Canvas Area */}
      <main
        className={`flex-1 relative h-full w-full ${
          mobileTab === 'map' ? 'block' : 'hidden md:block'
        }`}
      >
        <TripMap
          routes={analysis ? analysis.routes : []}
          selectedRouteId={selectedRouteId}
          onSelectRoute={(id) => setSelectedRoute(id)}
          activeCheckpoint={activeCheckpoint}
          heatmapData={heatmapData}
          heatmapHour={heatmapHour}
          heatmapVisible={heatmapVisible}
          heatmapMetric={heatmapMetric}
        />

        {/* Floating Risk Legend on Top-Left */}
        <div className="absolute top-4 left-4 z-20">
          <RiskLegend />
        </div>

        {/* Floating 0-48 Hour Heatmap Scrubbing Controls at Bottom */}
        {(heatmapData || heatmapMutation.isPending) && (
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20">
            <HeatmapControls
              heatmapData={heatmapData}
              isLoading={heatmapMutation.isPending}
            />
          </div>
        )}

        {/* Empty state hint when no routes analyzed yet */}
        {!analysis && (
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 bg-card/90 backdrop-blur-xs border border-border rounded-xl px-4 py-2.5 shadow-lg text-xs flex items-center gap-2 text-muted-foreground">
            <Navigation className="w-4 h-4 text-primary animate-pulse" />
            <span>Enter origin, destination, and weight on the left to analyze routes</span>
          </div>
        )}
      </main>

      <Toaster position="top-right" richColors />
    </div>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MainTripPlanner />
    </QueryClientProvider>
  )
}

export default App
