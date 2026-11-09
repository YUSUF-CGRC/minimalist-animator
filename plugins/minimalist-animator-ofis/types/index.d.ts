export type Mesaj = { zaman: string; kim: string; metin: string }

export type Kayit = { zaman: string; ajan: string; proje: string; metin: string }

export type HafizaNotu = { baslik: string; ozet: string }

export type AjanDurum = {
  id: string
  ad: string
  ikon: string
  rol: string
  calisiyor: boolean
  aciklama: string
  son: Kayit | null
  gecmis: Kayit[]
  hafiza: HafizaNotu[]
  sohbet: Mesaj[]
  cevapBekliyor: boolean
}

export type Proje = {
  id: string
  baslik: string
  asama: string
  mod: string
  adim: number
  toplam: number
  kullaniciBekleniyor: boolean
  video: string | null
  paket: string | null
  sonNot: string
}

export type Bekleyen = { baslik: string; satirlar: string[] }

export type Kilit = { sahip: string; not: string; bitis: string }

export type Studyo = { marka: string; kullanici: string }

export type Veri = {
  zaman: number
  studyo: Studyo | null
  kilit: Kilit | null
  ajanlar: AjanDurum[]
  projeler: Proje[]
  bekleyen: Bekleyen | null
}

export type Gorunum =
  | { sayfa: 'ana' }
  | { sayfa: 'ajan'; ajan: string; sekme: 'konus' | 'gecmis' | 'hafiza' }
  | { sayfa: 'video'; proje: string }

declare module 'claude-code' {
  interface PluginState {
    'minimalist-animator-ofis': { veri: Veri | null; gorunum: Gorunum }
  }
}
