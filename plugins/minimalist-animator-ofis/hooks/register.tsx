import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { AjanDurum, Bekleyen, Gorunum, HafizaNotu, Kayit, Kilit, Mesaj, Proje, Studyo, Veri } from '../types'

// Minimalist Animatör stüdyosunun dosyaları: panel yalnızca okur; yazdığı tek şey kullanıcının mesajı
// (sirket/kullanici/sohbet/<ajan>.jsonl) ve panelden verilen senaryo metni (sirket/kullanici/metinler/).
const PANE = 'minimalist-animator-ofis'
const YENILEME_MS = 4000

const veri = atom({ plugin: 'minimalist-animator-ofis', key: 'veri' } as const, null)
const gorunum = atom({ plugin: 'minimalist-animator-ofis', key: 'gorunum' } as const, { sayfa: 'ana' } as Gorunum)

const AJANLAR = [
  { id: 'yonetici', ad: 'Yönetici', ikon: '🧭', rol: 'İşi planlar, ekibi yönlendirir, kaliteyi denetler' },
  { id: 'analist', ad: 'Analist', ikon: '📊', rol: 'Hesapları ve benzer kanalları izler, fikir önerir' },
  { id: 'arastirmaci', ad: 'Araştırmacı', ikon: '📚', rol: 'Konuyu kaynaklı araştırır, senaryoyu doğrular' },
  { id: 'senarist', ad: 'Senarist', ikon: '✍️', rol: 'Senaryoyu yazar ya da senin metnini sahneler' },
  { id: 'cizer', ad: 'Çizer', ikon: '🎨', rol: 'Görselleri hazırlar, temizler, arşivler' },
  { id: 'seslendirmen', ad: 'Seslendirmen', ikon: '🎙️', rol: 'Seslendirir, sesi satırlara böler' },
  { id: 'animator', ad: 'Animatör', ikon: '🎞️', rol: 'Görsel ve sesten videoyu kodla üretir' },
]

const ANA_YOL = [
  'brief', 'arastirma', 'senaryo', 'senaryo-kontrol', 'gorsel-hazirlik', 'ses-hazirlik', 'indirme-onayi',
  'indirme-isleme', 'animasyon', 'son-kontrol', 'kullanici-onayi', 'tamam', 'yayinlandi',
]

const ASAMA_AD: Record<string, string> = {
  brief: 'Brief',
  arastirma: 'Araştırma',
  senaryo: 'Senaryo',
  'senaryo-kontrol': 'Senaryo kontrolü',
  'gorsel-hazirlik': 'Görseller',
  'ses-hazirlik': 'Seslendirme',
  'indirme-onayi': 'İndirme onayı',
  'indirme-isleme': 'Dosyalar işleniyor',
  animasyon: 'Animasyon',
  'son-kontrol': 'Son kontrol',
  'kullanici-onayi': 'Senin onayın',
  revizyon: 'Revizyon',
  tamam: 'Tamam',
  yayinlandi: 'Yayınlandı',
  iptal: 'İptal',
  demo: 'Demo',
}

const MOD_AD: Record<string, string> = {
  ajan: 'senaryo: ekip',
  'kendi-arastir': 'senaryo: senin + öneri',
  'kendi-duzenle': 'senaryo: senin, düzenlenmiş',
  'kendi-aynen': 'senaryo: senin, aynen',
}

const CALISAN = new Set(['pending', 'running', 'waiting'])

let sonJson = ''

// ---------- okuma ----------

async function metinOku($: EngineInterface, yol: string): Promise<string | null> {
  try {
    return (await $.fs.read(yol)) as string
  } catch {
    return null
  }
}

async function jsonOku<T>($: EngineInterface, yol: string): Promise<T | null> {
  const metin = await metinOku($, yol)
  if (metin === null) return null
  try {
    return JSON.parse(metin) as T
  } catch {
    return null
  }
}

async function listele($: EngineInterface, yol: string) {
  try {
    return await $.fs.list(yol)
  } catch {
    return []
  }
}

