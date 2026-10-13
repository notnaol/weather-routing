import { useEffect, useMemo, useRef, useState } from 'react'
import Map, {
  Layer,
  Marker,
  NavigationControl,
  Popup,
  Source,
  type MapRef,
} from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
import { CloudRain, CloudSnow, Wind } from 'lucide-react'
import { decodePolyline } from '@/lib/polyline'
import { RiskLevel, RISK_COLORS } from '@/lib/risk-colors'
import { RiskBadge } from './RiskBadge'
import type { Checkpoint, HeatmapResponse, RouteAnalysis } from '@/features/trip/types'

interface TripMapProps {
  routes: RouteAnalysis[]
  selectedRouteId: string | null
  onSelectRoute: (id: string) => void
  activeCheckpoint?: Checkpoint | null
  heatmapData?: HeatmapResponse | null
  heatmapHour?: number
  heatmapVisible?: boolean
  heatmapMetric?: 'risk' | 'wind' | 'precip'
}

interface SelectedHeatmapPoint {
  lng: number
  lat: number
  risk: number
  wind: number
  rain: number
  snow: number
}

const MAP_STYLE = 'https://tiles.openfreemap.org/styles/liberty'

export function TripMap({
  routes,
  selectedRouteId,
  onSelectRoute,
  activeCheckpoint,
  heatmapData,
  heatmapHour = 0,
  heatmapVisible = true,
  heatmapMetric = 'risk',
}: TripMapProps) {
  const mapRef = useRef<MapRef | null>(null)
  const [clickedCheckpoint, setClickedCheckpoint] = useState<Checkpoint | null>(null)
  const [selectedHeatmapPt, setSelectedHeatmapPt] = useState<SelectedHeatmapPoint | null>(null)

  // Derived selected checkpoint (active takes precedence)
  const selectedCheckpoint = activeCheckpoint ?? clickedCheckpoint


  // Decode polylines into GeoJSON FeatureCollection for each route
  const routeGeoJsons = useMemo(() => {
    return routes.map((r) => {
      const coords = decodePolyline(r.geometry)
      return {
        id: r.id,
        name: r.name,
        isSelected: r.id === selectedRouteId,
        geojson: {
          type: 'Feature' as const,
          properties: { id: r.id, name: r.name },
          geometry: {
            type: 'LineString' as const,
            coordinates: coords,
          },
        },
      }
    })
  }, [routes, selectedRouteId])

  // Fit bounds to selected route or all routes
  useEffect(() => {
    if (!mapRef.current || routes.length === 0) return

    const selectedRoute = routes.find((r) => r.id === selectedRouteId) || routes[0]
    if (!selectedRoute) return

    const coords = decodePolyline(selectedRoute.geometry)
    if (coords.length === 0) return

    let minLng = coords[0][0]
    let maxLng = coords[0][0]
    let minLat = coords[0][1]
    let maxLat = coords[0][1]

    for (const [lng, lat] of coords) {
      if (lng < minLng) minLng = lng
      if (lng > maxLng) maxLng = lng
      if (lat < minLat) minLat = lat
      if (lat > maxLat) maxLat = lat
    }

    mapRef.current.fitBounds(
      [
        [minLng, minLat],
        [maxLng, maxLat],
      ],
      { padding: 70, duration: 1200 },
    )
  }, [routes, selectedRouteId])

  // Build GeoJSON FeatureCollection for Corridor Weather Heatmap
  const heatmapGeoJson = useMemo(() => {
    if (!heatmapData || !heatmapData.points || heatmapData.points.length === 0) {
      return null
    }

    const hour = Math.max(0, Math.min(47, heatmapHour))
    const risks = heatmapData.risk[hour] || []
    const winds = heatmapData.weather.wind[hour] || []
    const rains = heatmapData.weather.rain[hour] || []
    const snows = heatmapData.weather.snow[hour] || []

    const features = heatmapData.points.map((pt, idx) => {
      const risk = risks[idx] ?? 0
      const wind = winds[idx] ?? 0
      const rain = rains[idx] ?? 0
      const snow = snows[idx] ?? 0

      let weight = 0.1
      if (heatmapMetric === 'wind') {
        weight = Math.min(1.0, Math.max(0.08, wind / 55.0))
      } else if (heatmapMetric === 'precip') {
        const precipVal = Math.max(rain, snow / 2.5)
        weight = Math.min(1.0, Math.max(0.08, precipVal / 1.0))
      } else {
        weight = Math.min(1.0, Math.max(0.12, (risk + 1) / 5.0))
      }

      return {
        type: 'Feature' as const,
        geometry: {
          type: 'Point' as const,
          coordinates: [pt.lng, pt.lat] as [number, number],
        },
        properties: {
          id: idx,
          risk,
          wind,
          rain,
          snow,
          weight,
        },
      }
    })

    return {
      type: 'FeatureCollection' as const,
      features,
    }
  }, [heatmapData, heatmapHour, heatmapMetric])

  // Select dynamic color ramp based on chosen metric
  const heatmapColorRamp = useMemo(() => {
    if (heatmapMetric === 'wind') {
      return [
        'interpolate',
        ['linear'],
        ['heatmap-density'],
        0,
        'rgba(0, 0, 0, 0)',
        0.2,
        'rgba(56, 189, 248, 0.45)', // Sky blue
        0.4,
        'rgba(14, 165, 233, 0.7)', // Cyan
        0.65,
        'rgba(234, 179, 8, 0.85)', // Yellow / Caution
        0.85,
        'rgba(249, 115, 22, 0.92)', // Orange
        1.0,
        'rgba(239, 68, 68, 0.98)', // Red gale
      ]
    }
    if (heatmapMetric === 'precip') {
      return [
        'interpolate',
        ['linear'],
        ['heatmap-density'],
        0,
        'rgba(0, 0, 0, 0)',
        0.2,
        'rgba(103, 232, 249, 0.45)', // Light cyan
        0.45,
        'rgba(59, 130, 246, 0.72)', // Blue
        0.7,
        'rgba(99, 102, 241, 0.88)', // Indigo
        1.0,
        'rgba(147, 51, 234, 0.98)', // Deep purple
      ]
    }
    // Default: Risk scale (Emerald -> Yellow -> Orange -> Red -> Maroon)
    return [
      'interpolate',
      ['linear'],
      ['heatmap-density'],
      0,
      'rgba(0, 0, 0, 0)',
      0.18,
      'rgba(34, 197, 94, 0.45)', // Low (green)
      0.38,
      'rgba(234, 179, 8, 0.7)', // Moderate (yellow)
      0.6,
      'rgba(249, 115, 22, 0.85)', // High (orange)
      0.8,
      'rgba(239, 68, 68, 0.92)', // Severe (red)
      1.0,
      'rgba(88, 28, 135, 0.98)', // No Travel (purple)
    ]
  }, [heatmapMetric])

  const currentRoute = routes.find((r) => r.id === selectedRouteId) || routes[0]
  const checkpoints = currentRoute ? currentRoute.checkpoints : []
  const interactiveLayerIds = [
    ...routeGeoJsons.map((r) => `route-line-${r.id}`),
    ...(heatmapVisible && heatmapGeoJson ? ['corridor-heatmap-points'] : []),
  ]

  const firstRouteId = routeGeoJsons[0]?.id

  return (
    <div className="relative w-full h-full">
      <Map
        ref={mapRef}
        initialViewState={{
          longitude: -98.5795,
          latitude: 39.8283,
          zoom: 4,
        }}
        mapStyle={MAP_STYLE}
        style={{ width: '100%', height: '100%' }}
        interactiveLayerIds={interactiveLayerIds}
        onClick={(e) => {
          const feature = e.features?.[0]
          if (!feature) return

          if (feature.layer?.id === 'corridor-heatmap-points' && feature.properties) {
            const p = feature.properties
            const coords = (feature.geometry as { coordinates: [number, number] }).coordinates
            setSelectedHeatmapPt({
              lng: coords[0],
              lat: coords[1],
              risk: Number(p.risk),
              wind: Number(p.wind),
              rain: Number(p.rain),
              snow: Number(p.snow),
            })
            return
          }

          if (feature.properties?.id && feature.layer?.id.startsWith('route-line-')) {
            onSelectRoute(feature.properties.id as string)
          }
        }}
      >
        <NavigationControl position="top-right" />

        {/* 0-48 Hour Weather Corridor Heatmap Layer (Placed beneath route lines) */}
        {heatmapVisible && heatmapGeoJson && (
          <Source id="corridor-heatmap-src" type="geojson" data={heatmapGeoJson}>
            {/* Smooth GPU Heatmap layer */}
            <Layer
              id="corridor-heatmap-blur"
              type="heatmap"
              beforeId={firstRouteId ? `route-line-${firstRouteId}` : undefined}
              paint={{
                'heatmap-weight': ['get', 'weight'],
                'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 0, 1.2, 9, 3.2],
                'heatmap-color': heatmapColorRamp as unknown as any,
                'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 2, 22, 6, 48, 10, 80],
                'heatmap-opacity': 0.78,
              }}
            />

            {/* Clickable corridor sample points layer */}
            <Layer
              id="corridor-heatmap-points"
              type="circle"
              minzoom={5.5}
              paint={{
                'circle-radius': ['interpolate', ['linear'], ['zoom'], 5.5, 3.5, 9, 6.5],
                'circle-color': [
                  'interpolate',
                  ['linear'],
                  ['get', 'risk'],
                  0,
                  '#22c55e',
                  1,
                  '#eab308',
                  2,
                  '#f97316',
                  3,
                  '#ef4444',
                  4,
                  '#581c87',
                ],
                'circle-stroke-width': 1.5,
                'circle-stroke-color': '#ffffff',
                'circle-opacity': 0.85,
              }}
            />
          </Source>
        )}

        {/* Route Lines */}
        {routeGeoJsons.map((item) => (
          <Source key={item.id} id={`route-source-${item.id}`} type="geojson" data={item.geojson}>
            <Layer
              id={`route-line-${item.id}`}
              type="line"
              layout={{
                'line-join': 'round',
                'line-cap': 'round',
              }}
              paint={{
                'line-color': item.isSelected ? '#2563eb' : '#64748b',
                'line-width': item.isSelected ? 5.5 : 3.5,
                'line-opacity': item.isSelected ? 0.95 : 0.45,
              }}
            />
          </Source>
        ))}

        {/* Checkpoint Markers for the active route */}
        {checkpoints.map((cp, idx) => {
          const color = RISK_COLORS[cp.risk as RiskLevel] ?? '#22c55e'
          const isSelected = selectedCheckpoint?.mile === cp.mile

          return (
            <Marker
              key={`${cp.mile}-${idx}`}
              longitude={cp.lng}
              latitude={cp.lat}
              anchor="center"
              onClick={(e) => {
                e.originalEvent.stopPropagation()
                setClickedCheckpoint(cp)
              }}
            >
              <div
                className={`flex items-center justify-center rounded-full cursor-pointer transition-transform shadow-md ${
                  isSelected ? 'scale-130 ring-3 ring-white' : 'hover:scale-120'
                }`}
                style={{
                  backgroundColor: color,
                  width: idx === 0 || idx === checkpoints.length - 1 ? '18px' : '14px',
                  height: idx === 0 || idx === checkpoints.length - 1 ? '18px' : '14px',
                  border: '2px solid #ffffff',
                }}
                title={`Mile ${cp.mile.toFixed(1)} - Risk: ${cp.risk}`}
              />
            </Marker>
          )
        })}

        {/* Checkpoint Weather Popup */}
        {selectedCheckpoint && (
          <Popup
            longitude={selectedCheckpoint.lng}
            latitude={selectedCheckpoint.lat}
            anchor="bottom"
            onClose={() => setClickedCheckpoint(null)}
            closeOnClick={false}
            offset={14}
            className="z-50"
          >
            <div className="p-1 max-w-xs text-xs space-y-2">
              <div className="flex items-center justify-between gap-2 border-b border-border pb-1">
                <span className="font-bold text-foreground">
                  Mile {selectedCheckpoint.mile.toFixed(1)}
                </span>
                <RiskBadge level={selectedCheckpoint.risk} size="sm" />
              </div>

              <div className="text-[11px] text-muted-foreground font-medium">
                ETA:{' '}
                {new Date(selectedCheckpoint.eta).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                  month: 'short',
                  day: 'numeric',
                })}
              </div>

              {/* Weather Parameters */}
              <div className="grid grid-cols-2 gap-1.5 bg-muted/60 p-1.5 rounded-md text-[11px]">
                <div className="flex items-center gap-1">
                  <Wind className="w-3.5 h-3.5 text-sky-600" />
                  <span>{selectedCheckpoint.weather.wind_mph.toFixed(0)} mph</span>
                </div>
                <div className="flex items-center gap-1">
                  <CloudRain className="w-3.5 h-3.5 text-blue-600" />
                  <span>{selectedCheckpoint.weather.rain_in_per_hr.toFixed(2)} in/h</span>
                </div>
                <div className="flex items-center gap-1">
                  <CloudSnow className="w-3.5 h-3.5 text-cyan-600" />
                  <span>{selectedCheckpoint.weather.snow_in_per_hr.toFixed(2)} in/h</span>
                </div>
                {selectedCheckpoint.weather.temperature_f != null && (
                  <div>{Math.round(selectedCheckpoint.weather.temperature_f)}°F</div>
                )}
              </div>

              {/* Plain-English Reason */}
              <div className="text-[10px] text-muted-foreground italic bg-background p-1.5 rounded-sm border border-border/50">
                {selectedCheckpoint.reason}
              </div>
            </div>
          </Popup>
        )}

        {/* Corridor Heatmap Point Popup */}
        {selectedHeatmapPt && (
          <Popup
            longitude={selectedHeatmapPt.lng}
            latitude={selectedHeatmapPt.lat}
            anchor="bottom"
            onClose={() => setSelectedHeatmapPt(null)}
            closeOnClick={false}
            offset={12}
            className="z-50"
          >
            <div className="p-1 max-w-xs text-xs space-y-2">
              <div className="flex items-center justify-between gap-2 border-b border-border pb-1">
                <span className="font-bold text-foreground">Corridor Sensor Point</span>
                <RiskBadge level={selectedHeatmapPt.risk} size="sm" />
              </div>

              <div className="text-[11px] text-muted-foreground font-medium">
                Forecast Hour: +{heatmapHour}h
              </div>

              <div className="grid grid-cols-2 gap-1.5 bg-muted/60 p-1.5 rounded-md text-[11px]">
                <div className="flex items-center gap-1">
                  <Wind className="w-3.5 h-3.5 text-sky-600" />
                  <span>{selectedHeatmapPt.wind.toFixed(0)} mph</span>
                </div>
                <div className="flex items-center gap-1">
                  <CloudRain className="w-3.5 h-3.5 text-blue-600" />
                  <span>{selectedHeatmapPt.rain.toFixed(2)} in/h</span>
                </div>
                <div className="flex items-center gap-1">
                  <CloudSnow className="w-3.5 h-3.5 text-cyan-600" />
                  <span>{selectedHeatmapPt.snow.toFixed(2)} in/h</span>
                </div>
              </div>
            </div>
          </Popup>
        )}
      </Map>
    </div>
  )
}
