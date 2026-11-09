# İş Akışı — Bir videonun yolculuğu

Her video ya da gönderi bir **proje**dir: `sirket/projeler/<YYYY-MM-DD>_<konu-slug>/`. Projenin nerede olduğunu `durum.json` söyler. Yönetici yalnızca bu dosyaya bakarak sıradaki adımı bilir; bu yüzden her aşama sonunda güncellenir (`ma proje asama <proje> <yeni-asama> "<not>"`). Proje açmak: `ma proje yeni <slug> "<Başlık>" [--format <format>] [--mod <mod>] [--metin <dosya>]`.

## Senaryo modları (`durum.json` → `senaryo_modu`)

Varsayılan `ayarlar.json` → `akis.varsayilan_senaryo_modu`. Kendi modlarında kullanıcının metni `sirket/kullanici/metinler/<tarih>_<slug>.md`'de durur (projeler klasörünün dışında; kilit o klasördeki değişiklikleri "çalışıyor" sayar), `--metin` ile projeye `kullanici-metni.md` olarak kopyalanır. Gönderide metin dosyası `## Kare N` bölümlerinden oluşur.

| Mod | Araştırma (1) | Senaryo (2) | Kontrol (3) | Kullanıcı onayı (3b) |
|---|---|---|---|---|
| `ajan` | Araştırmacı Görev 1 → `arastirma.md` | Senarist yazar | Araştırmacı doğruluk kontrolü (Görev 3) + Yönetici KK | Okunuş |
| `kendi-arastir` | Araştırmacı Görev 2: dar araştırma → `arastirma.md` + `oneriler.md` (metne dokunmaz) | Senarist kullanıcı metnini korur, satırlara böler ve sahneler | Yönetici önerileri kullanıcıya sorar (multiSelect); kabul edilenleri Senarist uygular | Okunuş (uygulanan öneriler işaretli) |
| `kendi-duzenle` | yok | Senarist yalnızca anlaşılırlık/akıcılık için cümleleri düzenler, bilgi eklemez/çıkarmaz, değişiklikleri listeler | Yönetici KK: anlam ve bilgi aynı mı | Okunuş + değişiklik listesi |
| `kendi-aynen` | yok | Senarist kelimeye dokunmaz; yalnızca satırlara böler ve sahneler | `ma kontrol <proje> --senaryo` (sözcük farkı = HATA; gönderide `--post`) | Seslendirme dönüşümleri listesi, tek onay |

Bütün kendi modlarında: `altyazi` = kullanıcının sözcükleri; `metin` = yalnızca sayı/sembol/kısaltmaların seslendirme için yazıya çevrilmiş hâli (`etiketli` = `metin`). Bu dönüşümler kullanıcıya tek onayla gösterilir. Araştırma olmayan modlarda (`kendi-duzenle`, `kendi-aynen`) bilgilerin doğruluğu kullanıcının sorumluluğundadır; Yönetici bunu mod seçilirken bir kez söyler, `kaynak` alanı `"kullanici"` olur. `kendi-arastir`'da kullanıcı bir ❌ düzeltmesini reddederse metin onun dediği gibi kalır; Yönetici bunu `gunluk.md`'ye ve yayın paketinin kaynak notuna işler.

Öneri sorusu ile Okunuş onayı: kullanıcı sohbetteyse sırayla sorulur (öneriler → uygulama → Okunuş). Günlük döngüde aynı soru turunda iki soru olarak sorulur: öneriler (multiSelect) + "Seçtiğin önerilerle Okunuş'u onaylıyor musun?"; Senarist yalnızca seçilenleri uygular, başka değişiklik yapmaz.

## Aşamalar

