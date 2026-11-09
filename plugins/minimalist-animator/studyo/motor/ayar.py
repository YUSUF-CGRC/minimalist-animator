"""Eklenti ayarları ve proje kökü (yalnızca standart kütüphane).

Kod eklenti klasöründe (studyo/, assets/, sablon/), kullanıcının verisi proje kökünde durur:
    <proje kökü>/ayarlar.json            ("_tur": "minimalist-animator" işaretli)
    <proje kökü>/sirket/{projeler,arsiv,bilgi-bankasi,kullanici}/

Proje kökü sırası: env MA_KOK -> env CLAUDE_PROJECT_DIR (işaretli ayarlar.json varsa) -> çalışma klasöründen yukarı
doğru işaretli ayarlar.json -> çalışan betiğin klasöründen yukarı doğru. Bulunamazsa KokBulunamadi (anlaşılır mesajla
çıkar). Ayarlar = sablon/ayarlar.varsayilan.json + proje ayarlar.json (derin birleştirme, önbellekli).

    import ayar
    ayar.kok()                      -> proje kökü
    ayar.yol("sirket", "projeler")  -> proje içi yol
    ayar.al("marka.slogan")         -> nokta yoluyla tek ayar
    ayar.buyuk("istanbul")          -> "İSTANBUL" (tr/az), diğer dillerde str.upper()
"""
import copy
import functools
import json
import os
import sys

TUR = "minimalist-animator"
AYAR_ADI = "ayarlar.json"
EKLENTI = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
VARSAYILAN = os.path.join(EKLENTI, "sablon", "ayarlar.varsayilan.json")
TR_DILLER = ("tr", "az")

# eski değişken-font varyasyon adları -> font türü
FONT_TURU = {"Bold Condensed": "kalin_dar", "Bold SemiCondensed": "kalin_yari_dar",
             "kalin_dar": "kalin_dar", "kalin_yari_dar": "kalin_yari_dar"}
# dil -> konuşma hızı (karakter/sn); ayarlar.json'da icerik.konusma_hizi_kar_sn verilmişse o kullanılır
DIL_HIZI = {"tr": 16.0, "az": 16.0, "en": 14.0, "de": 14.0, "fr": 14.0, "es": 15.0, "it": 15.0, "pt": 15.0}


class KokBulunamadi(SystemExit):
    """Proje kökü yok. SystemExit'ten türer: yakalanmazsa iz dökümü yerine mesajı basıp çıkar."""


def eklenti_kok():
    return EKLENTI


def _isaretli(d):
    y = os.path.join(d, AYAR_ADI)
    if not os.path.isfile(y):
        return False
    try:
        with open(y, encoding="utf-8") as f:
            return json.load(f).get("_tur") == TUR
    except (OSError, ValueError, AttributeError):
        return False


def _yukari(d):
    d = os.path.abspath(d)
    while True:
        if _isaretli(d):
            return d
        ust = os.path.dirname(d)
        if ust == d:
            return None
        d = ust


_KOK = None


def kok():
    """Proje kökü. MA_KOK açıkça verildiyse işaret aranmaz (kurulum öncesi de geçerli)."""
    global _KOK
    if _KOK:
        return _KOK
    e = os.environ.get("MA_KOK", "").strip()
    if e:
        _KOK = os.path.abspath(os.path.expanduser(e))
        return _KOK
    c = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if c and _isaretli(c):
        _KOK = os.path.abspath(c)
        return _KOK
    for bas in (os.getcwd(), os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv and sys.argv[0] else None):
        if bas:
            d = _yukari(bas)
            if d:
                _KOK = d
                return _KOK
    raise KokBulunamadi(
        f"Proje kökü bulunamadı: '_tur: {TUR}' işaretli {AYAR_ADI} yok (çalışma klasörü: {os.getcwd()}).\n"
        f"  Yeni proje için: ma kurulum <klasör>   ya da   MA_KOK=<proje kökü> ile çalıştırın.")


def kok_var_mi():
    try:
        kok()
        return True
    except KokBulunamadi:
        return False


def sifirla():
    """Önbellekleri temizler (testler ve kurulum sonrası)."""
    global _KOK
    _KOK = None
    ayarlar.cache_clear()
    _uyarilar.clear()
    _PROJE_FONT.update(proje=None, font={})


def yol(*p):
    return os.path.join(kok(), *p)


