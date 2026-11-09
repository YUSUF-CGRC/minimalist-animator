# Taslak ses (çevrimdışı mırıltı)

`ayarlar.json` → `araclar.ses_araci: "taslak"` iken, ya da gerçek ses gelmeden kurguyu denemek için kullanılır. Tarayıcı, hesap, kredi ve indirme gerekmez.

- Komut: `ma taslak-ses <proje> [--zorla]`. Senaryodaki her satır için anlamsız, konuşma ritminde bir mırıltı sesi üretir; süreyi metin uzunluğundan ve `icerik.konusma_hizi_kar_sn`'den hesaplar.
- Çıktı: `ses/parcalar/NN_<konusan>.wav` + `ses/zamanlama.json` (`ma ses-bol` ile aynı şema, `"kaynak": "taslak"`). Animatör bu dosyalarla normal şekilde çalışır.
- Gerçek ses varsa (`kaynak` ≠ `taslak`) üzerine yazmaz; `--zorla` yalnızca kullanıcı isterse.
- Kullanım yerleri: `ma demo`; senaryo onayından sonra görselleri ve kurguyu erkenden görmek; gerçek ses gelince parçalar `ma ses-bol` ile değiştirilir ve render yeniden alınır (zamanlama satırlara bağlı olduğu için kurgu kendiliğinden kayar).
- **Taslak sesli video önizlemedir, yayınlanmaz.** Yönetici teslimde bunu açıkça söyler; `yayin-paketi.md`'nin başına "ÖNİZLEME — taslak ses" yazılır. `ses_araci: taslak` kalıcı ayarsa her teslimde kullanıcıya gerçek sesin nasıl ekleneceği (`elle.md` ya da `elevenlabs.md`) tek cümleyle hatırlatılır.