| # | Aşama (`asama`) | Sorumlu | Girdi | Çıktı | Kapı (geçmeden ilerlenmez) |
|---|---|---|---|---|---|
| 0 | `brief` | Yönetici | fikir havuzu, analiz, islenen-konular, (kendi modlarında) kullanıcı metni | `brief.md` | Konu daha önce işlenmemiş ya da yeni bir açı var |
| 1 | `arastirma` | Araştırmacı | `brief.md` (+ `kullanici-metni.md`) | `arastirma.md` (+ `oneriler.md`) | Her bilgi kaynaklı, önemli iddialar en az 2 bağımsız kaynaklı; tartışmalılar işaretli. `kendi-duzenle`/`kendi-aynen`'de atlanır |
| 2 | `senaryo` | Senarist | brief + arastirma/kullanıcı metni + büyüme bilimi + arşiv | `senaryo.md` + `senaryo.json` (gönderide `post.md` + `post.json`) | Hook ilk 2 sn'de, süre hedefte, her bilgi cümlesi kaynaklı (ajan modu); mod kuralına uygun |
| 3 | `senaryo-kontrol` | Yönetici (+ Araştırmacı doğruluk kontrolü, `ajan` modunda) | senaryo | onay ya da revizyon | `kalite-kontrol.md` → Senaryo listesi |
| 3b | `senaryo-kontrol` + `ma proje bekle` | Yönetici → **kullanıcı** | `senaryo.md` → "Okunuş" paragrafı (moda göre ek liste) | Kullanıcının senaryo onayı (`ma proje devam`) ya da düzeltme notu → Senarist | Senaryoyu kullanıcı onaylamadan görsel ve ses üretimi başlamaz. Sohbette Okunuş + AskUserQuestion ("Onayla" / "Değişiklik var"); en fazla 1 düzeltme turu, sonra yeniden sorulur |
| 4 | `gorsel-hazirlik` | Çizer | `senaryo.json` → `varliklar` | Üretilmiş, incelenmiş görseller + `cizim/cizim-raporu.md` (indirilecekler listesi) | Arşivde olan yeniden çizilmedi; stil tutarlı |
| 5 | `ses-hazirlik` | Seslendirmen | `senaryo.json` → `satirlar` | Üretilmiş sesler + `ses/ses-raporu.md` (indirilecekler listesi) | Ses kimliği arşivdekiyle aynı; telaffuz kontrolü |
| 6 | `indirme-onayi` | Yönetici → **kullanıcı** | iki rapordaki listeler | Kullanıcının onayı | Günün bütün projelerinin listesi tek turda: dosya adı, kaynak site, yaklaşık boyut |
| 7 | `indirme-isleme` | Yönetici indirir; Çizer + Seslendirmen tarayıcısız işler (paralel) | onay | `cizim/hazir/*.png` (dekupe), `ses/parcalar/*.wav`, `ses/zamanlama.json`, arşiv kayıtları | Dosyalar proje klasöründe, envantere işlendi |
| 8 | `animasyon` | Animatör | senaryo.json + cizim/hazir + ses/ | `animasyon/` kodu, kontrol kareleri, `cikti/<proje>.mp4` | `ma kontrol <proje>` temiz; kareler incelendi |
| 9 | `son-kontrol` | Yönetici | video | `cikti/yayin-paketi.md` (+ kapak) | `kalite-kontrol.md` → Final listesi |
| 10 | `kullanici-onayi` | **kullanıcı** | video + paket | onay ya da geri bildirim | — |
| 11 | `revizyon` | ilgili ajan | kullanıcının notu | düzeltilmiş çıktı | → tekrar 9 |
| 12 | `tamam` | — | — | Kullanıcı yayınlamaya hazır | — |
| 13 | `yayinlandi` | Analist (48 sa. sonra) | yayın linki | `bilgi-bankasi/analiz/` performans notu | — |

Araç seçimi aşama 4–5'i değiştirir (`ayarlar.json` → `araclar`): `gorsel_araci: elle` / `ses_araci: elle` → kullanıcı dosyaları kendisi bırakır, indirme aşaması yoktur (`${CLAUDE_PLUGIN_ROOT}/protokoller/araclar/elle.md`); `ses_araci: taslak` → `ma taslak-ses <proje>` çevrimdışı mırıltı sesi üretir, yalnızca önizleme içindir (`araclar/taslak.md`).

