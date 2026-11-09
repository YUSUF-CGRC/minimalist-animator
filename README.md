# Minimalist Animatör

**Claude ajanlarından oluşan bir içerik stüdyosu.** Konunu verirsin (tarih, bilim, sanat, ne istersen); ekip araştırır, senaryoyu yazar ya da **senin senaryonu sahneler**, görselleri çizdirir, seslendirir ve Python koduyla **dikey kısa video** (Reels / Shorts / TikTok) ve **Instagram gönderisi** (kaydırmalı ya da karikatür) üretir. **Hiçbir şeyi kendi başına yayınlamaz**: son sözü ve paylaşımı sen yaparsın.

[English below](#english)

```
                 ┌──────────── SEN ────────────┐
                 │ senaryo onayı · indirme onayı · final onay │
                 └──────────────▲──────────────┘
                                │ günde tek soru turu
                          ┌─────┴─────┐
                          │ YÖNETİCİ  │  (ana Claude oturumu)
                          └─────┬─────┘
   ┌──────────┬─────────┬───────┼────────┬──────────────┬───────────┐
Analist   Araştırmacı  Senarist  Çizer   Seslendirmen   Animatör
```

| Ajan | Ne yapar |
|---|---|
| **Yönetici** (ana oturum) | İşi planlar, ajanları çağırır, kaliteyi denetler, sana tek seferde soru sorar. |
| Analist | Hesaplarını ve benzer kanalları tarayıcıdan okur, fikir önerir. |
| Araştırmacı | Konuyu **kaynaklı** araştırır, senaryonun doğruluğunu denetler. |
| Senarist | Akıcı bir senaryo yazar ya da senin metnini sahneler. |
| Çizer | Görselleri Gemini'de çizdirir (ya da senin görsellerini işler), arşivler. |
| Seslendirmen | Sesi ElevenLabs'te üretir (ya da senin kaydını / çevrimdışı taslak sesi kullanır), satırlara böler. |
| Animatör | Görsel ve sesten videoyu Python ile üretir, kendi kontrolünü yapar. |

## Senaryo: sen mi yazarsın, ekip mi?

Her yeni videoda Yönetici sorar (varsayılanı kurulumda seçersin):

| Seçenek | Ne olur |
|---|---|
| **Ekip yazsın** (`ajan`) | Araştırma → senaryo → doğruluk kontrolü → metni sen onaylarsın. |
| **Benim metnim, araştırıp öner** (`kendi-arastir`) | Kısa bir araştırma yapılır, düzeltme önerileri ayrı listelenir; hangilerinin uygulanacağına sen karar verirsin. |
| **Benim metnim, sadece anlaşılır yap** (`kendi-duzenle`) | Araştırma yok; cümleler daha akıcı ve anlaşılır hâle getirilir, bilgi eklenmez ya da çıkarılmaz. |
| **Benim metnim, aynen** (`kendi-aynen`) | Kelimelerine dokunulmaz; ekip yalnızca satırlara böler ve sahneler. Bir sözcük bile değişirse kontrol aracı hata verir. |

Kendi metnini sohbete yapıştırabilir, `/minimalist-animator:senaryom` komutunu kullanabilir ya da Ofis panelindeki **"Senaryomu ver"** kutusuna yazabilirsin.

## Gereksinimler

- [Claude Code](https://claude.com/claude-code) (terminal ya da Claude masaüstü uygulaması)
- Python 3.10+ ve şu paketler: `numpy`, `Pillow`, `opencv-python-headless`, `imageio-ffmpeg` (kurulum gerekirse senin onayınla yükler; ayrıca ffmpeg kurman gerekmez)
- Görsel ve ses için (isteğe bağlı): Chrome'da **Claude in Chrome** eklentisi ve **kendi** Gemini / ElevenLabs hesaplarına giriş. Bunlar olmadan da çalışır: görselleri ve sesleri kendin verebilir ya da çevrimdışı taslak sesle önizleme yapabilirsin.

## Kurulum

Terminalde:

```
/plugin install minimalist-animator --marketplace YUSUF-CGRC/minimalist-animator
```

Ofis paneli (isteğe bağlı, masaüstü uygulaması için):

```
/plugin install minimalist-animator-ofis --marketplace YUSUF-CGRC/minimalist-animator
```

Claude masaüstü uygulamasında: istem kutusunun yanındaki **+** → **Plugins** → **Add marketplace** → `YUSUF-CGRC/minimalist-animator` → **Add plugin**.

Sonra **boş bir klasörde** bir oturum aç ve şunu yaz:

```
/minimalist-animator:kurulum
```

Kurulum sana marka adını, içerik dilini, konu alanını, adını, varsayılan senaryo seçeneğini ve görsel/ses araçlarını sorar; klasörü hazırlar ve çevrimdışı bir **demo video** üretip gösterir.

## Kullanım

| Ne istiyorsun | Yaz |
|---|---|
| Yeni video | `/minimalist-animator:yeni-video Ay neden hep aynı yüzünü gösterir?` |
| Kendi senaryonla video ya da gönderi | `/minimalist-animator:senaryom` |
| Durum özeti | `/minimalist-animator:durum` |
| Günlük döngüyü şimdi çalıştır | `/minimalist-animator:gunluk-dongu` |
| Her sabah otomatik çalışsın (varsayılan kapalı) | `/minimalist-animator:otomatik-dongu` |
| Ofis panelini aç | `/ofis` |

Çıktılar `sirket/projeler/<tarih>_<konu>/cikti/` içinde durur: MP4 (ya da gönderi kareleri) ve `yayin-paketi.md` (açıklama, hashtag, önerilen saat, kaynaklar).

### Yazı tipi

Varsayılan yazı tipi **Barlow** (OFL lisanslı, Türkçe harfleri tam). Bir video için başka bir font istersen Yönetici'ye söyle: font dosyası `sirket/arsiv/fontlar/` klasöründe tutulur, yalnızca o video o fontla üretilir, diğer fontlar kenarda bekler.

### Ayarlar

Her şey proje kökündeki `ayarlar.json` dosyasında: marka adı, slogan, logo, hesaplar, adın, içerik dili, konu alanı, ton, ekrandaki çağrı metinleri ("Kaydet, birine gönder"), renkler, font, görsel ve ses aracı, varsayılan senaryo seçeneği, haftalık plan ve kullanım eşiği.

## Güvenlik ve sınırlar

- **Yayın yok:** ajanlar paylaşmaz, yorum yazmaz, beğenmez, mesaj atmaz.
- **Giriş, şifre, ödeme yok:** bir site giriş ya da CAPTCHA isterse ekip durur ve sana söyler.
- **İndirme yalnızca senin onayınla:** tarayıcıdan dosya indirmeden önce dosya listesi sana sorulur; indirmeyi ana oturum yapar.
- **İzinli siteler:** tarayıcı kullanan ajanlar yalnızca `sirket/izinli-alanlar.json` listesindeki sitelere gidebilir; bir kanca bunu zorunlu kılar.
- **Doğruluk:** videodaki her bilgi kaynağa bağlanır; tartışmalı bilgi işaretlenir ya da çıkarılır.
- **Ses lisansı:** ElevenLabs'in ücretsiz planı ticari kullanımı kısıtlayabilir ve atıf isteyebilir; kendi planının koşullarına bak.
- **Ses kalitesi:** ajanlar sesi kulakla duyamaz; finalde videoyu bir kez dinlemen önemli.

## Lisans ve bir rica

[MIT](LICENSE): herkes kullanabilir, değiştirebilir, ticari işlerde de kullanabilir. Fontlar ayrıca SIL Open Font License 1.1 ile lisanslıdır.

**Rica (zorunlu değil):** Bu eklentiyle ürettiğin videoları paylaşırken açıklamaya şöyle bir satır eklersen çok seviniriz:

> Benzer animasyonlar için: github.com/YUSUF-CGRC/minimalist-animator

Bu eklenti, [Maziden](https://www.instagram.com/maziden.official/) için kurulan bir içerik stüdyosundan genelleştirildi; markaya ait görseller, karakterler ve veriler repoda yoktur. Ayrıntılar: [NOTICE](NOTICE).

---

## English

**Minimalist Animatör** is a content studio made of Claude agents. Give it a topic (history, science, anything); the team researches it, writes the script **or stages your own script**, has images drawn, voices it and renders **vertical short videos** (Reels / Shorts / TikTok) and **Instagram posts** with Python. **It never publishes anything on its own.**

The agent instructions are in Turkish; the **content language of your videos is configurable** (`icerik.dil` in `ayarlar.json`).

**Script options** (asked for every video): the team writes it (`ajan`) · your text + research-based suggestions you approve (`kendi-arastir`) · your text, only made clearer (`kendi-duzenle`) · your text, word for word (`kendi-aynen`, enforced by the checker).

**Install** (terminal):

```
/plugin install minimalist-animator --marketplace YUSUF-CGRC/minimalist-animator
/plugin install minimalist-animator-ofis --marketplace YUSUF-CGRC/minimalist-animator
```

In the Claude desktop app: **+** → **Plugins** → **Add marketplace** → `YUSUF-CGRC/minimalist-animator` → **Add plugin**. Then, in an empty folder, run `/minimalist-animator:kurulum`: it asks for your brand, language, topic area, script default and tools, sets up the folder and renders an offline demo video.

**Requirements:** Claude Code, Python 3.10+ with `numpy`, `Pillow`, `opencv-python-headless`, `imageio-ffmpeg`. Optional: the Claude in Chrome extension with your own Gemini / ElevenLabs sign-ins (you can also supply images and audio yourself, or use the offline draft voice).

**Safety:** no publishing, no logins/passwords/payments, browser downloads only after your explicit approval, browser agents restricted to an allow-list by a hook, every fact tied to a source.

**License:** [MIT](LICENSE); fonts under the SIL OFL 1.1. A kind request (not required): if you share videos made with it, a line like *"For similar animations: github.com/YUSUF-CGRC/minimalist-animator"* in your description would make our day. Generalized from a studio built for [Maziden](https://www.instagram.com/maziden.official/); no brand assets are included ([NOTICE](NOTICE)).
