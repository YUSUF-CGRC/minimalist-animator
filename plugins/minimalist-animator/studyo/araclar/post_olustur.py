"""Gönderi (post) üreticisi: post.json + cizim/hazir/*.png -> cikti/kare-01.png ... + cikti/kontak.png

Kullanım:
    ma post-olustur <proje>              # bütün kareler + kontak sayfası
    ma post-olustur <proje> --kare 3     # yalnızca 3. kare (hızlı deneme; kontak yok)
    ma post-olustur <proje> --cikti <klasor>
    ma kontrol <proje> --post            # post.json şema/içerik kontrolü (üretmeden önce)

<proje>: proje klasörünün yolu ya da adından bir parça (ör. "ay-yuzu"); post.json olan herhangi bir klasör de olur.

post.json şeması (Senarist yazar):
    {"tur": "carousel" | "karikatur", "baslik": "...",
     "kareler": [{"no": 1, "rol": "kanca" | "bilgi" | "panel" | "kapanis",
                  "metin": "≤20 kelime; **kalın** yazılan kelimeler vurgulanır",
                  "vurgu": ["kelime", ...],          # isteğe bağlı, ** yerine
                  "alt_metin": "küçük not / kaynak",  # isteğe bağlı
                  "konusma": "balon metni" | [{"kim": "<gorsel id>", "metin": "..."}],   # panel
                  "gorsel": "<id>" | ["<id>", "<id>"],  # cizim/hazir/<id>.png, <id>_acik.png, <id>_ana.png, <id>*.png
                  "arka_plan": "<id>",                 # isteğe bağlı, tam kare zemin görseli
                  "cta": "Kaydet, birine gönder",      # kapanış, isteğe bağlı (yoksa ayarlar -> metinler.cta_kapanis)
                  "sahne": "...", "kaynak": "..."}],
     "varliklar": [...], "aciklama": "...",
     "gorsel_klasorleri": ["../başka/klasör"],       # isteğe bağlı: cizim/hazir dışında aranacak klasörler
     "rozet": "bilgi" | "kare" | "yok",              # isteğe bağlı: bilgi rozeti numarası (varsayılan bilgi sırası)
     "sayfa_no": false,                               # isteğe bağlı: true -> bilgi/panel karelerinde "2/7" göstergesi
                                                      # (varsayılan kapalı; Instagram kaydırma noktalarını zaten gösterir)
     "font": "sirket/arsiv/fontlar/X.ttf" | {"kalin_dar": "...", "kalin_yari_dar": "..."}}
                                                      # isteğe bağlı: bu gönderiye özel yazı tipi (durum.json'daki önce gelir)

Düzen (1080x1350, metin güvenli kenarı 80 px):
    kanca   : 2-3 satır büyük başlık + büyük chibi (1 ya da 2 görsel) + kaydırma ipucu (metinler.kaydir)
    bilgi   : numara rozeti + logo/marka adı (+ isteğe bağlı sayfa göstergesi) / gölgeli görsel / açık panelde metin / alt_metin
    kapanis : büyük soru + (isteğe bağlı görsel) + CTA (metinler.cta_kapanis) + logo + slogan (marka.slogan/alt_slogan)
    panel   : karikatür çerçevesi, anlatım kutusu (metin), konuşma balonları, altta "gerçekte" notu (alt_metin)

Çıkış kodu: 0 temiz (uyarılar olabilir), 2 eksik görsel nedeniyle atlanan kare var, 1 post.json hatası.
"""
import argparse
import functools
import glob
import json
import math
import os
import re
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# eklenti içi motor modülleri (kod eklentide, veri proje kökünde: ayar.kok())
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "motor"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ayar  # noqa: E402
import motor as M  # noqa: E402
import kurgu as K  # noqa: E402
from motor import DARK, INK, GOLD, GOLD_D, CREAM, NAVY, RED, Vec, rrect, star_pts, draw_gear, font, premul, over  # noqa: E402
from ayar import buyuk  # noqa: E402

PW, PH = 1080, 1350
KENAR = 80                      # metin güvenli kenarı
KAHVE = K.KAHVE                 # kapanış kartındaki alt slogan rengi (gorsel.renkler.KAHVE)
PANEL = (255, 250, 238)
BASLIK_FONT = "Bold Condensed"
GOVDE_FONT = "Bold SemiCondensed"
ISARET = re.compile(r"\*\*(.+?)\*\*")


# ================================================================== zemin
@functools.lru_cache(None)
def _zemin_taban():
    # video parşömeni (1080x1920) ortasından 4:5 kesit: ışık merkezi karenin ortasına düşer
    bg = K.parsomen()[145:145 + PH].copy()
    for cx, cy, r, ang in ((28, 52, 150, 0.2), (1072, 1318, 210, 0.5), (1046, 22, 86, 0.1)):
        v = Vec.around(cx, cy, r + 8)
        draw_gear(v, cx, cy, r, max(8, round(r / 12)), ang, GOLD_D, th=5)
        v.to(bg, 0.15)
    rng = np.random.default_rng(7)
    for _ in range(18):
        x, y, r = rng.uniform(0, PW), rng.uniform(0, PH), rng.uniform(2.5, 5)
        v = Vec.around(x, y, r + 2)
        v.circle((x, y), r, (255, 246, 214))
        v.to(bg, rng.uniform(0.3, 0.6))
    return bg


def zemin():
    return _zemin_taban().copy()


def kapla(im, w, h, fazla=1.0):
    """Görseli w x h kutuyu dolduracak şekilde büyütür/küçültür ve ortadan kırpar (float32 RGB)."""
    hh, ww = im.shape[:2]
    f = max(w / ww, h / hh) * fazla
    im = cv2.resize(im, (int(ww * f) + 1, int(hh * f) + 1), interpolation=cv2.INTER_AREA if f < 1 else cv2.INTER_CUBIC)
    y0, x0 = (im.shape[0] - h) // 2, (im.shape[1] - w) // 2
    return np.ascontiguousarray(im[y0:y0 + h, x0:x0 + w], np.float32)


