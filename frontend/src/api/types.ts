import type { components } from './schema'

type Schemas = components['schemas']

export type FrontPage = Schemas['FrontPage']
export type Event = Schemas['Event']
// Desativado: Lua e céu noturno
// export type Sky = Schemas['Sky']
// export type SkyObject = Schemas['SkyObject']
// export type Moon = Schemas['Moon']
export type Indicator = Schemas['Indicator']
export type Exchange = Schemas['Exchange']
export type Money = Schemas['Money']
export type Editorial = Schemas['Editorial']
export type Headline = Schemas['Headline']
export type ApiError = Schemas['ApiError']
export type Health = Schemas['Health']
export type Birth = Schemas['Birth']
export type City = Schemas['City']
export type Weather = Schemas['Weather']
export type HourlyPoint = Schemas['HourlyPoint']
