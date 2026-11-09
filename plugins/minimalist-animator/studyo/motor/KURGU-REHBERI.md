# Kurgu Motoru Rehberi (eklenti: `studyo/motor/kurgu.py`)

Senaryo + ses parçaları + dekupe görsellerden 1080×1920, 30 fps Reels videosu üretir. Kod eklentide (`studyo/motor/`), veri proje kökünde (`sirket/projeler/<proje>/`). Çalışan tam örnek: `ma demo` → `sirket/projeler/0000-00-00_demo/` (senaryo.json → taslak ses → render.py → cikti/*.mp4; kaynağı eklentide `ornek/demo/`).

Komutlar: `ma render <proje> [--bilgi | --kareler otomatik | --kapak 3.2 | --ses]` (render.py yoksa şablonu kopyalar), `ma taslak-ses <proje>` (gerçek ses gelmeden mırıltı sesiyle zamanlama), `ma motor-testi`.

## Akış

```python
v = Video(PROJE)          # senaryo.json + ses/zamanlama.json okunur
v.ses_hatti()             # ses parçaları satır sırasıyla yerleşir (satır arası: senaryodaki sonra_bosluk, yoksa 0.28 sn)
v.otomatik_kurgu()        # her satırın "ekranda" olayları uygulanır; müzik + kapanış otomatik
# ... ince ayar ...
v.calistir()              # --bilgi | --kareler otomatik | --kareler 1.2,3.4 | --kapak 3.2 | --ses | (boş = tam video)
```

Zamanları **sabit saniye yazmak yerine satırlara bağla**: `v.satir(4).bas`, `.bit`, `.orta`, `.kelime("makineler")` (kelimenin altyazıdaki yaklaşık başlangıcı), `.kelime("x", son=True)`. Ses değişirse kurgu kendiliğinden kayar.

## Ekran düzeni
- Karakter ayak hizası `y=1400` (ZEMIN_Y). Tek karakter boyu 900 px, iki karakterde 760 px.
- Yerler: `sol`=270, `orta`=540, `sag`=810. Nesne üst yerleri: `sol-ust`, `sag-ust`, `orta-ust` (y≈800).
- Üst bant (y 200–420): etiket / isim plakası / yıl / konum — **aynı anda ikisini koyma**.
- Altyazı merkezi `y=1545`. Alt 330 px ve sağ kenar (x>960) platform arayüzünün altında kalır.

## Figürler
```python
k = v.karakter("kasif", boy=900)            # cizim/hazir/<id>_acik.png (+ _kapali, _konusma varsa)
n = v.nesne("ay", boy=620)                  # cizim/hazir/<id>.png
```
Hareketler (hepsi zincirlenebilir, zaman sırası serbest):
| Metot | Açıklama |
|---|---|
| `gir(t, nasil, x, y=None, boy=None)` | `pop`, `sol-zipla`, `sag-zipla`, `kenardan-bak`, `alttan`, `soldan`, `sagdan`, `yukaridan` |
| `git(t, x=, y=, boy=, sure=0.5, zipla=True)` | yeni yere (zıplayarak) gider; `boy` ile büyür/küçülür |
| `cik(t, nasil="sag")` | `sag`, `sol`, `alt`, `pop` |
| `zipla(t, yukseklik=50)` · `sallan(t0, t1, aci=6)` · `buyut(t0, t1, k=1.07)` · `don(t)` | ek hareketler |
| `yerlestir(t, x, y, boy)` | animasyonsuz konum |
| `goz_kirp(t, sure=0.45)` (karakter) | `_kapali` varyantı varsa |
Otomatik: nefes alma, konuşurken sesin zarfına göre zıplama/esneme, rastgele göz kırpma (`_kapali` varsa), konuşurken ağız (`_konusma` varsa), yere inişte esneme, zemin gölgesi, nesnelerde hafif süzülme.

## Yazılar ve ikonlar
| Metot | Görünüm |
|---|---|
| `etiket(metin, t0, t1)` | üstte altın çizgili başlık (icat/eser adı) |
| `isim_plakasi(metin, t0, t1, alt="Kaşif · Gökbilimci")` | lacivert-altın pano soldan kayar |
| `yil(2026, 1609, t0, t1, alt=None)` | büyük altın yıl sayacı (geri sayar, tik sesi) |
| `konum("Gözlemevi · İstanbul", t0, t1)` | düşen kırmızı pin + yer adı |
| `soru_isareti(t0, t1, x, y)` · `unlem(...)` · `isaret("?", ...)` | zıplayan büyük işaret |
| `carpi(t0, t1, x, y)` | kırmızı X ("yok/yasak") + bzzt sesi |
| `buyuk_metin(metin, t0, t1, y=330)` | büyük vurgu yazısı |
| `dusunce_balonu(t0, t1, x, y, icerik="robot", kuyruk=(hx, hy))` | içinde varlık görseli ya da metin |
| `parilti(t, x, y)` · `pirilti_alani(t0, t1, x, y, rx, ry)` | parıltı patlaması / sürekli yıldızcıklar |

## Arka plan
`v.arka_plan("parsomen")` varsayılan. Görsel: `v.arka_plan("gece-gokyuzu", t, gecis="iris")` (cizim/hazir/<id>.png; yavaş zoom ve kenar kırpma otomatik). Geçişler: `kesme`, `iris`, `kayma`, `flas`.

## Ses
- `v.efekt(ad, t, seviye=0.5, **kw)` — `pop, boing, thump, whoosh, tick, bell(f0=880), trumpet, water(d=1.0), drip, gears(d), rewind(d), beeps, sparkle, chirp, zupp, power_up, hum(d), zap, clank, buzzer, slide_whistle, cricket, tweets, fanfare, pad_chord, arpeggio`. Bileşenler kendi efektlerini zaten ekler.
- `v.muzik("merak" | "neseli" | "gizem" | "yok", seviye=0.13)` — konuşma sırasında otomatik kısılır.
- Miks sonunda ffmpeg `loudnorm` ile ≈ -14 LUFS.

## Altyazı
Otomatik: her satırın `altyazi` metni 1–4 kelimelik parçalara bölünür, hece oranıyla zamanlanır, `vurgu` kelimeleri altın renkte. Elle bölmek için: `v.satir(2).parcalar = ["Çünkü Ay,", "Dünya'nın çevresinde", ...]`. Büyük harf ve hece sayımı dile göre (`ayarlar.json` → `icerik.dil`; tr/az'de i→İ). Kapatmak: `v.altyazi_acik = False`.

## Kapanış
`otomatik_kurgu` son konuşmadan 0.35 sn sonra iris geçişli marka kartını ekler: logo (`marka.logo`; boşsa `marka.ad` yazıyla), `marka.slogan`, `marka.alt_slogan` (boşsa o satır çizilmez), karakter. Elle: `v.kapanis(t=None, karakter=k)`. Süre: kapanış + 2.9 sn.

## Renkler ve yazı tipi
Renk sabitleri (`DARK, INK, GOLD, GOLD_D, CREAM, NAVY, RED, KAHVE`) `ayarlar.json` → `gorsel.renkler` ile ezilebilir (`[r, g, b]` ya da `"#rrggbb"`). Yazı tipi önceliği: proje `durum.json` / `senaryo.json` (gönderide `post.json`) üst düzey `"font"` alanı → `ayarlar.json` `gorsel.font.degisken_yol` (+ varyasyon adı) → `gorsel.font.kalin_dar / kalin_yari_dar` (eklentinin `assets/fonts/` Barlow fontları) → Pillow yedeği. Video başına font: `"font": "sirket/arsiv/fontlar/X.ttf"` (iki tür için de) ya da `{"kalin_dar": "...", "kalin_yari_dar": "..."}`; yol proje köküne, `sirket/arsiv/fontlar/`'a ya da proje klasörüne göre çözülür. `ma doktor <proje>` seçilen fontu gösterir.

## Projeye özel çizim
```python
# animasyon/ozel.py
from motor import Vec, GOLD, DARK, prog
def su_damlalari(fr, t):
    v = Vec.around(800, 900, 60); v.circle((800, 900 + 40 * prog(t, 15, 16)), 12, (84, 170, 230)); v.to(fr)
# render.py
from ozel import su_damlalari; v.ozel(su_damlalari, z=15, t0=v.satir(6).bas, t1=v.satir(6).bit)
```
`motor.py` çizim araçları: `Vec` (poly, circle, ellipse, line, polyline → `to(fr)`), `blit`, `text_spr`, `draw_gear`, `star_pts`, `sparkles`, `twinkles`, `shadow_ellipse`, kolaylaştırma eğrileri `prog, lerp, e_in, e_out, e_io, back, bump, spring`. Projeye özel efektler `animasyon/ozel.py` içinde tutulur; motorun genel araçlarıyla (yukarıdaki) yazılır.

## Performans
Demo (~15 sn) render: bir-iki dakika. Kontrol kareleri saniyeler. Önce `ma render <proje> --kareler otomatik`, sonra tam render.

## Motoru değiştirdiysen
`ma motor-testi` → demo projenin kareleri hâlâ üretiliyor mu? Bu rehberi güncelle.