def zemin_gorsel(yol):
    # kenarlardan %2 fazla doldurur (köşe filigranı ve kenar artıkları)
    return kapla(np.array(Image.open(yol).convert("RGB")).astype(np.float32), PW, PH, 1.04)


# ================================================================== yardımcılar
def bindir(fr, rgba, x, y, alpha=1.0):
    """PIL RGBA ya da düz RGBA uint8 dizisini çerçeveye bindirir (sol-üst köşe x, y)."""
    a = np.array(rgba) if isinstance(rgba, Image.Image) else rgba
    over(fr, premul(a), int(round(x)), int(round(y)), alpha)


def yumusak_elips(fr, cx, cy, rx, ry, renk, alpha, bulanik):
    pad = int(bulanik * 3) + 4
    w, h = int(2 * rx + 2 * pad), int(2 * ry + 2 * pad)
    m = np.zeros((h, w), np.float32)
    cv2.ellipse(m, (w // 2, h // 2), (int(rx), int(ry)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
    m = cv2.GaussianBlur(m, (0, 0), max(1.0, bulanik))
    src = np.dstack([np.array(renk, np.float32)[None, None, :] * m[..., None], m])
    over(fr, src, int(cx - w / 2), int(cy - h / 2), alpha)


def yildizlar(fr, kutu, n, tohum, boy=22):
    x0, y0, x1, y1 = kutu
    rng = np.random.default_rng(tohum)
    for k in range(n):
        # yalnızca görselin üstüne ve iki yanına (görselin üstüne binmesin)
        kenar = k % 3
        if kenar == 0:
            x, y = rng.uniform(x0 + 60, x1 - 60), y0 - rng.uniform(-6, 30)
        else:
            x = x0 - rng.uniform(4, 36) if kenar == 1 else x1 + rng.uniform(4, 36)
            y = rng.uniform(y0 + 40, y0 + (y1 - y0) * 0.65)
        r = boy * rng.uniform(0.6, 1.1)
        v = Vec.around(x, y, r + 4)
        v.poly(star_pts(x, y, r, 0, 4, 0.3), (255, 236, 160), GOLD_D, 2)
        v.to(fr, 0.85)


@functools.lru_cache(None)
def logo(gen, renk=INK):
    if not K.LOGO:
        return K.marka_yazisi(gen, renk)
    lg = np.array(Image.open(K.LOGO).convert("RGBA"))
    ys, xs = np.nonzero(lg[..., 3] > 10)
    lg = lg[max(0, ys.min() - 4):ys.max() + 5, max(0, xs.min() - 4):xs.max() + 5].astype(np.float32)
    f = gen / lg.shape[1]
    big = cv2.resize(lg, (gen, int(lg.shape[0] * f)), interpolation=cv2.INTER_CUBIC if f > 1 else cv2.INTER_AREA)
    if f > 1:
        blur = cv2.GaussianBlur(big, (0, 0), 1.2)
        big = np.clip(big * 1.6 - blur * 0.6, 0, 255)
    big[..., :3] = np.array(renk, np.float32)
    return np.clip(big, 0, 255).astype(np.uint8)


# ================================================================== yazı
@functools.lru_cache(None)
def _glif(ch, var):
    im = Image.new("L", (90, 90), 0)
    ImageDraw.Draw(im).text((10, 70), ch, font=font(60, var), fill=255, anchor="ls")
    return im.tobytes()


def eksik_glifler(metin, var):
    nd = _glif("\ue000", var)
    return sorted({ch for ch in metin if not ch.isspace() and _glif(ch, var) == nd})


def _kelimeler(metin, vurgular, buyuk):
    vset = {K._norm(v) for v in (vurgular or [])}
    out = []
    for i, parca in enumerate(ISARET.split(metin)):
        for k in parca.split():
            out.append((ayar.buyuk(k) if buyuk else k, i % 2 == 1 or (K._norm(k) in vset and K._norm(k) != "")))
    return out


def _sar(kel, f, gen):
    bos = f.getlength(" ")
    satirlar, cur, w = [], [], 0.0
    for d, v in kel:
        lw = f.getlength(d)
        if cur and w + bos + lw > gen:
            satirlar.append(cur)
            cur, w = [], 0.0
        w += (bos if cur else 0) + lw
        cur.append((d, v))
    if cur:
        satirlar.append(cur)
    return satirlar


def yerlestir(metin, gen, yuk, boy_max, boy_min, var=BASLIK_FONT, buyuk=True, satir_k=1.06, max_satir=None,
              vurgular=None, kontur=0.0, dengele=True, ad="", uyarilar=None):
    """Metni kutuya sığan en büyük boyda satırlara böler. -> dict(f, boy, lh, satirlar, h, tasma)"""
    kel = _kelimeler(metin, vurgular, buyuk)
    if uyarilar is not None:
        eksik = eksik_glifler(" ".join(d for d, _ in kel), var)
        if eksik:
            uyarilar.append(f"{ad}: yazı tipinde olmayan karakter(ler) {eksik} kutu olarak çıkar; metni değiştirin")
    sonuc = None
    for boy in range(int(boy_max), int(boy_min) - 1, -2):
        f = font(boy, var)
        sw = kontur * boy
        g = gen - 2 * sw
        if max(f.getlength(d) for d, _ in kel) > g:
            continue
        sat = _sar(kel, f, g)
        lh = boy * satir_k
        h = (len(sat) - 1) * lh + 1.17 * boy + 2 * sw
        if h <= yuk and (max_satir is None or len(sat) <= max_satir):
            sonuc = dict(f=f, boy=boy, lh=lh, satirlar=sat, h=h, tasma=False, sw=sw)
            break
    if sonuc is None:
        boy = int(boy_min)
        f = font(boy, var)
        sw = kontur * boy
        sat = _sar(kel, f, gen - 2 * sw)
        lh = boy * satir_k
        sonuc = dict(f=f, boy=boy, lh=lh, satirlar=sat, h=(len(sat) - 1) * lh + 1.17 * boy + 2 * sw, tasma=True, sw=sw)
        if uyarilar is not None:
            uyarilar.append(f"{ad}: metin kutuya sığmadı (en küçük boy {boy}px, {len(sat)} satır) -> kısaltın")
    if dengele and len(sonuc["satirlar"]) > 1 and not sonuc["tasma"]:
        f, n = sonuc["f"], len(sonuc["satirlar"])
        g = gen - 2 * sonuc["sw"]
        lo, hi = max(f.getlength(d) for d, _ in kel), g
        for _ in range(14):
            mid = (lo + hi) / 2
            if len(_sar(kel, f, mid)) <= n:
                hi = mid
            else:
                lo = mid
        sonuc["satirlar"] = _sar(kel, f, hi + 0.5)
    return sonuc


STILLER = {
    # dolgu, vurgu dolgusu, kontur rengi, kontur (boy oranı), gölge, vurgu bandı
    "baslik": (CREAM, GOLD, DARK, 0.075, 0.35, False),
    "govde": (INK, INK, None, 0.0, 0.0, True),
    "kucuk": (KAHVE, INK, None, 0.0, 0.0, False),
    "balon": (INK, RED, None, 0.0, 0.0, False),
    "kutu": (DARK, RED, None, 0.0, 0.0, False),
    "acik": (CREAM, GOLD, None, 0.0, 0.0, False),
}


def yazi_ciz(fr, yer, x0, y0, gen, stil="baslik", hiza="orta"):
    """yerlestir() sonucunu (x0, y0) sol-üst köşeli, gen genişlikli kutuya çizer."""
    dolgu, vdolgu, kontur, _, golge, bant = STILLER[stil]
    f, boy, lh, sw = yer["f"], yer["boy"], yer["lh"], yer["sw"]
    pad = 24 + int(sw)
    Wk, Hk = int(gen + 2 * pad), int(yer["h"] + 2 * pad)
    bos = f.getlength(" ")
    konumlar = []  # (x, taban, metin, vurgu)
    for i, satir in enumerate(yer["satirlar"]):
        taban = pad + sw + boy * 0.92 + i * lh
        tot = sum(f.getlength(d) for d, _ in satir) + bos * (len(satir) - 1)
        x = pad + {"orta": (gen - tot) / 2, "sol": sw, "sag": gen - tot - sw}[hiza]
        for d, v in satir:
            konumlar.append((x, taban, d, v, i))
            x += f.getlength(d) + bos
    im = Image.new("RGBA", (Wk, Hk), (0, 0, 0, 0))
    swi = int(round(sw))
    if golge:
        sh = Image.new("RGBA", (Wk, Hk), (0, 0, 0, 0))
        ds = ImageDraw.Draw(sh)
        c = (30, 14, 6, int(255 * golge))
        for x, t, d, v, _ in konumlar:
            ds.text((x, t + max(5, boy * 0.05)), d, font=f, fill=c, stroke_width=swi, stroke_fill=c, anchor="ls")
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(max(4, boy * 0.045))))
    dr = ImageDraw.Draw(im)
    if bant:
        # ardışık vurgulu kelimeler tek bir fosforlu kalem bandı olur
        gruplar = []
        for x, t, d, v, i in konumlar:
            if not v:
                continue
            x1 = x + f.getlength(d)
            if gruplar and gruplar[-1][3] == i and abs(gruplar[-1][1] + bos - x) < 1:
                gruplar[-1][1] = x1
            else:
                gruplar.append([x, x1, t, i])
        bl = Image.new("RGBA", (Wk, Hk), (0, 0, 0, 0))
        db = ImageDraw.Draw(bl)
        for x, x1, t, _ in gruplar:
            db.rounded_rectangle((x - 8, t - boy * 0.60, x1 + 8, t + boy * 0.13), radius=int(boy * 0.14),
                                 fill=(*GOLD, 150))
        im.alpha_composite(bl)
    if kontur is not None and swi > 0:
        for x, t, d, v, _ in konumlar:
            dr.text((x, t), d, font=f, fill=kontur, stroke_width=swi, stroke_fill=kontur, anchor="ls")
    for x, t, d, v, _ in konumlar:
        dr.text((x, t), d, font=f, fill=vdolgu if v else dolgu, anchor="ls")
    bindir(fr, im, x0 - pad, y0 - pad)