Aşama 4 ve 5 tarayıcı kullandığında **sırayla** çalışır (önce Çizer, sonra Seslendirmen). Biri engellenirse (giriş istendi, kredi bitti) diğeri yine de çalışır; engel kullanıcıya tek turda bildirilir.

Gönderilerde (`post-carousel`, `post-karikatur`) ses aşaması yoktur: `gorsel-hazirlik` → `indirme-onayi` → kareler (`ma post-olustur <proje>`) → son kontrol. Dört senaryo modu gönderilerde de aynen geçerlidir.

Ajanlar bir aşamada eksik/hatalı girdi bulursa durmaz: yapabildiğini yapar, eksik için **talep** açar (`iletisim.md`). Ör. Animatör "Ay görselinin arkası beyaz değil, dekupe edilemiyor" → Çizer'e talep.

## durum.json

```json
{
  "id": "2025-05-12_ay-yuzu",
  "baslik": "Ay neden hep aynı yüzünü gösterir?",
  "format": "monolog",
  "senaryo_modu": "ajan",
  "asama": "senaryo",
  "olusturma": "2025-05-12T09:05",
  "kullanici_bekleniyor": false,
  "bekleyen_onay": null,
  "font": null,
  "revizyon": {"senaryo": 0, "gorsel": 0, "ses": 0, "animasyon": 0},
  "gecmis": [{"zaman": "2025-05-12T09:05", "asama": "brief", "not": "Fikir havuzundan seçildi"}]
}
```

`kullanici_bekleniyor: true` iken o proje kullanıcıdan yanıt gelmeden ilerletilmez; Yönetici diğer projelere geçer. `font` (isteğe bağlı): bu videoya özel yazı tipi — `"<dosya>.ttf"` ya da `{"kalin_dar": "<dosya>", "kalin_yari_dar": "<dosya>"}`, dosyalar `sirket/arsiv/fontlar/`'da (`uslup.md` → Yazı tipi).

## Günlük döngü

`minimalist-animator:gunluk-dongu` skill'i uygular. Özet:
1. Kullanıcının gelen kutusunu (`sirket/kullanici/`) ve açık projeleri oku. Kullanıcı yanıt verdiyse ilgili projeyi ilerlet.
2. Son geniş taramadan (en yeni `*_haftalik.md`) 7 gün geçtiyse Analist geniş tarama yapar (kendi hesaplar + rakipler); diğer günler sadece nokta atışı işler. Büyüme bilimi ayda bir.
3. Açık projeleri en ileri noktaya kadar götür (en eski proje önce).
4. Haftalık plana (`akis.haftalik_plan`) göre gerekiyorsa yeni proje aç. Aynı anda en fazla 3 açık proje.
5. Kullanıcıya gereken her şeyi **günde tek turda** topla: bütün indirmeler, kararlar (önerinle), hazır videolar — en fazla `akis.gunluk_soru_siniri` tıklanabilir soru (AskUserQuestion); önerin ilk seçenek. Bildirim gönder. Sonradan çıkan her şey yarının sorularına girer.
6. Günün özetini `sirket/kullanici/gunluk-ozet.md`'nin başına ekle.

## Yayın sonrası

Kullanıcı "yayınladım" + link verdiğinde proje `yayinlandi` olur, konu `islenen-konular.json`'a işlenir. Analist 48 saat sonra (bir sonraki günlük döngüde) izlenme, izlenme süresi, kaydetme/paylaşım verilerini okur ve "ne işe yaradı / yaramadı" notunu `bilgi-bankasi/analiz/` altına yazar. Bu notlar Senarist ve Yönetici'nin sonraki kararlarını besler.
