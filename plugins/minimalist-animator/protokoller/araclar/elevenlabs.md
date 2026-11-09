# ElevenLabs (ses aracı) — Arayüz, Ayarlar, İndirme

`ayarlar.json` → `araclar.ses_araci: "elevenlabs"` iken Seslendirmen bu dosyayı okur. Tarayıcı kuralları: `tarayici.md`. Projeye özgü öğrenimler (arayüz, telaffuz hileleri, iyi ayarlar) `sirket/arsiv/arac-notlari.md` → "ElevenLabs" bölümüne ve Seslendirmen'in hafızasına yazılır.

## Arayüz
- Adres: `https://elevenlabs.io/app/speech-synthesis/text-to-speech` (izinli alan: `sirket/izinli-alanlar.json` → `seslendirmen`). Girişi kullanıcı yapar; giriş ekranı çıkarsa dur.
- Arayüz değişebilir; öğeleri `find` / `read_page` ile adından bul (ses seçici, model seçici, ayarlar paneli, "Generate", History).
- **Önce kalan krediyi oku** (kenar çubuğu / profil menüsü / abonelik sayfası) ve rapora yaz. Senaryonun metin uzunluğu kalan krediyi aşıyorsa **üretme**, Yönetici'ye sor. Yükseltme ekranında hiçbir şeye tıklama.

## Ses seçimi (yeni karakter)
- Voice Library'de `icerik.dil` dilindeki sesleri karakterin yaşına, cinsiyetine, kişiliğine göre filtrele; **2 aday** belirle (ad, kısa tarif, neden).
- Kısa bir deneme cümlesi (≤ 80 karakter) üret; dinleyemediğin için süre/akıcılık bilgisini not et. Kullanıcıdan History'den dinlemesini iste (Yönetici sorar).
- Bir sesi "My Voices"a eklemek gerekiyorsa ekle; slot sınırı doluysa Yönetici'ye sor (hiçbir sesi silme).
- Gerçek bir kişinin sesini klonlamak ya da taklit eden ses seçmek kritik karardır.

## Ayarlar
- Kimlikteki ses, model ve ayarları (stability, similarity, style, speaker boost) seç; ekran görüntüsüyle doğrula.
- **Etiketsiz, tek üslup:** metin duygu etiketi olmadan seslendirilir (`uslup.md` → Ses kimliği). Senaryoda etiket kalmışsa (izinli en fazla 1) fazlasını sil ve raporla. Çok etiket sesi her satırda başka biri gibi yapar; [softly] gibi etiketler karakteri aşırı kibar yapar.
- Tutarlılık için stability'yi düşük tutma (öneri 0.6–0.7 ya da arayüzdeki "Natural"/"Robust"); yeni ayarı `ses-kimlikleri.json`'a yaz.

## Metin düzeni
- Bir karakterin bütün satırlarını senaryo sırasıyla, her satır ayrı paragrafta olacak şekilde **tek üretimde** seslendir (tutarlı tını, az kredi, az indirme). Satır aralarına ekstra "..." koyma; paragraf boşluğu yeterli duraklama verir. Diyalog formatında her konuşan için ayrı bir üretim yap.
- Riskli özel isimleri gerekirse hece hece/fonetik yaz; altyazı metnini değiştirme.
- Üretilen sesin süresini oku: beklenen (`icerik.konusma_hizi_kar_sn` ile) ile %35'ten fazla fark varsa (atlanan cümle, takılma şüphesi) aynı üretimi bir kez daha dene ve iki sürümü listeye koy.

## İndirme (Yönetici yapar; `tarayici.md` → İndirme protokolü)
- Seslendirmen indirmez; `indirme_listesi`'ne hedef ad (`kasif_tum.mp3`), kaynak (elevenlabs.io → History, üretimin ilk kelimeleri ve saati), ~boyut yazar ve sekmeyi açık bırakır.
- History'de indir simgesi menü açar; en üstteki "MP3 44.1kHz/128kbps". Sonra `ma indir-bekle sirket/projeler/<proje>/ses/ham <ad_uzantisiz> "ElevenLabs_*"`.
- İndirilen sesin süresini rapordaki üretim süresiyle eşleştir (aynı başlıklı birden çok üretim olabilir).

## Kota ve koşullar
Ücretsiz planın aylık kredisi sınırlıdır ve ticari kullanım/atıf koşulları içerir; Yönetici kurulumda kullanıcıya bir kez hatırlatır. Kredi bittiyse dur, `engellendi` raporla; Yönetici bunu günün sorularına KARAR olarak koyar.
