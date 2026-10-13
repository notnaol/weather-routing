import { describe, expect, it } from 'vitest'
import { decodePolyline } from './polyline'

describe('decodePolyline', () => {
  it('decodes standard Google encoded polyline string to [lng, lat] pairs', () => {
    // Encodes: (38.5, -120.2), (40.7, -120.95), (43.252, -126.453)
    const encoded = '_p~iF~ps|U_ulLnnqC_mqNvxq`@'
    const coords = decodePolyline(encoded)

    expect(coords).toHaveLength(3)

    // Check [lng, lat] order for MapLibre/GeoJSON
    expect(coords[0][0]).toBeCloseTo(-120.2, 4)
    expect(coords[0][1]).toBeCloseTo(38.5, 4)

    expect(coords[1][0]).toBeCloseTo(-120.95, 4)
    expect(coords[1][1]).toBeCloseTo(40.7, 4)

    expect(coords[2][0]).toBeCloseTo(-126.453, 4)
    expect(coords[2][1]).toBeCloseTo(43.252, 4)
  })

  it('handles empty polyline gracefully', () => {
    const coords = decodePolyline('')
    expect(coords).toEqual([])
  })
})