def tek_satir(fr, metin, boy, cx, cy, renk, var=BASLIK_FONT, hiza="orta", aralik=0):
    """Küçük tek satır (sayfa göstergesi, slogan): cy satırın görsel ortası."""
    f = font(boy, var)
    if aralik:
        gen = sum(f.getlength(ch) for ch in metin) + aralik * (len(metin) - 1)
    else:
        gen = f.getlength(metin)
    im = Image.new("RGBA", (int(gen + 20), int(boy * 1.5)), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    taban = boy * 1.1
    if aralik:
        x = 10
        for ch in metin:
            dr.text((x, taban), ch, font=f, fill=renk, anchor="ls")
            x += f.getlength(ch) + aralik
    else:
        dr.text((10, taban), metin, font=f, fill=renk, anchor="ls")
    x0 = {"orta": cx - gen / 2, "sol": cx, "sag": cx - gen}[hiza] - 10
    bindir(fr, im, x0, cy - (taban - boy * 0.36))
    return gen


# ================================================================== görseller
def gorsel_bul(ctx, gid):
    for d in ctx["klasorler"]:
        for ad in (gid, gid + "_acik", gid + "_ana"):
            p = os.path.join(d, ad + ".png")
            if os.path.exists(p):
                return p
        aday = [p for p in sorted(glob.glob(os.path.join(d, gid + "*.png")))
                if "_ham" not in os.path.basename(p) and "_kapali" not in os.path.basename(p)]
        if aday:
            return aday[0]
    return None


@functools.lru_cache(None)
def _kirpilmis(yol):
    im = Image.open(yol).convert("RGBA")
    bb = im.getchannel("A").point(lambda a: 255 if a > 10 else 0).getbbox()
    return im.crop(bb) if bb else im


def gorsel(ctx, yol, gen, yuk, ad=""):
    im = _kirpilmis(yol)
    f = min(gen / im.width, yuk / im.height)
    if f > 1.25:
        ctx["uyarilar"].append(f"{ad}: {os.path.basename(yol)} küçük ({im.width}x{im.height}), {f:.1f}x büyütüldü -> bulanık olabilir")
    yeni = (max(1, round(im.width * f)), max(1, round(im.height * f)))
    return im.convert("RGBa").resize(yeni, Image.LANCZOS).convert("RGBA")


def gorsel_koy(fr, im, cx, alt_y, isik=True, golge=True, isik_renk=(255, 238, 196)):
    """Görseli alt kenarı alt_y, ortası cx olacak şekilde ışık halesi + gölgeyle yerleştirir."""
    w, h = im.size
    x, y = cx - w / 2, alt_y - h
    if isik:
        yumusak_elips(fr, cx, y + h * 0.52, w * 0.52, h * 0.5, isik_renk, 0.75, max(w, h) * 0.08)
    if golge:
        yumusak_elips(fr, cx, alt_y - 6, w * 0.36, max(10, min(36, h * 0.035)), (40, 20, 10), 0.30, 8)
        a = np.array(im.getchannel("A"), np.float32) / 255
        pad = 40
        a = cv2.copyMakeBorder(a, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
        a = cv2.GaussianBlur(a, (0, 0), 12)
        sh = np.dstack([np.array((40, 20, 10), np.float32)[None, None, :] * a[..., None], a])
        over(fr, sh, int(x - pad + 10), int(y - pad + 16), 0.32)
    bindir(fr, im, x, y)
    return (x, y, x + w, alt_y)


def gorsel_listesi(k):
    g = k.get("gorsel")
    if not g:
        return []
    return [g] if isinstance(g, str) else list(g)


# ================================================================== küçük bileşenler
def rozet(fr, cx, cy, sayi, r=46):
    v = Vec.around(cx, cy, r + 8)
    v.circle((cx, cy), r + 4, DARK)
    v.circle((cx, cy), r, NAVY)
    v.circle((cx, cy), r - 9, GOLD, 4)
    v.to(fr)
    yer = yerlestir(str(sayi), 2 * r, 2 * r, int(r * 1.15), 20, dengele=False)
    yazi_ciz(fr, yer, cx - r, cy - yer["h"] / 2 + yer["boy"] * 0.08, 2 * r, "acik")


def hap(fr, x0, cy, x1, h, kenar=GOLD):
    """Lacivert-altın hap (buton) zemini."""
    v = Vec(x0 - 8, cy - h / 2 - 8, x1 - x0 + 16, h + 16)
    v.poly(rrect(x0 - 4, cy - h / 2 - 4, x1 + 4, cy + h / 2 + 4, h / 2 + 4), DARK)
    v.poly(rrect(x0, cy - h / 2, x1, cy + h / 2, h / 2), NAVY)
    v.polyline(rrect(x0 + 7, cy - h / 2 + 7, x1 - 7, cy + h / 2 - 7, h / 2 - 7), kenar, 3, True)
    v.to(fr)


def ok_ciz(fr, cx, cy, boy, renk=GOLD):
    v = Vec.around(cx, cy, boy)
    v.line((cx - boy * 0.55, cy), (cx + boy * 0.4, cy), renk, boy * 0.2)
    v.polyline([(cx + boy * 0.05, cy - boy * 0.42), (cx + boy * 0.5, cy), (cx + boy * 0.05, cy + boy * 0.42)], renk,
               boy * 0.2)
    v.to(fr)


def kaydir_ipucu(fr, sag_x, cy):
    f = font(40, BASLIK_FONT)
    yazi = buyuk(ayar.metin("kaydir", "Kaydır"))
    gen = f.getlength(yazi) + 44 + 34 + 30
    x0 = sag_x - gen
    hap(fr, x0, cy, sag_x, 66)
    tek_satir(fr, yazi, 40, x0 + 30, cy, CREAM, hiza="sol")
    ok_ciz(fr, sag_x - 40, cy, 34)


def ikon_kaydet(v, cx, cy, s):
    pts = [(cx - s * 0.36, cy - s * 0.5), (cx + s * 0.36, cy - s * 0.5), (cx + s * 0.36, cy + s * 0.5),
           (cx, cy + s * 0.22), (cx - s * 0.36, cy + s * 0.5)]
    v.poly(pts, GOLD, DARK, 3)


def ikon_gonder(v, cx, cy, s):
    pts = [(cx - s * 0.5, cy - s * 0.08), (cx + s * 0.5, cy - s * 0.45), (cx + s * 0.12, cy + s * 0.5),
           (cx - s * 0.04, cy + s * 0.1)]
    v.poly(pts, GOLD, DARK, 3)
    v.line((cx - s * 0.04, cy + s * 0.1), (cx + s * 0.5, cy - s * 0.45), DARK, 3)


def varsayilan_cta():
    """metinler.cta_kapanis; boşsa metinler.kaydet + metinler.gonder."""
    cta = ayar.metin("cta_kapanis").strip()
    if cta:
        return cta
    return ", ".join(p for p in (ayar.metin("kaydet", "Kaydet"), ayar.metin("gonder", "Birine gönder")) if p.strip())


def cta_satiri(fr, metin, cy):
    """'Kaydet, birine gönder' -> iki hap: [kaydet ikonu] KAYDET  [uçak] BİRİNE GÖNDER (virgülle ayrılmış en çok 2 parça)"""
    parcalar = [p.strip() for p in metin.split(",") if p.strip()][:2]
    ikonlar = [ikon_kaydet, ikon_gonder]
    f = font(46, BASLIK_FONT)
    genler = [f.getlength(buyuk(p)) + 40 + 52 + 34 for p in parcalar]
    bosluk = 30
    x = PW / 2 - (sum(genler) + bosluk * (len(genler) - 1)) / 2
    for i, (p, g) in enumerate(zip(parcalar, genler)):
        hap(fr, x, cy, x + g, 84)
        v = Vec(x, cy - 50, 120, 100)
        ikonlar[i % 2](v, x + 52, cy, 42)
        v.to(fr)
        tek_satir(fr, buyuk(p), 46, x + 90, cy, CREAM, hiza="sol")
        x += g + bosluk


def sayfa_gostergesi(fr, sira, toplam, cy=122):
    tek_satir(fr, f"{sira}/{toplam}", 38, PW - KENAR, cy, KAHVE, hiza="sag")


def marka_blogu(fr, y_logo, gen_logo=400):
    """Logo (ya da marka adı) + slogan + süs çizgisi + alt slogan; boş slogan satırları çizilmez."""
    lg = logo(gen_logo)
    bindir(fr, lg, PW / 2 - lg.shape[1] / 2, y_logo)
    y = y_logo + lg.shape[0] + 18
    if K.SLOGAN:
        tek_satir(fr, buyuk(K.SLOGAN), 50, PW / 2, y + 22, INK, aralik=6)
    v = Vec(150, y + 48, 780, 32)
    v.line((PW / 2 - 40 - 300, y + 62), (PW / 2 - 40, y + 62), GOLD_D, 3)
    v.line((PW / 2 + 40, y + 62), (PW / 2 + 40 + 300, y + 62), GOLD_D, 3)
    v.poly(star_pts(PW / 2, y + 62, 13, 0, 4, 0.45), GOLD, DARK, 2)
    v.to(fr)
    if K.ALT_SLOGAN:
        tek_satir(fr, buyuk(K.ALT_SLOGAN), 36, PW / 2, y + 104, KAHVE, aralik=4)
    return y + 130


def acik_panel(fr, x0, y0, x1, y1, r=30, dolgu=PANEL):
    yumusak_elips(fr, (x0 + x1) / 2, y1 - 4, (x1 - x0) * 0.46, 18, (40, 20, 10), 0.18, 10)
    v = Vec(x0 - 8, y0 - 8, x1 - x0 + 16, y1 - y0 + 16)
    v.poly(rrect(x0 - 5, y0 - 5, x1 + 5, y1 + 5, r + 5), DARK)
    v.poly(rrect(x0, y0, x1, y1, r), dolgu)
    v.polyline(rrect(x0 + 10, y0 + 10, x1 - 10, y1 - 10, r - 8), GOLD, 3, True)
    v.to(fr)


# ================================================================== kare türleri
def kare_kanca(ctx, k, sira):
    fr = ctx["zemin"](k)
    ad = f"kare {sira} (kanca)"
    gen = PW - 2 * KENAR
    yer = yerlestir(k.get("metin", ""), gen, 420, 150, 80, max_satir=3, vurgular=k.get("vurgu"), kontur=0.075,
                    ad=ad, uyarilar=ctx["uyarilar"])
    if len(yer["satirlar"]) > 3:
        ctx["uyarilar"].append(f"{ad}: başlık {len(yer['satirlar'])} satır (öneri 2-3)")
    y_bas = 92
    alt_metin = k.get("alt_metin")
    alt_y = 1188 if alt_metin else 1196
    ust = y_bas + yer["h"] + 26
    yollar = ctx["yollar"](k, ad)
    if yollar is None:
        return None
    if len(yollar) == 1:
        im = gorsel(ctx, yollar[0], 760, alt_y - ust, ad)
        kutu = gorsel_koy(fr, im, PW / 2, alt_y)
    elif yollar:
        im1 = gorsel(ctx, yollar[0], 470, alt_y - ust, ad)
        im2 = gorsel(ctx, yollar[1], 440, (alt_y - ust) * 0.78, ad)
        k2 = gorsel_koy(fr, im2, 760, alt_y)
        k1 = gorsel_koy(fr, im1, 320, alt_y)
        kutu = (min(k1[0], k2[0]), min(k1[1], k2[1]), max(k1[2], k2[2]), alt_y)
    else:
        kutu = (200, ust, 880, alt_y)
    yildizlar(fr, (kutu[0] - 30, kutu[1], kutu[2] + 30, kutu[3]), 6, sira * 13 + 1, 24)
    yazi_ciz(fr, yer, KENAR, y_bas, gen, "baslik")
    if alt_metin:
        y2 = yerlestir(alt_metin, 560, 104, 48, 30, var=GOVDE_FONT, buyuk=False, max_satir=2, ad=ad + " alt_metin",
                       uyarilar=ctx["uyarilar"])
        yazi_ciz(fr, y2, KENAR, 1266 - y2["h"], 560, "govde", "sol")
    kaydir_ipucu(fr, PW - KENAR, 1234)
    return fr


def kare_bilgi(ctx, k, sira):
    fr = ctx["zemin"](k)
    ad = f"kare {sira} (bilgi)"
    yollar = ctx["yollar"](k, ad)
    if yollar is None:
        return None
    # üst sıra: rozet, logo, sayfa
    if ctx["rozet"] != "yok":
        rozet(fr, KENAR + 44, 122, ctx["bilgi_no"](sira))
    lg = logo(190)
    bindir(fr, lg, PW / 2 - lg.shape[1] / 2, 122 - lg.shape[0] / 2)
    if ctx["sayfa_no"]:
        sayfa_gostergesi(fr, sira, ctx["toplam"])
    # görsel
    g_ust, g_alt = 196, 772
    if len(yollar) == 1:
        im = gorsel(ctx, yollar[0], 860, g_alt - g_ust, ad)
        dikey_bosluk = (g_alt - g_ust) - im.height
        kutu = gorsel_koy(fr, im, PW / 2, g_alt - dikey_bosluk * 0.45)
    elif yollar:
        im1 = gorsel(ctx, yollar[0], 420, g_alt - g_ust, ad)
        im2 = gorsel(ctx, yollar[1], 420, g_alt - g_ust, ad)
        k1 = gorsel_koy(fr, im1, 300, g_alt)
        k2 = gorsel_koy(fr, im2, 780, g_alt)
        kutu = (k1[0], min(k1[1], k2[1]), k2[2], g_alt)
    else:
        kutu = None
    if kutu:
        yildizlar(fr, (max(60, kutu[0] - 20), kutu[1], min(PW - 60, kutu[2] + 20), kutu[3]), 4, sira * 7 + 3, 20)
    # metin paneli
    px0, py0, px1, py1 = 56, 796, PW - 56, 1162
    acik_panel(fr, px0, py0, px1, py1)
    gen = px1 - px0 - 2 * 40
    yer = yerlestir(k.get("metin", ""), gen, py1 - py0 - 2 * 34, 74, 44, var=GOVDE_FONT, buyuk=False, satir_k=1.16,
                    max_satir=5, vurgular=k.get("vurgu"), ad=ad, uyarilar=ctx["uyarilar"])
    yazi_ciz(fr, yer, px0 + 40, (py0 + py1) / 2 - yer["h"] / 2, gen, "govde")
    if k.get("alt_metin"):
        y2 = yerlestir(k["alt_metin"], PW - 2 * KENAR, 88, 34, 24, var=GOVDE_FONT, buyuk=False, max_satir=2,
                       ad=ad + " alt_metin", uyarilar=ctx["uyarilar"])
        yazi_ciz(fr, y2, KENAR, 1180 + (88 - y2["h"]) / 2, PW - 2 * KENAR, "kucuk")
    return fr


def kare_kapanis(ctx, k, sira):
    fr = ctx["zemin"](k)
    ad = f"kare {sira} (kapanis)"
    yollar = ctx["yollar"](k, ad, zorunlu=False) or []
    gen = PW - 2 * KENAR
    if yollar:
        yer = yerlestir(k.get("metin", ""), gen, 330, 116, 70, max_satir=3, vurgular=k.get("vurgu"), kontur=0.075,
                        ad=ad, uyarilar=ctx["uyarilar"])
        yazi_ciz(fr, yer, KENAR, 96, gen, "baslik")
        ust = 96 + yer["h"] + 24
        im = gorsel(ctx, yollar[0], 620, 820 - ust, ad)
        kutu = gorsel_koy(fr, im, PW / 2, 820)
        yildizlar(fr, (kutu[0] - 40, kutu[1], kutu[2] + 40, kutu[3]), 5, sira * 5 + 2, 22)
        cta_y, logo_y = 890, 968
    else:
        yer = yerlestir(k.get("metin", ""), gen, 560, 140, 80, max_satir=4, vurgular=k.get("vurgu"), kontur=0.075,
                        ad=ad, uyarilar=ctx["uyarilar"])
        yazi_ciz(fr, yer, KENAR, 140 + (560 - yer["h"]) / 2, gen, "baslik")
        cta_y, logo_y = 820, 940
    cta_satiri(fr, k.get("cta") or varsayilan_cta(), cta_y)
    son = marka_blogu(fr, logo_y)
    if son > PH - KENAR + 6:
        ctx["uyarilar"].append(f"{ad}: marka bloğu alt güvenli kenarı aşıyor (y={son:.0f})")
    return fr


def _balon(fr, x0, y0, x1, y1, uc):
    v = Vec(0, 0, PW, PH)
    r = min(46, (y1 - y0) / 2)
    bx = min(max(uc[0], x0 + r + 30), x1 - r - 30)
    kuyruk = [(bx - 40, y1 - 4), (bx + 40, y1 - 4), uc]
    beyaz = (255, 253, 246)
    v.poly(rrect(x0 - 5, y0 - 5, x1 + 5, y1 + 5, r + 5), DARK)
    v.poly(kuyruk, beyaz, DARK, 10)
    v.poly(rrect(x0, y0, x1, y1, r), beyaz)
    v.poly([(bx - 33, y1 - 10), (bx + 33, y1 - 10), (uc[0] * 0.15 + bx * 0.85, y1 + 8)], beyaz)
    v.to(fr)


def kare_panel(ctx, k, sira):
    fr = ctx["zemin"](None)
    ad = f"kare {sira} (panel)"
    yollar = ctx["yollar"](k, ad)
    if yollar is None:
        return None
    gen = PW - 2 * KENAR
    # anlatım kutusu (üst)
    y = KENAR
    sayfa = f"{sira}/{ctx['toplam']}" if (ctx["sayfa_no"] and ctx["toplam"] > 1) else ""
    sayfa_yeri = None
    if k.get("metin"):
        sag_pay = 90 if sayfa else 0
        yer = yerlestir(k["metin"], gen - 60 - 2 * sag_pay, 170, 56, 34, max_satir=3, vurgular=k.get("vurgu"), ad=ad,
                        uyarilar=ctx["uyarilar"])
        kh = yer["h"] + 40
        v = Vec(KENAR - 10, y - 10, gen + 20, kh + 20)
        v.poly(rrect(KENAR - 4, y - 4, KENAR + gen + 4, y + kh + 4, 18), DARK)
        v.poly(rrect(KENAR, y, KENAR + gen, y + kh, 14), (255, 232, 160))
        v.to(fr)
        yazi_ciz(fr, yer, KENAR + 30 + sag_pay, y + 20, gen - 60 - 2 * sag_pay, "kutu")
        sayfa_yeri = (KENAR + gen - 24, y + kh / 2)
        y += kh + 26
    # gerçekte ne oldu (alt)
    alt = PH - KENAR
    if k.get("alt_metin"):
        y2 = yerlestir(k["alt_metin"], gen - 40, 110, 36, 24, var=GOVDE_FONT, buyuk=False, max_satir=3,
                       ad=ad + " alt_metin", uyarilar=ctx["uyarilar"])
        acik_panel(fr, KENAR - 20, alt - y2["h"] - 30, PW - KENAR + 20, alt + 6, r=22)
        yazi_ciz(fr, y2, KENAR, alt - y2["h"] - 12, gen - 0, "kucuk")
        alt = alt - y2["h"] - 30 - 26
    # panel çerçevesi
    px0, py0, px1, py1 = 56, int(y), PW - 56, int(alt)
    pw, ph = px1 - px0, py1 - py0
    if k.get("arka_plan"):
        p = gorsel_bul(ctx, k["arka_plan"])
        if p:
            ic = zemin_gorsel(p)
        else:
            ctx["uyarilar"].append(f"{ad}: arka_plan '{k['arka_plan']}' bulunamadı, parşömen kullanıldı")
            ic = K.parsomen_acik()[300:300 + PH].copy()
    else:
        ic = K.parsomen_acik()[300:300 + PH].copy()
    ic = kapla(ic, pw, ph)
    if not k.get("arka_plan"):
        yumusak_elips(ic, pw / 2, ph - 30, pw * 0.48, 60, (226, 196, 140), 0.55, 18)
    # konuşmalar
    konusma = k.get("konusma") or []
    if isinstance(konusma, str):
        konusma = [{"kim": None, "metin": konusma}]
    n = max(1, len(yollar))
    balon_gen = (pw - 60) if len(konusma) <= 1 else (pw - 90) / 2
    balon_gen = min(balon_gen, 640)
    balonlar = []
    for b in konusma:
        yb = yerlestir(b.get("metin", ""), balon_gen - 70, 260, 54, 32, var=GOVDE_FONT, buyuk=False, satir_k=1.12,
                       max_satir=4, vurgular=b.get("vurgu"), ad=ad + " balon", uyarilar=ctx["uyarilar"])
        balonlar.append((b, yb))
    balon_h = max([yb["h"] + 56 for _, yb in balonlar], default=0)
    kar_ust_sinir = 30 + (balon_h + 70 if balonlar else 0)
    kar_yuk = min(ph * (0.74 if n == 1 else 0.66), ph - kar_ust_sinir - 24)
    kutular = []
    for i, yl in enumerate(yollar):
        cx = pw * (i + 0.5) / n
        im = gorsel(ctx, yl, pw / n * 0.92, kar_yuk, ad)
        kutular.append(gorsel_koy(ic, im, cx, ph - 24, isik=False))
    # balonlar konuşanların başının hemen üstüne iner (hepsi aynı hizada)
    if balonlar and kutular:
        bas_ust = min(kutular[min(i, len(kutular) - 1)][1] for i in range(len(balonlar)))
        balon_y = max(30, bas_ust - 64 - balon_h)
    else:
        balon_y = 30
    for j, (b, yb) in enumerate(balonlar):
        hedef = j
        if b.get("kim"):
            ids = gorsel_listesi(k)
            eslesen = [i for i, g in enumerate(ids) if g == b["kim"] or g.startswith(b["kim"])]
            hedef = eslesen[0] if eslesen else j
        hedef = min(hedef, len(kutular) - 1) if kutular else 0
        bw = min(balon_gen, yb["f"].getlength(" ") + max(sum(yb["f"].getlength(d) for d, _ in s) +
                                                        yb["f"].getlength(" ") * (len(s) - 1) for s in yb["satirlar"]) + 70)
        bw = max(bw, 240)
        bh = yb["h"] + 56
        if len(balonlar) == 1:
            bcx = kutular[hedef][0] / 2 + kutular[hedef][2] / 2 if kutular else pw / 2
        else:
            bcx = pw * (0.25 if j % 2 == 0 else 0.75)
        bx0 = min(max(24, bcx - bw / 2), pw - 24 - bw)
        by0 = balon_y + (balon_h - bh if len(balonlar) <= 2 else (j // 2) * (bh + 20))  # alt kenarlar aynı hizada
        if kutular:
            kx0, ky0, kx1, _ = kutular[hedef]
            uc = ((kx0 + kx1) / 2 + (kx1 - kx0) * 0.12 * (1 if bx0 + bw / 2 < (kx0 + kx1) / 2 else -1),
                  max(by0 + bh + 34, ky0 + 6))
        else:
            uc = (bx0 + bw / 2, by0 + bh + 50)
        _balon(ic, bx0, by0, bx0 + bw, by0 + bh, uc)
        yazi_ciz(ic, yb, bx0 + 35, by0 + 28, bw - 70, "balon")
    # paneli yuvarlak köşeli maskeyle yerleştir
    mask = np.zeros((ph, pw), np.float32)
    cv2.fillPoly(mask, [np.int32(np.array(rrect(0, 0, pw - 1, ph - 1, 26)) * 16)], 1.0, cv2.LINE_AA, 4)
    over(fr, np.dstack([ic * mask[..., None], mask]), px0, py0)
    v = Vec(px0 - 10, py0 - 10, pw + 20, ph + 20)
    v.polyline(rrect(px0, py0, px1, py1, 26), DARK, 9, True)
    v.to(fr)
    if sayfa:
        sx, sy = sayfa_yeri or (px1 - 28, py0 + 36)
        tek_satir(fr, sayfa, 34, sx, sy, INK if sayfa_yeri else KAHVE, hiza="sag")
    return fr


TURLER = {"kanca": kare_kanca, "bilgi": kare_bilgi, "kapanis": kare_kapanis, "panel": kare_panel}


# ================================================================== kontak sayfası
def kontak(kareler, baslik, yol):
    tw, th, ara, sutun = 340, 425, 16, 3
    satir = math.ceil(len(kareler) / sutun)
    ust = 70
    W_ = sutun * tw + (sutun + 1) * ara
    H_ = ust + satir * (th + 46) + ara
    sayfa = Image.new("RGB", (W_, H_), (60, 40, 30))
    dr = ImageDraw.Draw(sayfa)
    dr.text((ara, 46), baslik, font=font(36, BASLIK_FONT), fill=CREAM, anchor="ls")
    for i, (etiket, im) in enumerate(kareler):
        x = ara + (i % sutun) * (tw + ara)
        y = ust + (i // sutun) * (th + 46)
        if im is None:
            dr.rectangle((x, y, x + tw, y + th), fill=(120, 40, 36))
            dr.text((x + tw / 2, y + th / 2), "EKSİK", font=font(48, BASLIK_FONT), fill=CREAM, anchor="mm")
        else:
            sayfa.paste(im.convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
        dr.text((x, y + th + 32), etiket, font=font(26, GOVDE_FONT), fill=CREAM, anchor="ls")
    sayfa.save(yol)


# ================================================================== ana akış
def proje_bul(p):
    if os.path.isdir(p) and os.path.exists(os.path.join(p, "post.json")):
        return os.path.abspath(p)
    from proje import bul
    return bul(p)


def _goster(yol):
    try:
        r = os.path.relpath(yol, ayar.kok())
    except (ayar.KokBulunamadi, ValueError):
        return yol
    return yol if r.startswith("..") else r


def kelime_sayisi(metin):
    return len(ISARET.sub(r"\1", metin or "").split())


def calistir(proje, sadece=None, cikti=None):
    yol = os.path.join(proje, "post.json")
    if not os.path.exists(yol):
        print(f"HATA: {yol} yok")
        return 1
    try:
        with open(yol, encoding="utf-8") as f:
            post = json.load(f)
    except json.JSONDecodeError as e:
        print(f"HATA: post.json okunamadı: {e}")
        return 1
    kareler = post.get("kareler") or []
    if not kareler:
        print("HATA: post.json'da kare yok")
        return 1
    tur = post.get("tur", "carousel")
    uyarilar, eksikler = [], []
    K.yazi_tipi_sec(proje)              # gönderi başına font: durum.json/post.json "font" alanı
    _glif.cache_clear()
    logo.cache_clear()
    klasorler = [os.path.join(proje, "cizim", "hazir")] + [os.path.normpath(os.path.join(proje, d))
                                                          for d in post.get("gorsel_klasorleri", [])]
    cikti = cikti or os.path.join(proje, "cikti")
    os.makedirs(cikti, exist_ok=True)

    def yollar(k, ad, zorunlu=True):
        out = []
        for gid in gorsel_listesi(k):
            p = gorsel_bul(ctx, gid)
            if p is None:
                eksikler.append(f"{ad}: '{gid}' görseli cizim/hazir/'de yok")
                return None if zorunlu else []
            out.append(p)
        return out

    def zemin_sec(k):
        if k and k.get("arka_plan"):
            p = gorsel_bul(ctx, k["arka_plan"])
            if p:
                return zemin_gorsel(p)
            uyarilar.append(f"arka_plan '{k['arka_plan']}' bulunamadı, parşömen kullanıldı")
        return zemin()

    # rozet: "bilgi" (varsayılan) = bilgi kareleri 1, 2, 3...; "kare" = kare sırası; "yok" = rozet çizilmez
    rozet_turu = post.get("rozet", "bilgi")
    bilgi_sira = [i + 1 for i, k in enumerate(kareler) if k.get("rol") == "bilgi"]
    ctx = dict(klasorler=klasorler, uyarilar=uyarilar, toplam=len(kareler), yollar=yollar, zemin=zemin_sec,
               rozet=rozet_turu, sayfa_no=bool(post.get("sayfa_no", False)),
               bilgi_no=lambda s: bilgi_sira.index(s) + 1 if (rozet_turu == "bilgi" and s in bilgi_sira) else s)

    # içerik kontrolleri
    roller = [k.get("rol") for k in kareler]
    if tur == "carousel":
        if not 5 <= len(kareler) <= 7:
            uyarilar.append(f"carousel {len(kareler)} kare (öneri 5-7)")
        if roller[0] != "kanca":
            uyarilar.append("1. kare 'kanca' değil")
        if roller[-1] != "kapanis":
            uyarilar.append("son kare 'kapanis' değil")
    elif tur == "karikatur" and not 1 <= len(kareler) <= 4:
        uyarilar.append(f"karikatür {len(kareler)} panel (öneri 1-4)")
    for i, k in enumerate(kareler, 1):
        n = kelime_sayisi(k.get("metin"))
        if n > 20:
            uyarilar.append(f"kare {i}: metin {n} kelime (sınır 20)")
        if k.get("rol") not in TURLER:
            uyarilar.append(f"kare {i}: bilinmeyen rol '{k.get('rol')}' -> 'bilgi' gibi çizildi")
        if k.get("rol") == "bilgi" and not k.get("kaynak"):
            uyarilar.append(f"kare {i}: bilgi karesinde 'kaynak' alanı boş")
        if k.get("no") not in (None, i):
            uyarilar.append(f"kare {i}: 'no' alanı {k.get('no')} (sıra {i})")

    uretilen = []
    for i, k in enumerate(kareler, 1):
        rol = k.get("rol") if k.get("rol") in TURLER else "bilgi"
        etiket = f"{i:02d} {rol}"
        if sadece and i != sadece:
            continue
        fr = TURLER[rol](ctx, k, i)
        if fr is None:
            uretilen.append((etiket, None))
            continue
        im = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8), "RGB")
        hedef = os.path.join(cikti, f"kare-{i:02d}.png")
        im.save(hedef, optimize=True)
        uretilen.append((etiket, im))
        print(f"  {_goster(hedef)}")
    if not sadece:
        kontak_yol = os.path.join(cikti, "kontak.png")
        kontak(uretilen, f"{post.get('baslik', os.path.basename(proje))}  ·  {tur}  ·  {len(kareler)} kare", kontak_yol)
        print(f"  {_goster(kontak_yol)}")
        for f_ in sorted(glob.glob(os.path.join(cikti, "kare-*.png"))):
            m = re.match(r"kare-(\d+)\.png", os.path.basename(f_))
            if m and int(m.group(1)) > len(kareler):
                uyarilar.append(f"eski çıktı duruyor: {os.path.basename(f_)} (bu çalıştırmada üretilmedi)")
    for e in eksikler:
        print(f"EKSİK: {e} -> kare atlandı")
    for u in uyarilar:
        print(f"UYARI: {u}")
    if not eksikler and not uyarilar:
        print("temiz")
    return 2 if eksikler else 0


def main():
    ap = argparse.ArgumentParser(description="post.json -> 1080x1350 PNG kareler + kontak sayfası")
    ap.add_argument("proje")
    ap.add_argument("--kare", type=int, help="yalnızca bu kareyi üret (1'den başlar)")
    ap.add_argument("--cikti", help="çıktı klasörü (varsayılan <proje>/cikti)")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    sys.exit(calistir(proje_bul(a.proje), a.kare, a.cikti))


if __name__ == "__main__":
    main()
