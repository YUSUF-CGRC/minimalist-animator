# Gemini (görsel aracı) — Arayüz, Prompt Kütüphanesi, İndirme

`ayarlar.json` → `araclar.gorsel_araci: "gemini"` iken Çizer bu dosyayı okur. Tarayıcı kuralları: `tarayici.md`. Bu dosya eklentiyle gelir ve güncellemede değişir; **projeye özgü öğrenimler** (işe yarayan/yaramayan prompt, arayüz değişikliği) `sirket/arsiv/arac-notlari.md` → "Gemini" bölümüne ve Çizer'in hafızasına yazılır: tarih — proje — varlık — not. Yaramayanlar "❌" ile işaretlenir.

## Arayüz
- Adres: `https://gemini.google.com/app` (izinli alan: `sirket/izinli-alanlar.json` → `cizer`). Girişi kullanıcı yapar; giriş ekranı çıkarsa dur.
- Arayüz değişebilir; düğmeleri `find` / `read_page` ile adından bul ("Yeni sohbet", "Görüntü oluştur" / "Create image", "+" / "Dosya yükleyin", araç seçici, model seçici). Görsel üretebilen modeli/aracı seç.
- **Her proje için yeni sohbet** aç; ilk mesaja stil referansını yükle (`sirket/arsiv/stil-referansi/`) ve "bu görselin çizim stilini birebir kullan" de. Referans yoksa yalnızca üslup tarifini (`gorsel.cizim_uslubu` ya da aşağıdaki varsayılan) yaz.
- **Dosya yükleme:** "+" → "Dosya yükleyin" yerel dosya penceresi açar (ajan kullanamaz). Çözüm: önce sayfada `HTMLInputElement.prototype.click`'i yakala (type=file ise DOM'a ekle, aria-label ver, açma), sonra menüden "Dosya yükleyin"e tıkla, `find` ile girişi bul, `file_upload` ile doldur; iş bitince orijinal `click`'i geri yükle. Mesajda ek varken menüde araçlar görünmeyebilir: önce "Görüntü oluştur"u seç, sonra dosya ekle. Sayfa yenilendikten sonra "+" menüsü geç açılabilir; `find` birkaç sn sonra ref verir.
- Prompt kutusuna koordinatla değil `find` ref'iyle tıkla (yazı kaybolabiliyor).
- ❌ **Görsele tıklamak** düzenleyiciyi/lightbox'ı açar. Görseli incelemek için: blob src'yi JS ile tam ekran bir overlay'e kopyala, ekran görüntüsü al, overlay'i kaldır. Piksel karşılaştırma da aynı yolla (canvas).

## Varsayılan çizim üslubu (İngilizce prompt parçası)
`gorsel.cizim_uslubu` boşsa: *"Cute chibi-style cartoon, big head and small body (about 2.5 heads tall), thick dark brown outlines, flat colors with soft cel shading, rosy cheeks, clean sticker-like look."* Kullanıcı başka bir üslup yazdıysa aşağıdaki şablonlarda bu satırın yerine o kullanılır.

## Şablon 1 — Karakter (ana görsel, gözler açık)

```
Use the drawing style of the attached image exactly (same line weight, color saturation, shading and proportions).

{ÜSLUP}
Character: {KARAKTER: ör. "a young explorer with a wide-brim safari hat and a red scarf"}.
Full body, front view, standing straight, arms relaxed at the sides, friendly closed-mouth smile, big dark eyes.
Accurate appearance: {GÖRÜNÜŞ: araştırmadaki görsel doğruluk notlarından — kıyafet, dönem, meslek aletleri}.
Pure flat white background (#FFFFFF), no ground shadow, no text, no watermark, no frame, no props, no base or pedestal, no name label.
Centered, the whole figure visible with generous white margin on all sides. Square 1:1.
```

## Şablon 2 — Göz kapalı varyant (aynı sohbette, onaylanan görselden hemen sonra)

İngilizce yaz (Türkçe düzenleme isteği metinle reddedilebiliyor):
```
Edit the previous image you generated: generate the exact same image, same pose, same framing, same colors, same size, but with the eyes closed in a blink (each closed eye is a thick dark brown curved line). Keep everything else identical.
```
Konuşma varyantı: "...but with the mouth slightly open (talking). Keep everything else identical."

## Şablon 3 — Nesne / eser / bilimsel öğe

```
Use the drawing style of the attached image exactly.
Cute cartoon illustration of {NESNE: ör. "a brass refracting telescope on a wooden tripod, side view"}.
{DOĞRULUK: önemli ayırt edici özellikler, sayılar BÜYÜK HARFLE}
{ÜSLUP}, slightly chunky toy-like proportions.
Single object only, pure flat white background (#FFFFFF), no ground shadow, no people, no text, no watermark.
Centered, whole object visible with generous margin. Square 1:1.
```

