# İletişim, Talepler ve Kritik Konular

Ajanlar birbirini doğrudan çağıramaz; **her şey Yönetici üzerinden** akar. Kullanıcıya da yalnızca Yönetici yazar. Ajanlar konuşmak istediklerini iki yerde bırakır:

1. Proje klasöründeki `talepler.md` dosyasına (kalıcı kayıt).
2. Görev sonunda Yönetici'ye döndükleri **RAPOR** bloğuna (Yönetici bunu okuyup yönlendirir).

## Her ajanın görev sonu raporu

Her ajan işini şu blokla bitirir (son mesajında, aynen bu başlıklarla):

```
## RAPOR
ajan: cizer
proje: 2025-05-12_ay-yuzu
durum: tamam | kismi | engellendi
yapilanlar:
  - Kaşif karakteri görsel aracında üretildi (3. denemede), stil kontrolünden geçti
ciktilar:
  - cizim/cizim-raporu.md
indirme_listesi:            # sadece tarayıcıdan indirme gerekiyorsa
  - dosya: kasif_acik.png | kaynak: gemini.google.com (sohbet: "<marka> - Ay") | boyut: ~2 MB
talepler:
  - kime: senarist
    ne: "Sahne 4'teki 'rasathane iç mekân' görseli yerine dış sahne öneriyorum"
    neden: "İç mekân chibi stilde okunmuyor, 3 deneme başarısız"
    oncelik: normal          # dusuk | normal | yuksek
yoneticiye_sorular:
  - "Ses aracında 1.200 karakter kredi kaldı, senaryo 640 karakter. Devam edeyim mi?"
kritik: hayir               # evet ise Yönetici bunu kullanıcıya taşır
ogrendiklerim:
  - "'saf beyaz arka plan' yerine '#FFFFFF düz beyaz zemin, gölge yok' deyince daha temiz geliyor"
```

`ogrendiklerim` maddelerini ajan kendi hafızasına da yazar (ajan hafızası proje kapsamlıdır).

## talepler.md formatı

```
### T-003 | animator → cizer | yuksek | ACIK
14:20 — Ay görselinin sağ alt köşesinde gri gölge var, dekupe kenarında leke bırakıyor. Gölgesiz yeniden üretim ya da mevcut görselin rötuşu.
→ Yönetici 14:25: Çizer'e iletildi.
→ Çizer 14:50: "gölgeyi kaldır" düzenlemesi yapıldı, indirme listesine eklendi. KAPANDI
```

Durumlar: `ACIK` → `ILETILDI` → `KAPANDI` / `REDDEDILDI (gerekçe)` / `KULLANICIYA SORULDU`.

## Yönetici'nin yönlendirme kuralları

- Talep hedef ajanın işiyse ilet; değilse gerekçesiyle reddet.
- Aynı konuda 3. revizyon da başarısızsa → kullanıcıya sor (kısa, seçenekli).
- Talep bir kalite kapısını (`kalite-kontrol.md`) etkiliyorsa önceliği `yuksek` yap.
- Tarayıcı gerektiren talepler sıraya alınır; asla iki tarayıcı ajanı aynı anda çalışmaz.

## Kritik sayılanlar (Yönetici bunları kendi başına karara bağlamaz → kullanıcıya)

1. **Tarayıcıdan dosya indirme** (günde tek toplu liste, bütün projeler birlikte).
2. İzinli alan listesine (`sirket/izinli-alanlar.json`) **yeni site** eklemek — özellikle giriş/form/ödeme içeren siteler.
3. Para harcanması, kredi/abonelik yükseltme, ücretli özellik kullanımı gereken her şey.
4. Bir site **giriş, doğrulama kodu ya da CAPTCHA** istiyorsa.
5. Markanın kalıcı kimliğini değiştiren kararlar: **yeni tekrar eden karakter** tasarımı (ilk kez çizilen ana karakter), stil referansının belirlenmesi, yeni karakter **ses kimliği** seçimi, logo/slogan/renk/varsayılan yazı tipi değişikliği, yeni seri formatı.
6. Dinî, siyasi, etnik açıdan hassas ya da kaynaklar arasında **çelişkili** bilgiler.
7. Telif ve kişilik hakkı riski: gerçek bir kişinin sesi/yüzü (özellikle birinci ağızdan konuşturma), başka bir kanalın içeriğini birebir uyarlama, telifli müzik ya da yazı tipi.
8. 3 revizyon turunda çözülemeyen her sorun.
9. Analistin önerdiği strateji değişiklikleri (paylaşım sıklığı, platform önceliği, içerik yönü).
10. Bilgisayara bir şey kurmak ya da yapılandırmak: Python paketi, `.claude/settings.json` izinleri, zamanlanmış görev, font dosyası indirme.

Kritik olmayan örnekler (Yönetici karar verir, günlüğe yazar): sahne sırası, efekt seçimi, bir görselin tekrar çizdirilmesi, altyazı vurgu kelimeleri, video süresinin ±5 sn oynaması, aynı karakterin yeni pozu.

## Kullanıcıya soru sorma biçimi

- **Günde tek soru turu.** Uzun metin yazma; **AskUserQuestion** kullan: en fazla `akis.gunluk_soru_siniri` soru (`ayarlar.json`), önerdiğin seçenek ilk sırada ve "(Önerilen)" etiketli, gerekçe açıklamada tek cümle. Küçük onaylar tek multiSelect soruda toplanır. Görseller/videolar sorudan önce SendUserFile ile gönderilir. Kullanıcı soru yerine "onay" yazarsa önerilerin uygulanır. Acil olmayan hiçbir şey için gün içinde ikinci tur açma.
- İstisna: kullanıcının sohbette kendisinin başlattığı iş (`yeni-video`, `senaryom`, `kurulum`, `otomatik-dongu`, Ofis paneli mesajı) sırasında gereken sorular günlük turu bozmaz — kullanıcı ekrandadır.
- Her soruya "neden soruyorum" yarım cümle. Sohbette kullanıcıya `kullanici.ad` ile hitap et.
- `sirket/kullanici/sorular.md`'ye tarih ve proje ile kaydet; cevap gelince altına işle.
- Bildirim (PushNotification) 200 karakteri geçmez: "<marka>: 9 dosya + 2 karar için sorular bekliyor".
