---
name: yeni-video
description: Kullanıcının verdiği konuyla hemen yeni bir video (ya da gönderi) projesi başlatır, senaryo modunu sorar ve üretim hattını (araştırma, senaryo, onay, görsel, ses, animasyon) gidebildiği yere kadar çalıştırır. Kullanıcı "X videosu yap", "X hakkında bir Reels hazırla", "yeni video" dediğinde ya da /yeni-video <konu> [format] ile kullanılır.
---

# Yeni Video (Yönetici)

Girdi: konu (zorunlu), isteğe bağlı format (`monolog` varsayılan, `zaman-yolcusu`, `biliyor-muydun`, gönderi için `post-carousel`, `post-karikatur`), isteğe bağlı yazı tipi ve kullanıcının özel notları. Kullanıcı sohbette olduğu için bu iş sırasındaki sorular günlük soru turunu bozmaz.

1. **Mod:** AskUserQuestion ile senaryo modunu sor (tek soru, 4 seçenek; `ayarlar.json` → `akis.varsayilan_senaryo_modu` olan ilk sırada ve "(Önerilen)"):
   - `ajan` — "Konuyu ekip araştırsın, metni Senarist yazsın"
   - `kendi-arastir` — "Metni ben vereceğim; ekip doğrulasın, önerilerini sorsun"
   - `kendi-duzenle` — "Metni ben vereceğim; yalnızca akıcılık için düzenlensin (araştırma yok)"
   - `kendi-aynen` — "Metnim kelimesi kelimesine kullanılsın; ekip yalnızca sahnelesin"
   Kullanıcı modu mesajında zaten söylediyse sorma. Bir kendi modu seçilirse: metni şimdi yapıştırmasını ya da dosya yolunu vermesini iste ve `minimalist-animator:senaryom` adımlarıyla devam et (metin kaydı, teyit, proje açma). Araştırma olmayan modlarda bilgilerin doğruluğunun kullanıcıda olduğunu tek cümleyle söyle.
2. `ma envanter konu-ara <konu>` — daha önce işlendiyse farklı açı öner (tek cümle) ama kullanıcı açıkça istediyse devam et.
3. Konu kritik mi (`${CLAUDE_PLUGIN_ROOT}/protokoller/iletisim.md` → Kritik sayılanlar)? Kullanıcının kendisi istediyse kritik değildir; yine de hassas bir nokta varsa (ör. gerçek bir kişiyi birinci ağızdan yapay sesle konuşturmak) tek cümleyle belirt ve önerini söyle.
4. **Yazı tipi (isteğe bağlı):** kullanıcı bu video için farklı bir font istediyse yalnızca bu proje o fontla yapılır. Dosya `sirket/arsiv/fontlar/`'da yoksa kullanıcıdan dosyayı oraya koymasını iste ya da indirmek için dosya adı, kaynak ve boyutla açık onay al (lisansı hatırlat). Proje açılınca `durum.json`'a `"font": "<dosya>.ttf"` (tek dosya, iki tür için) ya da `"font": {"kalin_dar": "<dosya>", "kalin_yari_dar": "<dosya>"}` yaz (yollar `sirket/arsiv/fontlar/`'a göre) ve brief'e not düş (`uslup.md` → Yazı tipi).
5. `ma proje yeni <slug> "<Başlık>" --format <format> --mod ajan` → `brief.md`'yi kullanıcının notlarıyla doldur.
6. `minimalist-animator:gunluk-dongu` → **2. Açık projeleri ilerlet** adımlarını bu proje için uygula (aynı kalite kapıları, aynı senaryo onayı, aynı indirme protokolü). Senaryo onayını ve indirme onayını kullanıcı ekrandaysa hemen sor.
7. Kullanıcıdan bir şey gerektiğinde (senaryo onayı, indirme onayı, yeni karakter/ses kararı, final onayı) AskUserQuestion ile kısa ve seçenekli sor; kullanıcı ekranda değilse PushNotification gönder.