def _birlestir(taban, ust):
    out = copy.deepcopy(taban)
    for k, v in (ust or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _birlestir(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _json_oku(y):
    with open(y, encoding="utf-8") as f:
        return json.load(f)


def proje_ayarlari():
    """Proje kökündeki ayarlar.json (birleştirilmemiş). Proje yoksa {}."""
    try:
        y = yol(AYAR_ADI)
    except KokBulunamadi:
        return {}
    if not os.path.isfile(y):
        return {}
    try:
        return _json_oku(y)
    except ValueError as e:
        raise SystemExit(f"{y} okunamadı (JSON hatası): {e}")


@functools.lru_cache(None)
def ayarlar():
    taban = _json_oku(VARSAYILAN) if os.path.isfile(VARSAYILAN) else {}
    return _birlestir(taban, proje_ayarlari())


def al(nokta_yolu, varsayilan=None):
    """al("gorsel.font.kalin_dar") -> değer; yoksa varsayilan."""
    d = ayarlar()
    for k in nokta_yolu.split("."):
        if not isinstance(d, dict) or k not in d:
            return varsayilan
        d = d[k]
    return d


_uyarilar = set()


def uyar(mesaj):
    """Aynı uyarıyı bir kez basar (stderr)."""
    if mesaj in _uyarilar:
        return
    _uyarilar.add(mesaj)
    print(f"UYARI: {mesaj}", file=sys.stderr)


# ------------------------------------------------------------------ dil
def dil():
    return str(al("icerik.dil", "tr") or "tr").strip().lower()


def buyuk(s):
    """Büyük harf: Türkçe/Azericede i -> İ, ı -> I; diğer dillerde str.upper()."""
    if dil() in TR_DILLER:
        return s.replace("i", "İ").replace("ı", "I").upper()
    return s.upper()


def kucuk(s):
    if dil() in TR_DILLER:
        return s.replace("İ", "i").replace("I", "ı").lower()
    return s.lower()


def konusma_hizi():
    """Seslendirmenin karakter/sn hızı: proje ayarı > dil tablosu > varsayılan ayar."""
    proje = (proje_ayarlari().get("icerik") or {}).get("konusma_hizi_kar_sn")
    for v in (proje, DIL_HIZI.get(dil()), al("icerik.konusma_hizi_kar_sn"), 16.0):
        try:
            if v and float(v) > 0:
                return float(v)
        except (TypeError, ValueError):
            continue
    return 16.0


def kullanici():
    return str(al("kullanici.ad", "") or "").strip() or "Kullanıcı"


def metin(ad, varsayilan=""):
    """Kullanıcıya dönük kısa metinler (metinler.cta_kapanis, metinler.kaydir ...)."""
    v = al(f"metinler.{ad}")
    return v if isinstance(v, str) else varsayilan


# ------------------------------------------------------------------ görsel
def _renk_coz(v):
    if isinstance(v, str) and v.startswith("#") and len(v) in (4, 7):
        h = v[1:]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        try:
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            return None
    if isinstance(v, (list, tuple)) and len(v) == 3 and all(isinstance(x, (int, float)) for x in v):
        return tuple(int(max(0, min(255, x))) for x in v)
    return None


def renk(ad, varsayilan=None):
    """gorsel.renkler.<ad> -> (r, g, b). [r, g, b] ya da "#rrggbb" kabul edilir; geçersizse varsayilan."""
    v = al(f"gorsel.renkler.{ad}")
    c = _renk_coz(v) if v is not None else None
    if c is None and v is not None:
        uyar(f"gorsel.renkler.{ad} geçersiz ({v!r}); varsayılan renk kullanılıyor")
    return c or (tuple(varsayilan) if varsayilan is not None else (0, 0, 0))


def _yol_coz(p, *tabanlar):
    p = os.path.expanduser(str(p))
    if os.path.isabs(p):
        return os.path.normpath(p) if os.path.isfile(p) else None
    for t in tabanlar:
        if t:
            y = os.path.join(t, p)
            if os.path.isfile(y):
                return os.path.normpath(y)
    return None


def _kok_ya_da_none():
    try:
        return kok()
    except KokBulunamadi:
        return None


# video/gönderi başına yazı tipi: proje_fontu(<proje klasörü>) ile seçilir (Video ve post_olustur çağırır)
_PROJE_FONT = {"proje": None, "font": {}}
FONT_KLASORU = os.path.join("sirket", "arsiv", "fontlar")


def font_alani(v):
    """"font" alanı -> {tur: yol, varyasyon_<tur>: ad}. Tek dosya (metin) iki tür için de kullanılır."""
    if isinstance(v, str) and v.strip():
        return {"kalin_dar": v.strip(), "kalin_yari_dar": v.strip()}
    if not isinstance(v, dict):
        return {}
    out = {k: str(x).strip() for k, x in v.items() if isinstance(x, str) and x.strip()}
    dar, yari = out.get("kalin_dar"), out.get("kalin_yari_dar")
    if dar and not yari:
        out["kalin_yari_dar"] = dar
        if out.get("varyasyon_kalin_dar"):
            out.setdefault("varyasyon_kalin_yari_dar", out["varyasyon_kalin_dar"])
    elif yari and not dar:
        out["kalin_dar"] = yari
        if out.get("varyasyon_kalin_yari_dar"):
            out.setdefault("varyasyon_kalin_dar", out["varyasyon_kalin_yari_dar"])
    return out


def proje_font_alani(proje):
    """Projenin font seçimi: durum.json > senaryo.json > post.json üst düzey "font" alanı (anahtar bazında)."""
    secim = {}
    for ad in ("post.json", "senaryo.json", "durum.json"):      # sonra okunan öncelikli
        y = os.path.join(proje, ad)
        if not os.path.isfile(y):
            continue
        try:
            veri = _json_oku(y)
        except (OSError, ValueError):
            continue
        if isinstance(veri, dict) and veri.get("font"):
            secim.update(font_alani(veri["font"]))
    return secim


def proje_font_dosyasi(p, proje=None):
    """Projenin "font" alanındaki yol -> dosya (proje köküne, sirket/arsiv/fontlar/'a, proje klasörüne göre) ya da None."""
    kk = _kok_ya_da_none()
    return _yol_coz(p, kk, os.path.join(kk, FONT_KLASORU) if kk else None, proje)


def proje_fontu(proje):
    """Bu süreçte çizilecek video/gönderinin projesini bildirir; font seçimini o projeden alır. None -> sıfırla."""
    _PROJE_FONT["proje"] = os.path.abspath(proje) if proje else None
    _PROJE_FONT["font"] = proje_font_alani(proje) if proje else {}
    return dict(_PROJE_FONT["font"])


def font_cozumle(tur="kalin_dar"):
    """-> (dosya ya da None, varyasyon adı ya da None, kaynak açıklaması).

    Öncelik: proje "font" alanı (durum.json/senaryo.json/post.json) -> ayarlar.json gorsel.font.degisken_yol
    (+ varyasyon_<tur>) -> gorsel.font.<tur> (eklentiye, sonra projeye göre; varsayılan assets/fonts/) -> Pillow yedeği.
    tur eski varyasyon adı da olabilir ("Bold Condensed" -> kalin_dar). Bilinmeyen bir ad değişken fontta
    doğrudan varyasyon adı olarak denenir.
    """
    ad = FONT_TURU.get(tur)
    vary_ad = None if ad else tur
    ad = ad or "kalin_dar"
    kk = _kok_ya_da_none()
    pf = _PROJE_FONT["font"]
    if pf.get(ad):
        y = proje_font_dosyasi(pf[ad], _PROJE_FONT["proje"])
        if y:
            return y, (vary_ad or pf.get(f"varyasyon_{ad}") or None), f"proje ({os.path.basename(_PROJE_FONT['proje'])})"
        uyar(f"projenin font dosyası bulunamadı: {pf[ad]} (proje köküne ya da {FONT_KLASORU}/ altına göre); "
             "ayarlardaki font kullanılıyor")
    f = al("gorsel.font", {}) or {}
    dg = str(f.get("degisken_yol") or "").strip()
    if dg:
        y = _yol_coz(dg, kk, os.path.join(kk, FONT_KLASORU) if kk else None, EKLENTI)
        if y:
            return y, (vary_ad or f.get(f"varyasyon_{ad}") or None), "ayarlar (gorsel.font.degisken_yol)"
        uyar(f"gorsel.font.degisken_yol bulunamadı: {dg}")
    tek = str(f.get(ad) or "").strip()
    if tek:
        y = _yol_coz(tek, EKLENTI, kk, os.path.join(kk, FONT_KLASORU) if kk else None)
        if y:
            kaynak = "eklenti varsayılanı" if os.path.abspath(y).startswith(EKLENTI) else "ayarlar"
            return y, None, f"{kaynak} (gorsel.font.{ad})"
    uyar(f"'{ad}' yazı tipi dosyası yok ({tek or 'ayar boş'}); Pillow'un varsayılan yazı tipi kullanılıyor. "
         "Eklentinin assets/fonts/ klasörünü ya da ayarlar.json -> gorsel.font ayarını kontrol edin.")
    return None, None, "Pillow yedeği (ImageFont.load_default)"


def font_yolu(tur="kalin_dar"):
    """-> (dosya, varyasyon adı ya da None); bulunamazsa (None, None) ve tek seferlik uyarı."""
    y, v, _ = font_cozumle(tur)
    return y, v


def logo_yolu():
    """marka.logo -> dosya yolu (projeye, sonra eklentiye göre); boşsa ya da yoksa None (logo yerine marka adı)."""
    p = str(al("marka.logo", "") or "").strip()
    if not p:
        return None
    y = _yol_coz(p, _kok_ya_da_none(), EKLENTI)
    if not y:
        uyar(f"marka.logo bulunamadı: {p}; logo yerine marka adı yazılacak")
    return y


def marka_adi():
    return str(al("marka.ad", "") or "").strip()
