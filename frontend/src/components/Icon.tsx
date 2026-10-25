import back from '../assets/icons/back.png'
import calendar from '../assets/icons/calendar.png'
import cloud from '../assets/icons/cloud.png'
import drizzle from '../assets/icons/drizzle.png'
import fog from '../assets/icons/fog.png'
import forward from '../assets/icons/forward.png'
import partlyCloudy from '../assets/icons/partly-cloudy.png'
import print from '../assets/icons/print.png'
import rain from '../assets/icons/rain.png'
import share from '../assets/icons/share.png'
import showers from '../assets/icons/showers.png'
import snow from '../assets/icons/snow.png'
import storm from '../assets/icons/storm.png'
import sun from '../assets/icons/sun.png'

const ICONS = {
  back,
  calendar,
  cloud,
  drizzle,
  fog,
  forward,
  partlyCloudy,
  print,
  rain,
  share,
  showers,
  snow,
  storm,
  sun,
}

export type IconName = keyof typeof ICONS

export function Icon({ name, className = 'h-4 w-4' }: { name: IconName; className?: string }) {
  const url = `url(${ICONS[name]})`
  return (
    <span
      aria-hidden="true"
      className={`inline-block shrink-0 bg-current align-[-0.15em] [print-color-adjust:exact] ${className}`}
      style={{
        maskImage: url,
        WebkitMaskImage: url,
        maskSize: 'contain',
        WebkitMaskSize: 'contain',
        maskRepeat: 'no-repeat',
        WebkitMaskRepeat: 'no-repeat',
        maskPosition: 'center',
        WebkitMaskPosition: 'center',
      }}
    />
  )
}

export function weatherIcon(code: number | null | undefined): IconName | null {
  if (code == null) return null
  if (code === 0) return 'sun'
  if (code <= 2) return 'partlyCloudy'
  if (code === 3) return 'cloud'
  if (code >= 45 && code <= 48) return 'fog'
  if (code >= 51 && code <= 57) return 'drizzle'
  if (code >= 61 && code <= 67) return 'rain'
  if (code >= 71 && code <= 77) return 'snow'
  if (code >= 80 && code <= 82) return 'showers'
  if (code >= 85 && code <= 86) return 'snow'
  if (code >= 95) return 'storm'
  return null
}
