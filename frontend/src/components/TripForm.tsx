import { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2, MapPin, Navigation, Sparkles, Weight } from 'lucide-react'
import { useGeocodeQuery } from '@/api/hooks'
import type { GeocodingResult, LatLng, TripRequest } from '@/features/trip/types'

const tripSchema = z.object({
  originLabel: z.string().min(2, 'Origin is required'),
  originLat: z.number(),
  originLng: z.number(),
  destinationLabel: z.string().min(2, 'Destination is required'),
  destinationLat: z.number(),
  destinationLng: z.number(),
  departureTime: z.string().min(1, 'Departure time is required'),
  loadWeightLb: z.number().min(0, 'Weight must be positive').max(150000, 'Weight exceeds limit'),
  checkpointIntervalMiles: z.union([z.literal(10), z.literal(25), z.literal(50)]),
})

type TripFormValues = z.infer<typeof tripSchema>

interface TripFormProps {
  onSubmit: (trip: TripRequest) => void
  isLoading: boolean
}

// Default departure time formatted for datetime-local input (tomorrow at 08:00 AM)
function getDefaultDepartureTime(): string {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  d.setHours(8, 0, 0, 0)
  return d.toISOString().slice(0, 16)
}

export function TripForm({ onSubmit, isLoading }: TripFormProps) {
  const [originQuery, setOriginQuery] = useState('Chicago, IL')
  const [destQuery, setDestQuery] = useState('Denver, CO')
  const [showOriginSuggestions, setShowOriginSuggestions] = useState(false)
  const [showDestSuggestions, setShowDestSuggestions] = useState(false)

  const { data: originSuggestions } = useGeocodeQuery(originQuery)
  const { data: destSuggestions } = useGeocodeQuery(destQuery)

  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors },
  } = useForm<TripFormValues>({
    resolver: zodResolver(tripSchema),
    defaultValues: {
      originLabel: 'Chicago, IL',
      originLat: 41.8781,
      originLng: -87.6298,
      destinationLabel: 'Denver, CO',
      destinationLat: 39.7392,
      destinationLng: -104.9903,
      departureTime: getDefaultDepartureTime(),
      loadWeightLb: 42000,
      checkpointIntervalMiles: 25,
    },
  })

  const currentInterval = useWatch({ control, name: 'checkpointIntervalMiles', defaultValue: 25 })
  const currentWeight = useWatch({ control, name: 'loadWeightLb', defaultValue: 42000 })

  const handleSelectOrigin = (loc: GeocodingResult) => {
    setValue('originLabel', loc.label)
    setValue('originLat', loc.lat)
    setValue('originLng', loc.lng)
    setOriginQuery(loc.label)
    setShowOriginSuggestions(false)
  }

  const handleSelectDest = (loc: GeocodingResult) => {
    setValue('destinationLabel', loc.label)
    setValue('destinationLat', loc.lat)
    setValue('destinationLng', loc.lng)
    setDestQuery(loc.label)
    setShowDestSuggestions(false)
  }

  const handleApplyPreset = (
    oLabel: string,
    oLat: number,
    oLng: number,
    dLabel: string,
    dLat: number,
    dLng: number,
    weight: number,
  ) => {
    setValue('originLabel', oLabel)
    setValue('originLat', oLat)
    setValue('originLng', oLng)
    setOriginQuery(oLabel)

    setValue('destinationLabel', dLabel)
    setValue('destinationLat', dLat)
    setValue('destinationLng', dLng)
    setDestQuery(dLabel)

    setValue('loadWeightLb', weight)
  }

  const onFormSubmit = (values: TripFormValues) => {
    const origin: LatLng = {
      lat: values.originLat,
      lng: values.originLng,
      label: values.originLabel,
    }
    const destination: LatLng = {
      lat: values.destinationLat,
      lng: values.destinationLng,
      label: values.destinationLabel,
    }

    onSubmit({
      origin,
      destination,
      departure_time: new Date(values.departureTime).toISOString(),
      load_weight_lb: values.loadWeightLb,
      checkpoint_interval_miles: values.checkpointIntervalMiles,
    })
  }

  return (
    <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-4">
      {/* Demo Preset Quick-Buttons */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
          <Sparkles className="w-3.5 h-3.5 text-amber-500" /> Presets:
        </span>
        <button
          type="button"
          onClick={() =>
            handleApplyPreset(
              'Chicago, IL',
              41.8781,
              -87.6298,
              'Denver, CO',
              39.7392,
              -104.9903,
              42000,
            )
          }
          className="text-xs bg-secondary hover:bg-muted text-secondary-foreground px-2 py-1 rounded-md border border-border transition-colors cursor-pointer"
        >
          Chicago → Denver
        </button>
        <button
          type="button"
          onClick={() =>
            handleApplyPreset(
              'Seattle, WA',
              47.6062,
              -122.3321,
              'Salt Lake City, UT',
              40.7608,
              -111.891,
              48000,
            )
          }
          className="text-xs bg-secondary hover:bg-muted text-secondary-foreground px-2 py-1 rounded-md border border-border transition-colors cursor-pointer"
        >
          Seattle → SLC
        </button>
      </div>

      {/* Origin Field */}
      <div className="relative">
        <label className="block text-xs font-semibold text-muted-foreground mb-1">
          Origin Address
        </label>
        <div className="relative flex items-center">
          <MapPin className="w-4 h-4 text-emerald-600 absolute left-3 pointer-events-none" />
          <input
            type="text"
            className="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-2 text-sm text-foreground focus:outline-hidden focus:ring-2 focus:ring-ring"
            value={originQuery}
            onChange={(e) => {
              setOriginQuery(e.target.value)
              setValue('originLabel', e.target.value)
              setShowOriginSuggestions(true)
            }}
            onFocus={() => setShowOriginSuggestions(true)}
            placeholder="Search origin..."
          />
        </div>
        {errors.originLabel && (
          <p className="text-xs text-destructive mt-1">{errors.originLabel.message}</p>
        )}

        {/* Origin Autocomplete Suggestions */}
        {showOriginSuggestions && originSuggestions && originSuggestions.length > 0 && (
          <ul className="absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-lg max-h-48 overflow-y-auto text-xs">
            {originSuggestions.map((s, idx) => (
              <li
                key={idx}
                onClick={() => handleSelectOrigin(s)}
                className="px-3 py-2 hover:bg-muted cursor-pointer border-b border-border/40 last:border-b-0"
              >
                {s.label}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Destination Field */}
      <div className="relative">
        <label className="block text-xs font-semibold text-muted-foreground mb-1">
          Destination Address
        </label>
        <div className="relative flex items-center">
          <Navigation className="w-4 h-4 text-rose-600 absolute left-3 pointer-events-none" />
          <input
            type="text"
            className="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-2 text-sm text-foreground focus:outline-hidden focus:ring-2 focus:ring-ring"
            value={destQuery}
            onChange={(e) => {
              setDestQuery(e.target.value)
              setValue('destinationLabel', e.target.value)
              setShowDestSuggestions(true)
            }}
            onFocus={() => setShowDestSuggestions(true)}
            placeholder="Search destination..."
          />
        </div>
        {errors.destinationLabel && (
          <p className="text-xs text-destructive mt-1">{errors.destinationLabel.message}</p>
        )}

        {/* Destination Autocomplete Suggestions */}
        {showDestSuggestions && destSuggestions && destSuggestions.length > 0 && (
          <ul className="absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-lg max-h-48 overflow-y-auto text-xs">
            {destSuggestions.map((s, idx) => (
              <li
                key={idx}
                onClick={() => handleSelectDest(s)}
                className="px-3 py-2 hover:bg-muted cursor-pointer border-b border-border/40 last:border-b-0"
              >
                {s.label}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Departure Date & Time */}
      <div>
        <label className="block text-xs font-semibold text-muted-foreground mb-1">
          Departure Date & Time
        </label>
        <input
          type="datetime-local"
          {...register('departureTime')}
          className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-hidden focus:ring-2 focus:ring-ring"
        />
        {errors.departureTime && (
          <p className="text-xs text-destructive mt-1">{errors.departureTime.message}</p>
        )}
      </div>

      {/* Load Weight */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
            <Weight className="w-3.5 h-3.5" /> Cargo Weight (lb)
          </label>
          <span className="text-xs font-bold text-foreground">
            {Number(currentWeight || 0).toLocaleString()} lb
          </span>
        </div>
        <input
          type="range"
          min="5000"
          max="80000"
          step="1000"
          {...register('loadWeightLb', { valueAsNumber: true })}
          className="w-full accent-primary cursor-pointer"
        />
        <div className="flex justify-between text-[10px] text-muted-foreground">
          <span>Light (&lt;30k)</span>
          <span>Medium (30k-40k)</span>
          <span>Heavy (&gt;40k lb)</span>
        </div>
      </div>

      {/* Checkpoint Sampling Interval (10 / 25 / 50 miles) */}
      <div>
        <label className="block text-xs font-semibold text-muted-foreground mb-1.5">
          Sampling Interval
        </label>
        <div className="grid grid-cols-3 gap-2">
          {([10, 25, 50] as const).map((interval) => (
            <button
              key={interval}
              type="button"
              onClick={() => setValue('checkpointIntervalMiles', interval)}
              className={`py-1.5 text-xs font-semibold rounded-lg border transition-all cursor-pointer ${
                currentInterval === interval
                  ? 'bg-primary text-primary-foreground border-primary shadow-xs'
                  : 'bg-secondary text-secondary-foreground border-border hover:bg-muted'
              }`}
            >
              Every {interval} mi
            </button>
          ))}
        </div>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-semibold py-2.5 px-4 rounded-lg shadow-md transition-colors flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
      >
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Analyzing Weather Routes...
          </>
        ) : (
          'Find Safest Route'
        )}
      </button>
    </form>
  )
}
