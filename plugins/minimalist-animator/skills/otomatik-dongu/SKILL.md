---
name: otomatik-dongu
description: Günlük döngünün her gün belirli bir saatte kendiliğinden çalışmasını kurar, değiştirir ya da kapatır (varsayılan KAPALI). Claude masaüstü uygulamasının zamanlanmış görevleri varsa kullanıcının onayıyla günlük döngü ve isteğe bağlı kesinti sonrası devam görevi kurar; yoksa elle kurulum adımlarını yazar. Kullanıcı "otomatik çalışsın", "her sabah kendiliğinden başlasın", "zamanla", "otomatik döngüyü kapat" dediğinde kullanılır.
---

# Otomatik döngü (Yönetici)

Varsayılan **kapalı** (`ayarlar.json` → `akis.otomatik_dongu: false`). Yalnızca kullanıcı isterse kurulur; zamanlanmış görev kurmak kritik karardır (açık onay). Kullanıcı sohbette olduğu için bu sorular günlük soru turunu bozmaz.

1. **Saat:** AskUserQuestion ile sor: günlük döngü saati ("09:00 (Önerilen)" / "07:00" / "13:00" / Other) ve kesinti sonrası devam görevi isteniyor mu ("Evet, 3 saat sonra bir kez daha dene (Önerilen)" / "Hayır"). Devam görevi, limit dolduğu ya da oturum düştüğü için yarım kalan işi kilit boşaldıysa sürdürür.
2. **Araç var mı:** `ToolSearch` ile `mcp__scheduled-tasks__create_scheduled_task` (ve `list_scheduled_tasks`, `update_scheduled_task`) araçlarını yükle. Önce `list_scheduled_tasks` ile bu klasör için kurulmuş bir görev var mı bak; varsa yenisini kurma, güncelle.
3. **Onay:** Kurulacakları tek cümleyle özetle (görev adları, saatler, ne yapacakları) ve AskUserQuestion ile açık onay al.
4. **Kur** (araç varsa). Görevler yerel saatle cron alır (`"0 9 * * *"` = her gün 09:00). Her görevin istemi kendi kendine yeterli olmalı (her çalıştırma bu sohbeti hatırlamaz); proje klasörünün **mutlak yolunu** yaz:
   - `taskId`: `<klasör-adı>-gunluk-dongu`; istem: "Çalışma klasörün `<mutlak yol>`: oraya geç (`ayarlar.json` orada olmalı; yoksa hiçbir şey yapma ve tek cümleyle bildir). `ma kilit al gunluk-<tarih-saat>` çalıştır; çıkış kodu 3 ise (kilit dolu, başka oturum çalışıyor) hiçbir şey yapma, tek cümleyle bitir. Değilse `minimalist-animator:gunluk-dongu` skill'ini baştan sona uygula; bitince ya da kullanıcıyı beklemeye geçince `ma kilit birak`."
   - (İsteğe bağlı) `taskId`: `<klasör-adı>-devam`, günlük saatten 3 saat sonra; istem aynı, ama kilit sahibi `devam-<tarih-saat>` ve "bugün döngü zaten tamamlandıysa (`sirket/kullanici/gunluk-ozet.md`'de bugünün bloğu kapanmışsa ve açık iş yoksa) hiçbir şey yapma" eki.
   Sonra `ma kurulum . --ayar akis.otomatik_dongu=true` ile ayarı işaretle ve `sirket/kullanici/gunluk-ozet.md` → "Planlı işler"e görevleri yaz.
5. **Araç yoksa** (masaüstü uygulaması değil ya da zamanlanmış görevler kapalı): kurmaya çalışma. Elle kurulum adımlarını yaz: Claude masaüstü uygulamasında zamanlanmış görev oluştur (yukarıdaki istemler ve saatlerle) ya da işletim sisteminin zamanlayıcısıyla (Windows Görev Zamanlayıcı, cron, launchd) bu klasörde `claude -p "<istem>"` çalıştır — bunu kullanıcı kendisi kurar. Bulut zamanlayıcıları (uzak ajanlar) uygun değildir: yerel Chrome'a ve bu klasördeki dosyalara erişemezler.
6. **Söylenecekler:** Görevler yalnızca bilgisayar açık, uyumuyor ve Claude uygulaması çalışıyorken çalışır; uygulama kapalıysa ilk açılışta çalışır. Tarayıcı işleri için Chrome açık ve Claude in Chrome bağlı olmalı. Döngü kullanıcının yokluğunda çalışır ama yine hiçbir şey yayınlamaz, indirmeleri onaysız yapmaz; soruları günün sonunda tek turda bekler.
7. **Durdurma / kapatma:** Kullanıcı isterse `update_scheduled_task` ile görevi devre dışı bırak (ya da uygulamanın zamanlanmış görevler ekranından kendisi kapatsın), `ma kurulum . --ayar akis.otomatik_dongu=false` ile ayarı geri al ve "Planlı işler"den çıkar. Görevi silmek yerine devre dışı bırakmayı öner; silmek isterse onu da uygulamadan kendisinin yapabileceğini söyle.