## Şablon 4 — Arka plan (dikey)

```
Use the drawing style of the attached image exactly.
Vertical 9:16 cartoon background scene of {MEKÂN: ör. "a small observatory rooftop at night under a starry sky"}.
Same art style: thick dark brown outlines, flat warm colors, soft lighting.
Leave an empty open floor area in the lower-middle part of the image for characters to stand. No people, no animals, no text, no watermark.
```

Gönderi panelleri ve sahneleri: "Vertical 4:5"; metin ve konuşma balonu çizdirilmez (yazıyı Animatör ekler).

## Bilinen taktikler
- Tek seferde tek ve somut düzeltme iste; "Change nothing else." ekle.
- Stil kayarsa referans görseli yeniden yükle ve "return to the attached style" de.
- Aynı hata 2 kez tekrarlanırsa ya da sohbet çok uzarsa yeni sohbet aç, referansı yeniden yükle, öğrendiklerinle iyileştirilmiş tek bir prompt ver.
- **Sayılabilir yapısal ayrıntılar** (kule, pencere, bacak, kanat sayısı): 3/4 izometrik açıda sayı tutmuyor. ✅ Önden simetrik görünüş + soldan sağa sıra ("Left to right: short, very tall, center, very tall, short") + boy farkını somut anlat + sayıyı BÜYÜK HARFLE yaz ("EXACTLY THREE rings"). Tutmazsa tek düzeltme: "Only change the X: give EACH X EXACTLY THREE ... Change nothing else."
- ❌ Aynı sohbette "önceki çizimle aynı stil" demek yapıyı da kopyalatıyor. Farklı yapılar için ya yeni sohbet aç ya da yalnızca "attached style reference" de.
- ❌ **Yazı dokusu** ("unreadable handwriting texture") okunur sahte metin üretiyor. ✅ "ABSOLUTELY NO WORDS / LETTERS / LOREM IPSUM; leave areas plain flat color with simple doodles; squiggles only" de. Haritalarda tarif edilmeyen kara parçaları eklenebiliyor; çıktıyı araştırma notlarıyla karşılaştır.
- İstenmeyen aksesuarı açıkça yasakla ("NO hat / NO sword ..."): tarifle birlikte ilk denemede tutuyor.
- Ayrı nesneleri aynı sohbette "NEW, completely separate image" ile iste.
- Gemini bazen görselin köşesine küçük bir filigran (yıldız) koyar: dekupe kopuk küçük parçaları otomatik siler; arka planlarda `ma dekupe ... --arka-plan --filigran`.
- "no base platform" yazılsa da ince bir zemin çizgisi gelebilir; zararsızdır, dekupe ile kalır.

## İndirme (Yönetici yapar; `tarayici.md` → İndirme protokolü)
- Düğme görselin üstünde (hover) ya da altında: "Tam boyutlu resmi indir" / "Download full size image". JS ile `click()` yalnızca ilk indirmede çalışabiliyor; sonrakiler için gerçek tıklama (`find` → ref → `left_click`).
- Her indirmeden hemen sonra: `ma indir-bekle sirket/projeler/<proje>/cizim/ham <ad_uzantisiz>` (göreli yol proje köküne göredir; desen varsayılanı `Gemini_Generated_Image_*`). Çıkış 1 = dosya gelmedi → gerçek tıklamayla tekrar dene.
- Üretim çıktısı çoğunlukla **JPEG, 2048×2048** gelir (`.png` beklenirken); uzantı korunur.
- ❌ **Düzenlenmiş (edit) görsellerde** tam boyutlu indirme onaylanandan farklı bir görsel verebilir. İndirileni önizlemeyle karşılaştır; farklıysa sayfada gösterilen sürümü (≈1024 px) kaydet. Sayıların önemli olduğu bir düzenlemede indirmeden sonra sayıları yeniden say.

## Dekupe notları
- Beyaz nesnelerde kalın kapalı kontur sayesinde varsayılan eşik genelde yeter. Dekupe aracının "figür içi beyaz aday" diye listelediği alanlar (beyaz kumaş, kubbe, bulut) zemin değildir; `--tohum` verilmez.
- Açık/kapalı göz düzenlemesi genelde piksel hizalı gelir; `ma dekupe ... --grup` aynı kutuyla kırpar.

## Kota
Günlük görsel üretim sınırına takılırsan (uyarı metni çıkar) dur, `engellendi` raporla; ertesi gün devam edilir. Yükseltme/ödeme ekranında hiçbir şeye tıklama.
