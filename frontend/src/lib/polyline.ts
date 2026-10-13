/**
 * Google Encoded Polyline decoder for client-side map rendering.
 */

export function decodePolyline(str: string, precision = 5): [number, number][] {
  const factor = Math.pow(10, precision)
  const coordinates: [number, number][] = [] // [lng, lat] for GeoJSON
  let index = 0
  let lat = 0
  let lng = 0
  const len = str.length

  while (index < len) {
    let shift = 0
    let result = 0
    let byte: number

    do {
      byte = str.charCodeAt(index++) - 63
      result |= (byte & 0x1f) << shift
      shift += 5
    } while (byte >= 0x20)

    const dLat = result & 1 ? ~(result >> 1) : result >> 1
    lat += dLat

    shift = 0
    result = 0
    do {
      byte = str.charCodeAt(index++) - 63
      result |= (byte & 0x1f) << shift
      shift += 5
    } while (byte >= 0x20)

    const dLng = result & 1 ? ~(result >> 1) : result >> 1
    lng += dLng

    // Return [lng, lat] for MapLibre/GeoJSON format
    coordinates.push([lng / factor, lat / factor])
  }

  return coordinates
}
