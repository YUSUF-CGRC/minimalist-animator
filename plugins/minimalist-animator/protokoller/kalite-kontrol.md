# Kalite Kontrol Listeleri

Her aşamanın sonunda ilgili liste uygulanır. "Hayır" çıkan madde → gerekçesiyle aynı ajana revizyon. Yönetici listeyi `gunluk.md`'ye "KK: geçti / 2 madde döndü" diye işler. Senaryo modu (`durum.json` → `senaryo_modu`) bazı maddeleri değiştirir; aşağıda belirtilmiştir.

## Araştırma (`arastirma.md`) — `ajan` ve `kendi-arastir`
- [ ] Her bilgi en az bir **akademik ya da birincil** kaynağa bağlı (hakemli dergi, ansiklopedi maddesi, üniversite/kurum yayını, müze/arşiv kaydı, resmî veri). Wikipedia ve popüler siteler tek başına kaynak değildir, sadece başlangıç noktasıdır.
- [ ] Önemli iddialar (tarih, "ilk", "en", sayı) en az 2 bağımsız kaynakla doğrulandı.
- [ ] Tartışmalı/çelişkili bilgiler ayrı bölümde, hangi kaynağın ne dediğiyle.
- [ ] "Kullanılabilir şaşırtıcı bilgiler" (hook adayları) listesi var (`ajan` modu).
- [ ] Sayılar ve tarihler seslendirme için `icerik.dil`'de yazıyla da yazılmış.
- [ ] `kendi-arastir`: `oneriler.md` var; her öneride satır, öneri, neden, kaynak; kullanıcı metnine dokunulmamış.

## Senaryo (`senaryo.md` + `senaryo.json`)
- [ ] `senaryo.md`'nin başında etiketsiz, tek paragraf **Okunuş** var; sesli okununca akıyor (bağlaçlar, tekrar yok, "..." ile bölünmüş cümle yok).
- [ ] Duygu etiketi yok (bütün videoda en fazla 1 istisna); `etiketli` = `metin`.
- [ ] Ünlem bütün videoda en fazla 2.
- [ ] Her satır için "ekranda ne oluyor" yazılı; ekran 2–3 sn'den uzun durağan kalmıyor.
- [ ] `varliklar` listesi tam; arşivde olanlar `arsivde_var: true` ve dosya yoluyla işaretli.
- [ ] Altyazı vurgu kelimeleri seçili (cümle başına 1–2).
- [ ] `ma kontrol <proje> --senaryo` temiz (gönderide `--post`).
- [ ] **`ajan` modu:** hook ilk 1.5 sn'de (soru ya da şaşırtıcı bilgi); toplam konuşma ≈ 28–38 sn (`icerik.konusma_hizi_kar_sn` ile); her bilgi cümlesi `arastirma.md`'deki bir maddeye bağlı (`[K3]`); kapanışta izleyiciye dönük soru/çağrı.
- [ ] **`kendi-arastir`:** yalnızca kullanıcının kabul ettiği öneriler uygulandı; geri kalan metin kullanıcınınki.
- [ ] **`kendi-duzenle`:** bilgi eklenmedi/çıkarılmadı; değişiklik listesi `senaryo.md`'de.
- [ ] **`kendi-aynen`:** `altyazi` birleşimi kullanıcı metniyle sözcüğü sözcüğüne aynı; `metin` yalnızca sayı/sembol/kısaltmada ayrılıyor. Süre ve hook maddeleri yalnızca bilgi notudur.

## Görseller (`cizim/`)
- [ ] Arşivde olan hiçbir şey yeniden çizilmedi.
- [ ] Stil referansla tutarlı (çizgi kalınlığı, renk doygunluğu, oranlar — `gorsel.cizim_uslubu`).
- [ ] Zemin düz beyaz, gölge/yazı/filigran yok (dekupe edilebilir). Arka planlar hariç.
- [ ] Olgusal doğruluk: kıyafet, mimari, nesne, bilimsel çizim konuya uygun (Araştırmacı'nın görsel doğruluk notlarına göre).
- [ ] Karakter için `acik` + `kapali` (göz kırpma) varyantları var; aynı poz, aynı çerçeve.
- [ ] `cizim/hazir/` içindeki PNG'ler dekupe edilmiş, kenarda beyaz hale yok (`ma dekupe` önizlemesi kontrol edildi).
- [ ] Envantere işlendi (`ma envanter ekle`).

## Ses (`ses/`)
- [ ] Ses kimliği `ses-kimlikleri.json` ile birebir aynı (ses adı, model, ayarlar).
- [ ] Her satır ayrı parça; parça sayısı = senaryo satır sayısı (`zamanlama.json`).
- [ ] Baş/son sessizlik kırpılmış, parçalar arası seviye dengeli.
- [ ] Özel isimler doğru okunmuş (raporda Seslendirmen'in kontrol notu).
- [ ] Taslak ses (`"kaynak": "taslak"`) kullanıldıysa video yalnızca önizlemedir; yayın paketinde ve teslimde bu açıkça yazılı.

## Animasyon (`cikti/<proje>.mp4`)
- [ ] `ma kontrol <proje>` temiz: çözünürlük, fps, süre, ses akışı, ses seviyesi, siyah/donuk kare yok.
- [ ] Kontrol kareleri (her sahne en az 1 kare) incelendi: altyazı güvenli alanda, yazılar kesilmiyor, karakter kadraj içinde.
- [ ] Altyazılar sesle eşzamanlı (±0.15 sn), vurgu kelimeleri vurgu renginde.
- [ ] İlk kare boş değil, karakter görünür.
- [ ] Kapanış kartı var ve en az 2 sn.
- [ ] Projeye özel font istendiyse (`durum.json` → `font`) karelerde o font görünüyor.

## Gönderi (`cikti/kare-*.png`)
- [ ] `ma kontrol <proje> --post` temiz; kontak sayfası (`cikti/kontak.png`) incelendi.
- [ ] Kare başına az metin, okunur; güvenli kenar 80 px; son karede çağrı + marka.

## Final (Yönetici)
- [ ] Videoyu baştan sona kareler üzerinden izledin (en az 8 kare, her sahneden).
- [ ] Bilgiler `arastirma.md` (ya da kullanıcı metni) ile tutarlı; yanlış ya da abartılı bir iddia yok.
- [ ] `yayin-paketi.md` tam: platformlara (`icerik.platformlar`) göre açıklama/başlık, hashtagler, önerilen saat + gerekçe, kaynaklar.
- [ ] Kapak karesi seçildi.
- [ ] Konu `islenen-konular.json`'a "üretildi" olarak işlendi.
