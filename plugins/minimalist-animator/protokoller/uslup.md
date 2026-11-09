# Marka ve Üslup Rehberi

Marka bilgileri `ayarlar.json`'dadır: `marka.ad`, `marka.slogan`, `marka.alt_slogan`, `marka.logo`, `marka.hesaplar`; içerik `icerik.dil`, `icerik.konu_alani`, `icerik.ton`, `icerik.hedef_kitle`, `icerik.platformlar`; kısa ekran metinleri `metinler.*`; renk ve yazı tipi `gorsel.*`. Bu rehber varsayılandır; kullanıcı proje kökündeki `CLAUDE.md`'ye kendi üslup notlarını yazabilir — o notlar önce gelir.

## Kim gibi konuşuruz?

Varsayılan ton (`icerik.ton`): **tatlı, samimi, meraklı, ukala değil.** Anlatıcı ya da konunun kahramanı izleyiciyle sanki yıllardır tanışıyormuş gibi konuşur; bilgi verir ama ders anlatmaz, hikâye anlatır.

- İzleyiciye doğrudan hitap: "Biliyor muydun?", "Ne dersin?", "Gidip bakalım mı?"
- Kısa ve orta cümleler karışık; okunuşu zor kelime yok; sayılar seslendirmede `icerik.dil`'de **yazıyla** ("bin iki yüz altı").
- Mizah: hafif, sevimli, konuya ve kişilere saygılı. Alay, argo, küçümseme yok.
- Duygu yayı: merak → şaşkınlık → hayranlık → ilham. Son cümle izleyiciye döner.
- Abartı yok: "ilk" / "en" iddiaları ancak kaynak öyle diyorsa. Tartışmalıysa "bazı kaynaklara göre" diye işaretlenir ya da çıkarılır.
- Hedef kitle `icerik.hedef_kitle` (boşsa: genç yetişkinler; aileler ve öğrenciler de izleyebilmeli).

## Formatlar

1. **Monolog (`monolog`)**: Anlatıcı ya da konunun kahramanı tek başına anlatır; 30–35 sn, tek ses. Çalışan örnek: `ma demo` → `sirket/projeler/0000-00-00_demo/`.
2. **Röportaj — Zaman Yolcusu (`zaman-yolcusu`)**: Tekrar eden gezgin sunucu karakter konunun kahramanını (bir kişi, bir uzman ya da konuşan bir nesne) ziyaret eder, mikrofon uzatır. İki ses. Sunucu karakteri ve sesi arşivde tutulur (tekrar eden karakter).
3. **"Biliyor muydun?" (`biliyor-muydun`)**: 12–18 sn tek bilgi.

Aday formatlar (Yönetici dener, Analist ölçer): **"O zaman / şimdi"** karşılaştırması, **seri bölümleri** (5 bölümlük tematik hafta; yeni seri formatı kritik karardır).

## Video teknik standardı

| Özellik | Değer |
|---|---|
| Çözünürlük | 1080×1920 (9:16), 30 fps |
| Süre | 25–45 sn (ideal 30–35); "Biliyor muydun?" 12–18 sn |
| Kodek | H.264 High, yuv420p, CRF ≤ 18; AAC 192 kbps 44.1 kHz |
| Ses seviyesi | ~ -14 LUFS entegre, tepe ≤ -1.5 dBTP (motor otomatik uygular) |
| Hook | İlk 1.5 sn içinde hareket + soru/şaşırtıcı bilgi; ilk karede karakter görünür |
| Kapanış | Son ~2.5 sn: logo (`marka.logo`, yoksa marka adı) + `marka.slogan` + `marka.alt_slogan` + karakter küçük |

## Görsel kimlik

- **Çizim üslubu** (`gorsel.cizim_uslubu`; yoksa varsayılan): chibi / kawaii; büyük kafa, küçük gövde; kalın koyu kahverengi dış hat; düz renkler, yumuşak hücre gölgesi; pembe yanaklar; önden tam boy; saf beyaz zemin (dekupe için).
- **Stil referansı:** `sirket/arsiv/stil-referansi/` (kullanıcının koyduğu ya da onayladığı ilk ana karakter ve ilk arka plan). Belirlenmesi kritik karardır.
- **Nesneler:** aynı çizgi stili, tek nesne, beyaz zemin, gölge yok.
- **Arka planlar:** aynı çizgi stili, 9:16 dikey, ortası boş (karakter yeri), sıcak ışık.
- **Varsayılan zemin:** krem parşömen + soluk desen (motor üretir).
- **Renkler:** `gorsel.renkler` (DARK, INK, GOLD, GOLD_D, CREAM, NAVY, RED, KAHVE); motor bunları kullanır.
- **Altyazı:** 2–4 kelimelik parçalar, ekranın alt-ortasında (y≈1545), vurgu kelimeleri vurgu renginde (GOLD). Sessiz izlenebilirlik şart. Büyük harf dönüşümü `icerik.dil`'e göre (Türkçede İ/I doğru).
- **Güvenli alan:** üst 200 px ve alt 330 px'te önemli bilgi yok (platform arayüzü); sağ kenar (x>960, y 1000–1700) beğeni/yorum butonlarının altında kalır.
- **Etiketler:** eser/nesne adı üstte vurgu çizgili başlık; isim plakası lacivert-altın pano; yıl sayacı büyük rakam; konum pini kırmızı.

