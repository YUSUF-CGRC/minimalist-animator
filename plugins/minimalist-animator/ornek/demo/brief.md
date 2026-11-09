# Brief — Demo: Ay neden hep aynı yüzünü gösterir?

- **Proje:** 0000-00-00_demo
- **Format:** monolog
- **Senaryo modu:** ajan — örnek proje (motor testi; ağ, görsel aracı ya da ses aracı gerekmez)
- **Hedef süre:** ~15 sn (kapanış kartıyla)
- **Neden bu konu:** Herkesin gördüğü ama nedenini az kişinin bildiği, doğrulaması kolay bir bilgi.
- **Hedef duygu:** merak → "aa, demek öyle!"
- **Hook fikri:** Soru: "Ay neden hep aynı yüzünü gösterir?" + karakter kenardan bakar, soru işareti.
- **Anlatılacak:**
  1. Ay, Dünya'nın çevresinde dolanırken kendi çevresinde de döner.
  2. İki hareket de yaklaşık 27 gün sürer (eş zamanlı dönme / gelgit kilitlenmesi).
  3. Bu yüzden Dünya'dan hep aynı yüzü görürüz.
- **Kaçınılacaklar:** "Ay hiç dönmez" yanılgısı; abartı.
- **Kapanış çağrısı:** marka kartı (logo ya da marka adı) + karakter.

## Kaynak
- **K1:** NASA Science, "Tidal Locking" (Earth's Moon) — Ay'ın kendi ekseni çevresindeki dönüşü ile Dünya
  çevresindeki dolanımı yaklaşık 27,3 gün sürer; bu yüzden Dünya'ya hep aynı yarım küresi bakar.
  https://science.nasa.gov/moon/tidal-locking/

## Dosyalar
- `senaryo.json` — 4 satır; olaylar: karakter-giris, soru-isareti, nesne, etiket, buyuk-metin, efekt, parilti.
- `hazirla.py` — kaşif karakterini (açık / kapalı göz / konuşma) ve Ay, Dünya nesnelerini PIL ile çizer
  (`cizim/hazir/`). Ses: `ma taslak-ses` mırıltı sesi üretir.
- Çalıştırma: `ma demo` (kopyalar, çizer, taslak ses, render, kontrol).