// Sohbet kaydında ajan kimliği olmayan her yazar kullanıcıdır (ofis.py ile aynı kural).
function kullaniciMi(kim: string) {
  return kim !== '' && !AJANLAR.some(a => a.id === kim)
}

async function kokBul($: EngineInterface) {
  return (await $.session.root()).replace(/\\/g, '/').replace(/\/$/, '')
}

// Claude Code ana oturum hafızasını ~/.claude/projects/<kök yolunun harf-rakam dışı karakterleri '-'>/memory/ altında tutar.
async function yoneticiHafizasi($: EngineInterface, kok: string) {
  const ev = ((await $.env.get('USERPROFILE')) ?? (await $.env.get('HOME')) ?? '').replace(/\\/g, '/')
  if (!ev) return null
  return `${ev}/.claude/projects/${kok.replace(/[^A-Za-z0-9]/g, '-')}/memory/MEMORY.md`
}

function gunlukCoz(metin: string, proje: string): Kayit[] {
  const kayitlar: Kayit[] = []
  for (const satir of metin.split(/\r?\n/)) {
    const m = satir.match(/^- (\d{4}-\d{2}-\d{2}T\d{2}:\d{2})\S*\s+\*\*([^*]+)\*\*:\s*(.*)$/)
    if (m) kayitlar.push({ zaman: m[1] ?? '', ajan: (m[2] ?? '').trim(), proje, metin: kisalt(m[3] ?? '', 400) })
  }
  return kayitlar
}

function hafizaCoz(metin: string | null): HafizaNotu[] {
  if (!metin) return []
  const notlar: HafizaNotu[] = []
  for (const satir of metin.split(/\r?\n/)) {
    const m = satir.match(/^-\s*\[([^\]]+)\]\([^)]*\)\s*[—–-]?\s*(.*)$/)
    if (m) notlar.push({ baslik: m[1] ?? '', ozet: kisalt(m[2] ?? '', 300) })
  }
  return notlar
}

function sohbetCoz(metin: string | null): Mesaj[] {
  if (!metin) return []
  const mesajlar: Mesaj[] = []
  for (const satir of metin.split(/\r?\n/)) {
    if (!satir.trim()) continue
    try {
      const m = JSON.parse(satir) as Mesaj
      if (m && typeof m.metin === 'string') mesajlar.push(m)
    } catch {
      // bozuk satırı atla
    }
  }
  return mesajlar.slice(-30)
}

