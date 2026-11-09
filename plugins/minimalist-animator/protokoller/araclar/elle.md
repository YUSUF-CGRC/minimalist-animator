# Elle (kullanıcının kendi görselleri ve sesleri)

`ayarlar.json` → `araclar.gorsel_araci: "elle"` ve/veya `araclar.ses_araci: "elle"` iken geçerlidir. Tarayıcı kullanılmaz, indirme onayı yoktur: dosyaları kullanıcı kendisi üretir (başka bir çizim programı, kendi sesi, başka bir servis) ve proje klasörüne bırakır; ajanlar yalnızca işler.

## Görseller (`gorsel_araci: elle`)
1. Senarist `senaryo.json` → `varliklar`'ı yazdıktan ve kullanıcı senaryoyu onayladıktan sonra Çizer önce arşive bakar (`ma envanter ara <terim>`); arşivde olanları projeye bağlar (`ma envanter kullan`).
2. Kalanlar için Çizer `cizim/istek-listesi.md` yazar: her varlık için dosya adı (`<id>_acik.png`, `<id>_kapali.png`, nesnede `<id>.png`, arka planda `<id>.png`), tarif, görünüş/doğruluk notları, boyut önerisi (karakter/nesne kare ve en az 1024 px; arka plan 9:16) ve zemin kuralı (düz beyaz zemin ya da zaten şeffaf PNG).
3. Yönetici listeyi kullanıcıya özetler ve dosyaları `sirket/projeler/<proje>/cizim/ham/`'a bırakmasını ister; proje `ma proje bekle <proje> "görseller (elle)"` ile bekler.
4. Dosyalar gelince Çizer: eksik/yanlış adlı dosyayı raporlar, `ma dekupe` ile dekupe eder (şeffaf PNG geldiyse dekupe gerekmez, `cizim/hazir/`'e kopyalanır), önizlemeyi inceler ve `ma envanter ekle ... --kaynak "kullanıcı (elle)"` ile arşive işler. Stil tutarsızlığı varsa raporlar ama yeniden çizmez.

## Sesler (`ses_araci: elle`)
1. Seslendirmen `ses/kayit-listesi.md` yazar: konuşan başına satırlar sırayla, her satır ayrı paragraf, telaffuz notları, beklenen süre; tek dosya kayıt önerisi (`<konusan>_tum.wav|mp3`), satırlar arasında ~1 sn sessizlik.
2. Yönetici kullanıcıdan dosyaları `sirket/projeler/<proje>/ses/ham/`'a bırakmasını ister; proje bekler.
3. Dosyalar gelince Seslendirmen `ma ses-bol <proje> --girdi ses/ham/<dosya> --konusan <id>` ile böler, uyarıları inceler, ses kimliğini `ses-kimlikleri.json`'a "kullanıcı kaydı" olarak işler.

## Kurallar
- Kullanıcının dosyasının telif/kişilik hakkı kullanıcının sorumluluğundadır; başka bir kanalın görseli ya da gerçek kişinin sesi olduğu anlaşılıyorsa Yönetici bir kez sorar (kritik 7).
- Görsel ya da ses gelmeden de animasyon denenebilir: ses için `ma taslak-ses <proje>` (`taslak.md`).