## Yazı tipi

- Varsayılan: eklentideki **Barlow Condensed Bold** ve **Barlow Semi Condensed Bold** (SIL Open Font License; `gorsel.font`). Koyu kontur + yumuşak gölge.
- **Video başına font:** kullanıcı bir video ya da gönderi için farklı bir yazı tipi isterse yalnızca o proje o fontla yapılır; diğer projeler ve varsayılan değişmez. Font dosyası `sirket/arsiv/fontlar/`'a konur ve projenin `durum.json`'una (ya da `senaryo.json`/`post.json` üst düzeyine) yazılır: tek dosya için `"font": "<dosya>.ttf"` (iki tür için de kullanılır), ayrı dosyalar için `"font": {"kalin_dar": "<dosya>", "kalin_yari_dar": "<dosya>"}`. Yol proje köküne ya da `sirket/arsiv/fontlar/`'a göre çözülür; bulunamazsa motor uyarır ve varsayılan fonta döner.
- Font dosyasını indirmek gerekiyorsa kullanıcıya dosya adı, kaynak ve boyutla sorulur (indirme onayı); lisansı (ticari kullanım) kullanıcıya hatırlatılır. Varsayılan fontu kalıcı değiştirmek kritik karardır.

## Ses kimliği

Ses kimlikleri `sirket/arsiv/ses-kimlikleri.json`'da. Bir karakter bir kez seslendirildiyse **her videoda aynı ses + aynı ayarlar** kullanılır. **Duygu etiketi kullanılmaz:** karakter baştan sona aynı kişi gibi, tek sabit ve akıcı üslupla konuşur; vurgu noktalama ve cümle kuruluşuyla verilir. Bütün videoda en fazla 1 etiket istisna ([laughs] gibi, gerçekten gerekiyorsa); [softly], [whispers], [playfully], [cheerfully] yok. Gerçek bir kişiyi birinci ağızdan konuşturmak ve gerçek kişinin sesini taklit etmek kritik karardır.

## Gönderi (post) formatları
Instagram akışı için **4:5 (1080x1350)**. Sıklık `akis.haftalik_plan.gonderi`. Amaç: kaydedilen ve paylaşılan, kısa ama ilgi çekici içerik. İki tür (dönüşümlü denenebilir):
- **Bilgi kaydırmalı (`post-carousel`, 5–7 kare):** 1. kare kanca: tek merak cümlesi + karakter + büyük yazı. 2.–(n-1). kareler: her biri **tek bilgi**, ≤ 20 kelime, bir görsel. Son kare: soru + `metinler.cta_kapanis` + logo/slogan. Uygun konular: "5 bilgi", "bunu ilk kim yaptı?", sıralama, efsane mi gerçek mi.
- **Karikatür (`post-karikatur`, 1–4 panel):** Karakterlerle konunun komik bir anı. Espri gerçek bir bilgiye dayanır; son panelde ya da açıklamada 1–2 cümle "gerçekte ne oldu". Kimse küçük düşürülmez; **dinî şahsiyetler ve hassas konular karikatür yapılmaz**.
- **Türeme gönderi (`post-carousel`, proje adı `<video-slug>-gonderi`):** Bir videonun `arastirma.md`'si ve arşiv görselleriyle hazırlanan kaydırmalı. Videoyu tekrar etmez; videoda olmayan ya da daha ayrıntılı bilgiler. Son karede videoya yönlendirme olabilir. Yeni çizim yok (zorunluysa en fazla 1).
- **Ortak kurallar:** Her bilgi kaynaklı (videolardaki gibi; kendi modlarında kullanıcı metni). Kare başına az metin, büyük ve okunur yazı. Renk, yazı tipi ve doku videolarla aynı. Yayın paketi: açıklama (ilk satır kanca, sonda soru), 5–8 hashtag, önerilen saat (hafta sonu öğle başlangıç hipotezi; Analist doğrular). Kapak = 1. kare.

## Yayın paketi (`cikti/yayin-paketi.md`)

Yalnızca `icerik.platformlar`'daki platformlar için, `icerik.dil`'de:
- **Instagram açıklaması:** 1. satır hook (125 karakterden kısa), 2–3 satır bilgi, soru ile biten etkileşim cümlesi, marka satırı. 5–8 hashtag (karışık: geniş + niş + marka etiketi).
- **YouTube Shorts başlığı:** ≤ 60 karakter, merak boşluğu bırakan; açıklama 2 satır + 3 hashtag.
- **TikTok:** kısa açıklama + 3–5 hashtag.
- **Önerilen paylaşım saati:** `sirket/bilgi-bankasi/buyume-bilimi.md` + Analist'in hesap verisine göre, gerekçesiyle.
- **Kapak karesi:** videodan seçilmiş, yüz + büyük başlık okunur kare (`cikti/kapak.png`).
- **Kaynaklar:** açıklamanın sonunda ya da sabitlenmiş yoruma eklenecek 1–2 kaynak. Kullanıcı videoda kaynak ifadesi istemediyse (tek kaynaklı anlatı) bu not **zorunludur**.
- Taslak sesle üretildiyse en üstte: "ÖNİZLEME — taslak ses, yayınlanmaz".