function bekleyenCoz(metin: string | null): Bekleyen | null {
  if (!metin) return null
  const satirlar = metin.split(/\r?\n/)
  const bas = satirlar.findIndex(s => s.startsWith('## '))
  const ilk = satirlar[bas] ?? ''
  if (bas < 0 || !(ilk.includes('BEKLİYOR') || ilk.includes('⏳'))) return null
  const govde: string[] = []
  for (const s of satirlar.slice(bas + 1)) {
    if (s.startsWith('## ') || s.trim() === '---') break
    const temiz = s.replace(/\*\*/g, '').trim()
    if (temiz) govde.push(kisalt(temiz, 220))
    if (govde.length >= 12) break
  }
  return { baslik: ilk.replace(/^##\s*/, '').replace(/\*\*/g, ''), satirlar: govde }
}

function kisalt(metin: string, uzunluk: number) {
  return metin.length > uzunluk ? `${metin.slice(0, uzunluk - 1)}…` : metin
}

async function studyoOku($: EngineInterface, kok: string): Promise<Studyo | null> {
  const ayar = await jsonOku<{ _tur?: string; marka?: { ad?: string }; kullanici?: { ad?: string } }>(
    $, `${kok}/ayarlar.json`)
  if (!ayar || ayar._tur !== 'minimalist-animator') return null
  return { marka: ayar.marka?.ad ?? '', kullanici: ayar.kullanici?.ad ?? '' }
}

async function topla($: EngineInterface): Promise<Veri> {
  const simdi = await $.clock.now()
  const kok = await kokBul($)
  const studyo = await studyoOku($, kok)
  if (!studyo) return { zaman: simdi, studyo: null, kilit: null, ajanlar: [], projeler: [], bekleyen: null }

  const kilitHam = await jsonOku<Kilit>($, `${kok}/sirket/.kilit.json`)
  const kilit = kilitHam && new Date(kilitHam.bitis).getTime() > simdi ? kilitHam : null

  const projeler: Proje[] = []
  const kayitlar: Kayit[] = []
  for (const g of await listele($, `${kok}/sirket/projeler`)) {
    if (g.kind !== 'dir') continue
    const klasor = `${kok}/sirket/projeler/${g.name}`
    const durum = await jsonOku<{
      baslik?: string
      asama?: string
      senaryo_modu?: string
      kullanici_bekleniyor?: boolean
      gecmis?: { not?: string }[]
    }>($, `${klasor}/durum.json`)
    const gunluk = await metinOku($, `${klasor}/gunluk.md`)
    if (gunluk) kayitlar.push(...gunlukCoz(gunluk, g.name))
    if (!durum || g.name.startsWith('0000-')) continue
    const asama = durum.asama ?? 'brief'
    if (asama === 'iptal') continue
    const cikti = await listele($, `${klasor}/cikti`)
    const video = cikti.find(d => d.kind === 'file' && d.name.endsWith('.mp4'))
    const paket = cikti.find(d => d.kind === 'file' && d.name === 'yayin-paketi.md')
    const yoldaki = asama === 'revizyon' ? 'son-kontrol' : asama
    const sira = ANA_YOL.indexOf(yoldaki)
    projeler.push({
      id: g.name,
      baslik: durum.baslik ?? g.name,
      asama,
      mod: durum.senaryo_modu ?? 'ajan',
      adim: sira < 0 ? 0 : sira + 1,
      toplam: ANA_YOL.length,
      kullaniciBekleniyor: !!durum.kullanici_bekleniyor,
      video: video ? `${klasor}/cikti/${video.name}` : null,
      paket: paket ? `${klasor}/cikti/${paket.name}` : null,
      sonNot: kisalt(durum.gecmis?.[durum.gecmis.length - 1]?.not ?? '', 240),
    })
  }
  projeler.sort((a, b) => b.id.localeCompare(a.id))
  kayitlar.sort((a, b) => b.zaman.localeCompare(a.zaman))

  let calisanlar: { type: string; description: string; status: string }[] = []
  try {
    calisanlar = (await $.agent.list()).filter(a => CALISAN.has(a.status))
  } catch {
    calisanlar = []
  }

  // Eklenti ajanlarının hafıza klasörünün adı kapsamlı olabilir (ör. "minimalist-animator-senarist"): sonekten bul.
  const hafizaKlasorleri = (await listele($, `${kok}/.claude/agent-memory`)).filter(d => d.kind === 'dir').map(d => d.name)
  const yoneticiYolu = await yoneticiHafizasi($, kok)

  const ajanlar: AjanDurum[] = []
  for (const a of AJANLAR) {
    const gecmis = kayitlar.filter(k => k.ajan === a.id).slice(0, 15)
    const klasor = hafizaKlasorleri.find(ad => ad === a.id || ad.endsWith(`-${a.id}`) || ad.endsWith(`:${a.id}`))
    const hafizaYolu = a.id === 'yonetici' ? yoneticiYolu : klasor ? `${kok}/.claude/agent-memory/${klasor}/MEMORY.md` : null
    const sohbet = sohbetCoz(await metinOku($, `${kok}/sirket/kullanici/sohbet/${a.id}.jsonl`))
    const calisan = calisanlar.find(c => c.type === a.id || c.type.endsWith(`:${a.id}`))
    const yoneticiCalisiyor = a.id === 'yonetici' && !!kilit
    ajanlar.push({
      ...a,
      calisiyor: !!calisan || yoneticiCalisiyor,
      aciklama: calisan?.description ?? (yoneticiCalisiyor ? kilit?.not ?? '' : ''),
      son: gecmis[0] ?? null,
      gecmis,
      hafiza: hafizaCoz(hafizaYolu ? await metinOku($, hafizaYolu) : null),
      sohbet,
      cevapBekliyor: kullaniciMi(sohbet.at(-1)?.kim ?? ''),
    })
  }

  const bekleyen = bekleyenCoz(await metinOku($, `${kok}/sirket/kullanici/onay-bekleyenler.md`))

  return { zaman: simdi, studyo, kilit, ajanlar, projeler, bekleyen }
}

async function yenile($: EngineInterface) {
  const yeni = await topla($)
  const json = JSON.stringify({ ...yeni, zaman: 0 })
  if (json === sonJson) return
  sonJson = json
  await update($, veri, () => yeni)
}

// ---------- eylemler ----------

function simdiDamga(ms: number) {
  const d = new Date(ms)
  const iki = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${iki(d.getMonth() + 1)}-${iki(d.getDate())}T${iki(d.getHours())}:${iki(d.getMinutes())}`
}

async function ekle($: EngineInterface, yol: string, satir: string) {
  const eski = (await metinOku($, yol)) ?? ''
  await $.fs.write(yol, `${eski}${eski && !eski.endsWith('\n') ? '\n' : ''}${satir}\n`)
}

async function gonder($: EngineInterface, ajanId: string, metin: string) {
  const temiz = metin.trim()
  if (!temiz) return
  const ajan = AJANLAR.find(a => a.id === ajanId)
  if (!ajan) return
  const kok = await kokBul($)
  const kayit: Mesaj = { zaman: simdiDamga(await $.clock.now()), kim: 'kullanici', metin: temiz }
  await ekle($, `${kok}/sirket/kullanici/sohbet/${ajanId}.jsonl`, JSON.stringify(kayit))
  await yenile($)
  const hedef = ajanId === 'yonetici' ? 'Yönetici (sana)' : ajan.ad
  void $.prompt.submit({
    text:
      `[Ofis paneli] Kullanıcı → ${hedef}: ${temiz}\n\n` +
      `(minimalist-animator:yonetici → "Ofis paneli mesajları". Cevabı \`ma ofis yanit ${ajanId} "<cevap>"\` ile panele yaz.)`,
  })
}

async function senaryoVer($: EngineInterface, metin: string) {
  const temiz = metin.trim()
  if (!temiz) return
  const kok = await kokBul($)
  const damga = simdiDamga(await $.clock.now()).replace(/[-:]/g, '').replace('T', '-')
  const yol = `${kok}/sirket/kullanici/metinler/${damga}_panel.md`
  await $.fs.write(yol, `${temiz}\n`)
  void $.prompt.submit({
    text:
      `[Ofis paneli] Kullanıcı kendi senaryosunu verdi: ${yol}\n\n` +
      '(minimalist-animator:senaryom skill\'iyle devam et: metne dokunma, alt modu — araştırıp öner / ' +
      'yalnızca anlaşılır yap / aynen kullan — ve video mu gönderi mi olacağını kullanıcıya sor.)',
  })
}

async function istek($: EngineInterface, metin: string) {
  void $.prompt.submit({ text: `[Ofis paneli] ${metin}` })
}

// ---------- çizim ----------

function saat(zaman: string) {
  const bugun = new Date()
  const iki = (n: number) => String(n).padStart(2, '0')
  const gun = `${bugun.getFullYear()}-${iki(bugun.getMonth() + 1)}-${iki(bugun.getDate())}`
  if (zaman.startsWith(gun)) return zaman.slice(11, 16)
  return `${zaman.slice(8, 10)}.${zaman.slice(5, 7)} ${zaman.slice(11, 16)}`
}

function cubuk(adim: number, toplam: number) {
  const dolu = Math.max(0, Math.min(toplam, adim))
  return '■'.repeat(dolu) + '□'.repeat(toplam - dolu)
}

async function baslik($: EngineInterface) {
  const studyo = await studyoOku($, await kokBul($))
  return studyo?.marka ? `${studyo.marka} Ofis` : 'Ofis'
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const sonuc = await next(e)
    await $.command.register({ name: 'ofis', description: 'Minimalist Animatör Ofis panelini açar' })
    // Panel yalnızca bir Minimalist Animatör stüdyosunda kendiliğinden açılır; diğer projelerde /ofis ile açılabilir.
    if (await studyoOku($, await kokBul($))) void $.ui.open({ id: PANE, title: await baslik($) })
    void yenile($)
    $.clock.every(YENILEME_MS, () => {
      void yenile($)
    })
    return sonuc
  })

  on('command.run', { command: 'ofis' }, async $ => {
    await $.ui.open({ id: PANE, title: await baslik($) })
    await yenile($)
    return { text: 'Ofis paneli açıldı.' }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const ogeler = $.ui.resolve(e)
    const { Box, Text, Button, Markdown } = ogeler
    const Input = 'Input' in ogeler ? ogeler.Input : null
    const v = await read($, veri)
    const g = await read($, gorunum)
    const git = (yeni: Gorunum) => update($, gorunum, () => yeni)

    if (!v) {
      return (
        <Box padding={1}>
          <Text dimColor>Ofis yükleniyor…</Text>
        </Box>
      )
    }

    if (!v.studyo) {
      return (
        <Box flexDirection="column" gap={1} padding={1}>
          <Text weight="bold">Bu klasör henüz bir stüdyo değil</Text>
          <Text dimColor size="footnote">
            Proje klasöründe ayarlar.json bulunamadı. Kurmak için sohbete /minimalist-animator:kurulum yaz.
          </Text>
        </Box>
      )
    }

    // --- Ajan sayfası ---
    if (g.sayfa === 'ajan') {
      const a = v.ajanlar.find(x => x.id === g.ajan)
      if (!a) {
        void git({ sayfa: 'ana' })
        return <Text dimColor>…</Text>
      }
      const sekme = (id: 'konus' | 'gecmis' | 'hafiza', etiket: string) => (
        <Button
          key={`sekme-${id}`}
          label={etiket}
          variant={g.sekme === id ? 'primary' : 'secondary'}
          onPress={() => git({ sayfa: 'ajan', ajan: a.id, sekme: id })}
        />
      )
      return (
        <Box flexDirection="column" gap={1} padding={1}>
          <Box flexDirection="row" gap={1}>
            <Button key="geri" label="← Ofis" plain onPress={() => git({ sayfa: 'ana' })} />
          </Box>
          <Box flexDirection="column">
            <Text size="heading" weight="bold">
              {a.ikon} {a.ad}
            </Text>
            <Text dimColor size="footnote">
              {a.rol}
            </Text>
            <Text color={a.calisiyor ? 'success' : 'subtle'} size="footnote">
              {a.calisiyor ? `● Çalışıyor${a.aciklama ? ` — ${a.aciklama}` : ''}` : '○ Boşta'}
            </Text>
          </Box>
          <Box flexDirection="row" gap={1}>
            {sekme('konus', 'Konuş')}
            {sekme('gecmis', 'Geçmiş')}
            {sekme('hafiza', 'Öğrendikleri')}
          </Box>

          {g.sekme === 'konus' && (
            <Box flexDirection="column" gap={1}>
              {a.sohbet.length === 0 && (
                <Text dimColor size="footnote">
                  {a.id === 'yonetici'
                    ? 'Bana buradan yazabilirsin; cevabım burada görünür.'
                    : `${a.ad}'e bir soru sor ya da not bırak. Mesajını ben (Yönetici) iletirim, cevabı burada görürsün.`}
                </Text>
              )}
              {a.sohbet.slice(-14).map((m, i) => (
                <Box key={`m-${i}-${m.zaman}`} flexDirection="column">
                  <Text size="caption" dimColor>
                    {kullaniciMi(m.kim) ? 'Sen' : m.kim === 'yonetici' ? '🧭 Yönetici' : `${a.ikon} ${a.ad}`} · {saat(m.zaman)}
                  </Text>
                  <Text color={kullaniciMi(m.kim) ? 'suggestion' : 'text'}>{m.metin}</Text>
                </Box>
              ))}
              {a.cevapBekliyor && (
                <Text color="warning" size="footnote">
                  ⏳ Yönetici iletiyor, cevap bekleniyor…
                </Text>
              )}
              {Input ? (
                <Input
                  key={`mesaj-${a.id}`}
                  placeholder={`${a.ad}'e yaz…`}
                  submitLabel="Gönder"
                  rows={2}
                  onSubmit={(deger: string) => void gonder($, a.id, deger)}
                />
              ) : (
                <Text dimColor size="footnote">
                  Bu ekranda mesaj yazılamıyor; masaüstü uygulamasından yaz.
                </Text>
              )}
            </Box>
          )}

          {g.sekme === 'gecmis' && (
            <Box flexDirection="column" gap={1}>
              {a.gecmis.length === 0 && <Text dimColor>Henüz kayıt yok.</Text>}
              {a.gecmis.map((k, i) => (
                <Box key={`k-${i}-${k.zaman}`} flexDirection="column">
                  <Text size="caption" dimColor>
                    {saat(k.zaman)} · {k.proje.replace(/^\d{4}-\d{2}-\d{2}_/, '')}
                  </Text>
                  <Text size="footnote">{k.metin}</Text>
                </Box>
              ))}
            </Box>
          )}

          {g.sekme === 'hafiza' && (
            <Box flexDirection="column" gap={1}>
              {a.hafiza.length === 0 && <Text dimColor>Henüz not yok.</Text>}
              {a.hafiza.map((n, i) => (
                <Box key={`h-${i}`} flexDirection="column">
                  <Text weight="semibold" size="footnote">
                    • {n.baslik}
                  </Text>
                  {n.ozet && (
                    <Text dimColor size="footnote">
                      {n.ozet}
                    </Text>
                  )}
                </Box>
              ))}
              <Text dimColor size="caption">
                Yanlış bir not görürsen Konuş sekmesinden düzelttir.
              </Text>
            </Box>
          )}
        </Box>
      )
    }

    // --- Video sayfası ---
    if (g.sayfa === 'video') {
      const p = v.projeler.find(x => x.id === g.proje)
      if (!p) {
        void git({ sayfa: 'ana' })
        return <Text dimColor>…</Text>
      }
      const paket = p.paket ? await metinOku($, p.paket) : null
      return (
        <Box flexDirection="column" gap={1} padding={1}>
          <Button key="geri" label="← Ofis" plain onPress={() => git({ sayfa: 'ana' })} />
          <Text size="heading" weight="bold">
            🎬 {p.baslik}
          </Text>
          <Text dimColor size="footnote">
            {ASAMA_AD[p.asama] ?? p.asama} · {MOD_AD[p.mod] ?? p.mod}
          </Text>
          {p.video && (
            <Button
              key="izle"
              label="Videoyu sohbette göster"
              variant="primary"
              onPress={() => istek($, `Kullanıcı ${p.id} videosunu görmek istiyor: cikti'deki MP4'ü SendUserFile ile gönder.`)}
            />
          )}
          {paket ? <Markdown text={kisalt(paket, 6000)} /> : <Text dimColor>Yayın paketi henüz yazılmadı.</Text>}
        </Box>
      )
    }

    // --- Ana sayfa ---
    const calisanlar = v.ajanlar.filter(a => a.calisiyor)
    const acik = v.projeler.filter(p => !['tamam', 'yayinlandi'].includes(p.asama))
    const hazir = v.projeler.filter(p => p.video)

    return (
      <Box flexDirection="column" gap={1} padding={1}>
        <Box flexDirection="column" borderStyle="round" borderColor={calisanlar.length ? 'success' : 'subtle'} paddingX={1}>
          {calisanlar.length === 0 ? (
            <Text dimColor>○ Şu an kimse çalışmıyor</Text>
          ) : (
            calisanlar.map(a => (
              <Text key={`c-${a.id}`} color="success">
                ● {a.ikon} {a.ad} çalışıyor{a.aciklama ? ` — ${kisalt(a.aciklama, 80)}` : ''}
              </Text>
            ))
          )}
        </Box>

        <Box flexDirection="column">
          <Text weight="bold">📥 Senden beklenen</Text>
          {v.bekleyen ? (
            <Box flexDirection="column">
              {v.bekleyen.satirlar.slice(0, 6).map((s, i) => (
                <Text key={`b-${i}`} size="footnote">
                  {s}
                </Text>
              ))}
              <Button
                key="sorulari-sor"
                label="Soruları şimdi sor"
                variant="primary"
                onPress={() =>
                  istek($, 'Kullanıcı bekleyen onay ve kararları görmek istiyor: sirket/kullanici/onay-bekleyenler.md\'deki bekleyen maddeleri AskUserQuestion ile sor.')}
              />
            </Box>
          ) : (
            <Text dimColor size="footnote">
              Şu an bir şey beklenmiyor ✓
            </Text>
          )}
        </Box>

        <Box flexDirection="column">
          <Text weight="bold">✍️ Kendi senaryon</Text>
          {Input ? (
            <Input
              key="senaryo"
              placeholder="Metnini yapıştır; ekip kelimelerine dokunmadan sahneler (önce sana nasıl ilerleyeceğini sorar)…"
              submitLabel="Senaryomu ver"
              rows={5}
              onSubmit={(deger: string) => void senaryoVer($, deger)}
            />
          ) : (
            <Text dimColor size="footnote">
              Metnini sohbete yaz ya da /minimalist-animator:senaryom kullan.
            </Text>
          )}
        </Box>

        <Box flexDirection="column">
          <Text weight="bold">🎬 Videolar</Text>
          {acik.length === 0 && (
            <Text dimColor size="footnote">
              Üretimde video yok.
            </Text>
          )}
          {acik.map(p => (
            <Box key={`p-${p.id}`} flexDirection="column">
              <Text size="footnote" weight="semibold">
                {p.baslik} <Text dimColor>· {MOD_AD[p.mod] ?? p.mod}</Text>
              </Text>
              <Text size="footnote" color={p.kullaniciBekleniyor ? 'warning' : 'claude'}>
                {cubuk(p.adim, p.toplam)} {ASAMA_AD[p.asama] ?? p.asama}
                {p.kullaniciBekleniyor ? ' · seni bekliyor' : ''}
              </Text>
            </Box>
          ))}
          {hazir.length > 0 && (
            <Box flexDirection="column" marginTop={1}>
              <Text size="footnote" weight="semibold">
                Hazır videolar
              </Text>
              {hazir.map(p => (
                <Button key={`v-${p.id}`} plain onPress={() => git({ sayfa: 'video', proje: p.id })}>
                  ▶ {p.baslik} <Text dimColor>{ASAMA_AD[p.asama] ?? p.asama}</Text>
                </Button>
              ))}
            </Box>
          )}
        </Box>

        <Box flexDirection="column">
          <Text weight="bold">👥 Ekip</Text>
          {v.ajanlar.map(a => (
            <Box key={`a-${a.id}`} flexDirection="column" marginTop={1}>
              <Button key={`ajan-${a.id}`} plain onPress={() => git({ sayfa: 'ajan', ajan: a.id, sekme: 'konus' })}>
                {a.ikon} {a.ad}{' '}
                <Text color={a.calisiyor ? 'success' : 'subtle'}>{a.calisiyor ? '● çalışıyor' : '○ boşta'}</Text>
                {a.cevapBekliyor ? <Text color="warning"> · ✉ cevap bekleniyor</Text> : ''}
              </Button>
              <Text dimColor size="footnote" wrap="truncate-end">
                {a.son ? `${saat(a.son.zaman)} · ${a.son.metin}` : 'Henüz kayıt yok'}
              </Text>
            </Box>
          ))}
        </Box>

        <Text dimColor size="caption">
          Son yenileme: {saat(simdiDamga(v.zaman))} · her {YENILEME_MS / 1000} sn
        </Text>
      </Box>
    )
  })
}
