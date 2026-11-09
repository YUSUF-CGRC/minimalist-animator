"""Kurgu motoru: senaryo + ses parçaları + dekupe görsellerden 1080x1920 Reels videosu.

Kullanım rehberi: studyo/motor/KURGU-REHBERI.md (eklenti klasöründe)
Tipik render.py:

    v = Video(PROJE)
    v.ses_hatti()                 # ses/zamanlama.json'daki parçaları sırayla yerleştirir
    v.otomatik_kurgu()            # senaryo.json -> "ekranda" olaylarını uygular
    ... ince ayar (v.karakterler["kasif"].zipla(v.satir(3).kelime("Ay")) gibi)
    v.calistir()                  # komut satırı: (yok) tam video | --kareler otomatik | --kapak 3.2 | --ses
"""
import functools
import json
import math
import os
import subprocess
import sys
import unicodedata
import zlib

import cv2
import numpy as np
from PIL import Image

import ayar
import motor as M
import sentez as S
import ses_araclari as A
from motor import (W, H, DARK, INK, GOLD, GOLD_D, CREAM, NAVY, RED, prog, lerp, e_out, e_in, e_io, back, bump, spring,
                   shade, premul, over, blit, Vec, rrect, star_pts, draw_gear, text_spr, font, sparkles,
                   twinkles, shadow_ellipse)
from ayar import buyuk

FPS = 30
SR = A.SR
LOGO = ayar.logo_yolu()          # ayarlar.json -> marka.logo; None ise logo yerine marka adı yazılır
SLOGAN = str(ayar.al("marka.slogan", "") or "").strip()          # boşsa kapanışta slogan satırı çizilmez
ALT_SLOGAN = str(ayar.al("marka.alt_slogan", "") or "").strip()
KAHVE = ayar.renk("KAHVE", (130, 86, 44))

ZEMIN_Y = 1400          # karakterlerin ayak hizası
ALTYAZI_Y = 1545
YER = {"sol": 270, "orta": 540, "sag": 810}
NESNE_YER = {"sol": (270, ZEMIN_Y), "orta": (540, ZEMIN_Y), "sag": (810, ZEMIN_Y),
             "sol-ust": (290, 800), "sag-ust": (790, 800), "orta-ust": (540, 820)}


def _norm(s):
    s = ayar.kucuk(s)
    s = unicodedata.normalize("NFC", s)
    return "".join(ch for ch in s if ch.isalnum())


def _hece(kelime):
    rak = sum(ch.isdigit() for ch in kelime)
    return max(2, int(rak * 1.5)) if rak else A.hece_sayisi(kelime)


# ================================================================== arka planlar
def _parsomen(c0, c1, desen_a, tohum=3):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - 540) / 900) ** 2 + ((yy - 820) / 1250) ** 2)
    u = np.clip(d, 0, 1)[..., None] ** 1.6
    bg = np.array(c0, np.float32) * (1 - u) + np.array(c1, np.float32) * u
    bg += cv2.GaussianBlur(np.random.default_rng(tohum).standard_normal((H, W)).astype(np.float32), (0, 0), 1.3)[
              ..., None] * 3.2
    pat = np.zeros((H, W), np.uint8)
    step = 190
    for gy in range(-1, H // step + 2):
        for gx in range(-1, W // step + 2):
            cx, cy = gx * step + (step // 2 if gy % 2 else 0), gy * step + 40
            for rot in (0, 45):
                pts = [(cx + 52 * math.cos(math.radians(rot + 45 + 90 * k)),
                        cy + 52 * math.sin(math.radians(rot + 45 + 90 * k))) for k in range(4)]
                cv2.polylines(pat, [np.int32(np.round(np.array(pts) * 16))], True, 255, 2, cv2.LINE_AA, 4)
            cv2.circle(pat, (cx * 16, cy * 16), 16 * 16, 255, 2, cv2.LINE_AA, 4)
    pf = (pat.astype(np.float32) / 255 * desen_a)[..., None]
    bg = bg * (1 - pf) + np.array([168, 116, 58], np.float32) * pf
    bg *= (1 - 0.2 * np.clip(d - 0.5, 0, 1))[..., None]
    return bg.astype(np.float32)


@functools.lru_cache(None)
def parsomen():
    return _parsomen((249, 239, 215), (221, 191, 143), 0.10)


@functools.lru_cache(None)
def parsomen_acik():
    return _parsomen((251, 246, 233), (234, 216, 184), 0.07, 5)


def ortam(fr, t):
    """Parşömen zeminde dönen soluk çarklar ve yükselen toz zerreleri."""
    for (cx, cy, r, sp) in ((40, 150, 160, 0.18), (1060, 1840, 210, -0.13), (1010, 70, 90, -0.3)):
        v = Vec.around(cx, cy, r + 8)
        draw_gear(v, cx, cy, r, max(8, round(r / 12)), t * sp, GOLD_D, th=5)
        v.to(fr, 0.16)
    rng = np.random.default_rng(11)
    for k in range(22):
        x0, y0, sp, sz = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(12, 30), rng.uniform(2.5, 5.5)
        x = (x0 + 14 * math.sin(t * 0.6 + k)) % W
        y = (y0 - sp * t) % H
        tw = 0.5 + 0.5 * math.sin(t * 2.3 + k * 1.7)
        v = Vec.around(x, y, sz + 2)
        v.circle((x, y), sz, (255, 246, 214))
        v.to(fr, 0.25 + 0.35 * tw)


class ArkaPlan:
    def __init__(self, kaynak, t, gecis, kenburns):
        self.kaynak, self.t, self.gecis, self.kenburns = kaynak, t, gecis, kenburns
        self.img = None
        if kaynak != "parsomen":
            im = np.array(Image.open(kaynak).convert("RGB")).astype(np.float32)
            # 9:16'ya doldur, kenarlardan %3 kırp (köşe filigranı ve kenar artıkları)
            hh, ww = im.shape[:2]
            f = max(W / ww, H / hh) * 1.06
            im = cv2.resize(im, (int(ww * f) + 1, int(hh * f) + 1), interpolation=cv2.INTER_AREA)
            self.img = im

    def ciz(self, t, t_son):
        if self.img is None:
            fr = parsomen().copy()
            ortam(fr, t)
            return fr
        hh, ww = self.img.shape[:2]
        z = 1.0 + (0.045 * prog(t, self.t, max(self.t + 1, t_son)) if self.kenburns else 0)
        cx, cy = ww / 2, hh / 2
        Mx = np.array([[z, 0, W / 2 - z * cx], [0, z, H / 2 - z * cy]], np.float32)
        return cv2.warpAffine(self.img, Mx, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


# ================================================================== satırlar
class Satir:
    def __init__(self, no, konusan, metin, altyazi, vurgu, ses, bas):
        self.no, self.konusan, self.metin, self.altyazi = no, konusan, metin, altyazi
        self.vurgu = vurgu or []
        self.ses = ses
        self.bas = bas
        self.bit = bas + A.sure(ses)
        self.sure = self.bit - self.bas
        self.orta = (self.bas + self.bit) / 2
        self.parcalar = None   # elle altyazı parçaları

    def _kelime_zamanlari(self):
        ks = self.altyazi.split()
        w = [_hece(k) for k in ks]
        tot, acc, out = sum(w), self.bas, []
        for k, h in zip(ks, w):
            d = self.sure * h / tot
            out.append((k, acc, acc + d))
            acc += d
        return out

    def kelime(self, kelime, kacinci=0, son=False):
        """Altyazıdaki kelimenin (yaklaşık) başlangıç zamanı. son=True -> bitiş zamanı."""
        hedef, n = _norm(kelime), 0
        for k, a, b in self._kelime_zamanlari():
            if hedef and hedef in _norm(k):
                if n == kacinci:
                    return b if son else a
                n += 1
        raise KeyError(f"Satır {self.no}: '{kelime}' kelimesi altyazıda yok: {self.altyazi}")

    def __repr__(self):
        return f"<Satir {self.no} {self.konusan} {self.bas:.2f}-{self.bit:.2f} '{self.altyazi[:30]}'>"


# ================================================================== figürler (karakter / nesne)
def _yukle_rgba(yol):
    return np.array(Image.open(yol).convert("RGBA"))


def _sprite_seti(yollar, hedef_boy):
    """Varyantları aynı kutuyla kırpar, hedef boya göre küçültür. -> {ad: premul}, ayak, yükseklik"""
    ana = None
    ham = {}
    for ad, yol in yollar.items():
        im = _yukle_rgba(yol)
        if ana is None:
            ana = im.shape[:2]
        elif im.shape[:2] != ana:
            im = cv2.resize(im, (ana[1], ana[0]), interpolation=cv2.INTER_AREA)
        ham[ad] = im
    birlesik = np.zeros(ana, bool)
    for im in ham.values():
        birlesik |= im[..., 3] > 8
    ys, xs = np.nonzero(birlesik)
    y0, y1 = max(0, ys.min() - 6), min(ana[0], ys.max() + 7)
    x0, x1 = max(0, xs.min() - 6), min(ana[1], xs.max() + 7)
    f = min(1.0, hedef_boy * 1.25 / (y1 - y0))
    out = {}
    for ad, im in ham.items():
        c = im[y0:y1, x0:x1]
        if f < 1:
            c = M.scaled(c, f)
        out[ad] = premul(c)
    a = out[next(iter(out))][..., 3] > 0.3
    rows = np.nonzero(a.any(1))[0]
    alt = rows[-1]
    bant = a[max(0, alt - max(3, int(0.04 * a.shape[0]))):alt + 1]
    cols = np.nonzero(bant.any(0))[0]
    ayak = ((cols.min() + cols.max()) / 2, float(alt))
    return out, ayak, float(rows[-1] - rows[0])


class Figur:
    tur = "nesne"

    def __init__(self, video, id, yollar, boy, z):
        self.v, self.id, self.z = video, id, z
        self.spr, self.ayak, self.spr_boy = _sprite_seti(yollar, boy)
        self.boy0 = boy
        self.olaylar = []          # (t0, t1, tur, hedef, ek)
        self.ziplamalar = []       # (t0, t1, yukseklik)
        self.sallanmalar = []      # (t0, t1, aci, hiz)
        self.buyumeler = []        # (t0, t1, k)
        self.inisler = []          # yere iniş anları (squash)
        self.golge = True
        self.faz = (zlib.crc32(id.encode()) % 100) / 100 * 6.28
        self._hazir = False

    # ----- API
    def yerlestir(self, t, x=None, y=None, boy=None, yon=None):
        self._ekle(t, t, "ani", dict(x=x, y=y, boy=boy, yon=yon, alfa=1.0))
        return self

    def gir(self, t, nasil="pop", x=540, y=None, boy=None, sure=None):
        y = ZEMIN_Y if y is None and self.tur == "karakter" else y
        sure = sure or {"pop": 0.35, "sol-zipla": 0.95, "sag-zipla": 0.95, "alttan": 0.5, "soldan": 0.45,
                        "sagdan": 0.45, "yukaridan": 0.5, "kenardan-bak": 1.6}.get(nasil, 0.4)
        self._ekle(t, t + sure, "gir", dict(x=x, y=y, boy=boy, alfa=1.0), dict(nasil=nasil))
        if nasil in ("sol-zipla", "sag-zipla", "kenardan-bak"):
            n0 = t + (sure * 0.4 if nasil == "kenardan-bak" else 0)
            seg = (t + sure - n0) / 3
            self.inisler += [n0 + seg, n0 + 2 * seg, t + sure]
            for k in range(3):
                self.v.efekt("pop", n0 + (k + 1) * seg - 0.02, 0.18, pitch=0.8 + 0.1 * k)
        else:
            self.inisler.append(t + sure)
            self.v.efekt({"pop": "pop", "alttan": "whoosh", "soldan": "whoosh", "sagdan": "whoosh",
                          "yukaridan": "thump"}.get(nasil, "pop"), t if nasil != "yukaridan" else t + sure, 0.35)
        return self

    def git(self, t, x=None, y=None, boy=None, sure=0.5, zipla=True, yukseklik=110):
        self._ekle(t, t + sure, "git", dict(x=x, y=y, boy=boy), dict(zipla=zipla, yukseklik=yukseklik))
        self.inisler.append(t + sure)
        if zipla:
            self.v.efekt("boing", t, 0.18, pitch=1.15)
        return self

    def cik(self, t, nasil="sag", sure=0.4):
        self._ekle(t, t + sure, "cik", dict(alfa=0.0), dict(nasil=nasil))
        self.v.efekt("whoosh" if nasil in ("sag", "sol") else "pop", t, 0.25)
        return self

    def don(self, t, sure=0.25):
        self._ekle(t, t + sure, "don", {}, {})
        return self

    def zipla(self, t, yukseklik=50, sure=0.32):
        self.ziplamalar.append((t, t + sure, yukseklik))
        self.inisler.append(t + sure)
        return self

    def sallan(self, t0, t1, aci=6, hiz=1.4):
        self.sallanmalar.append((t0, t1, aci, hiz))
        return self

    def buyut(self, t0, t1, k=1.07):
        self.buyumeler.append((t0, t1, k))
        return self

    # ----- iç
    def _ekle(self, t0, t1, tur, hedef, ek=None):
        self.olaylar.append((t0, t1, tur, {k: v for k, v in hedef.items() if v is not None}, ek or {}))
        self._hazir = False

    def _hazirla(self):
        self.olaylar.sort(key=lambda e: e[0])
        cur = dict(x=540.0, y=float(ZEMIN_Y), boy=float(self.boy0), yon=1.0, alfa=0.0)
        self._adim = []
        for t0, t1, tur, hedef, ek in self.olaylar:
            bas = dict(cur)
            son = dict(cur)
            son.update(hedef)
            if tur == "don":
                son["yon"] = -cur["yon"]
            self._adim.append((t0, t1, tur, bas, son, ek))
            cur = son
        self._hazir = True

    def ilk_gorunme(self):
        if not self._hazir:
            self._hazirla()
        for t0, t1, tur, bas, son, ek in self._adim:
            if son.get("alfa", 0) > 0:
                return t0
        return None

    def durum(self, t):
        if not self._hazir:
            self._hazirla()
        s = None
        for adim in self._adim:
            if adim[0] <= t:
                s = adim
            else:
                break
        if s is None:
            return None
        t0, t1, tur, bas, son, ek = s
        d = dict(son, rot=0.0, yoff=0.0, olcek=1.0, sq=0.0)
        if t < t1 and t1 > t0:
            p = prog(t, t0, t1)
            if tur == "git":
                u = e_io(p)
                for k in ("x", "y", "boy"):
                    d[k] = lerp(bas[k], son[k], u)
                if ek.get("zipla"):
                    d["yoff"] = -ek["yukseklik"] * math.sin(math.pi * p)
                    d["rot"] = 5 * math.sin(math.pi * p) * (1 if son["x"] >= bas["x"] else -1)
            elif tur == "gir":
                self._giris(d, ek["nasil"], p, son)
            elif tur == "cik":
                d["alfa"] = 1.0
                n = ek["nasil"]
                u = e_in(p)
                if n == "sag":
                    d["x"] = lerp(bas["x"], W + 450, u)
                elif n == "sol":
                    d["x"] = lerp(bas["x"], -450, u)
                elif n == "alt":
                    d["y"] = lerp(bas["y"], H + bas["boy"], u)
                else:
                    d["olcek"] = 1 - u
                    d["alfa"] = 1 - prog(p, 0.7, 1)
            elif tur == "don":
                d["yon"] = bas["yon"] * math.cos(math.pi * p)
                d["yoff"] = -30 * math.sin(math.pi * p)
        return d

    def _giris(self, d, nasil, p, son):
        if nasil == "pop":
            d["olcek"] = max(0.0, back(p, 2.2))
        elif nasil in ("sol-zipla", "sag-zipla", "kenardan-bak"):
            yon = -1 if nasil != "sag-zipla" else 1
            bas_x = son["x"] + yon * 770
            if nasil == "kenardan-bak":
                if p < 0.4:
                    u = back(prog(p, 0, 0.18), 1.6)
                    d["x"], d["rot"] = lerp(-430, 40, u), -18
                    return
                bas_x, p = 40, prog(p, 0.4, 1)
            i = min(2, int(p * 3))
            hp = p * 3 - i
            xs = [lerp(bas_x, son["x"], k / 3) for k in range(4)]
            d["x"] = lerp(xs[i], xs[i + 1], e_io(hp))
            d["yoff"] = -70 * math.sin(math.pi * hp)
            d["rot"] = (4 if i % 2 else -4) * math.sin(math.pi * hp)
        elif nasil == "alttan":
            d["y"] = lerp(H + son["boy"] * 0.2, son["y"], back(p, 1.3))
        elif nasil in ("soldan", "sagdan"):
            yon = -1 if nasil == "soldan" else 1
            d["x"] = lerp(son["x"] + yon * 900, son["x"], e_out(p))
            d["rot"] = yon * 8 * (1 - e_out(p))
        elif nasil == "yukaridan":
            d["y"] = lerp(-200, son["y"], e_in(p))

    def _ek_hareket(self, d, t):
        for t0, t1, h in self.ziplamalar:
            if t0 <= t <= t1:
                d["yoff"] -= h * math.sin(math.pi * prog(t, t0, t1))
        for t0, t1, aci, hiz in self.sallanmalar:
            k = bump(t, t0, t1, 0.15)
            if k > 0:
                d["rot"] += k * aci * math.sin(2 * math.pi * hiz * (t - t0))
        for t0, t1, kk in self.buyumeler:
            d["olcek"] *= 1 + (kk - 1) * bump(t, t0, t1, 0.18)
        for tl in self.inisler:
            if t >= tl:
                d["sq"] += 0.1 * math.exp(-(t - tl) * 9) * math.cos(2 * math.pi * 3 * (t - tl))

    def _sprite(self, t, d):
        return self.spr[next(iter(self.spr))]

    def ciz(self, fr, t):
        d = self.durum(t)
        if d is None or d["alfa"] <= 0.003:
            return
        self._ek_hareket(d, t)
        if self.tur == "nesne":
            d["yoff"] += 8 * math.sin(2 * math.pi * 0.5 * t + self.faz)
            d["rot"] += 0.8 * math.sin(2 * math.pi * 0.27 * t + self.faz)
        sc = d["boy"] / self.spr_boy * d["olcek"]
        if sc < 0.01:
            return
        if self.golge and d["y"] >= ZEMIN_Y - 40:
            yuk = max(0.0, -d["yoff"])
            g = 1 / (1 + yuk / 120)
            shadow_ellipse(fr, d["x"], d["y"] + 6, 0.27 * d["boy"] * d["olcek"] * g, 0.035 * d["boy"] * g,
                           0.20 * d["alfa"] * g)
        sx = sc * d["yon"] * (1 - 0.5 * d["sq"])
        sy = sc * (1 + d["sq"])
        blit(fr, self._sprite(t, d), self.ayak, (d["x"], d["y"] + d["yoff"]), sx, sy, d["rot"], d["alfa"])

    def bas_noktasi(self, t):
        """Kafanın üst-orta noktası (soru işareti, balon konumlandırmak için)."""
        d = self.durum(t) or dict(x=540, y=ZEMIN_Y, boy=self.boy0)
        return d["x"], d["y"] - d["boy"]


class Nesne(Figur):
    tur = "nesne"


class Karakter(Figur):
    tur = "karakter"

    def __init__(self, video, id, yollar, boy, z):
        super().__init__(video, id, yollar, boy, z)
        self.kirpmalar = []        # (t0, t1) göz kapalı
        self.oto_kirp = "kapali" in self.spr
        self._oto = None

    def goz_kirp(self, t, sure=0.45):
        self.kirpmalar.append((t, t + sure))
        return self

    def _oto_kirpmalar(self):
        if self._oto is None:
            rng = np.random.default_rng(zlib.crc32(self.id.encode()))
            t, out = 1.2 + rng.uniform(0, 1.0), []
            while t < 120:
                out.append(t)
                t += rng.uniform(2.3, 4.3)
            self._oto = out
        return self._oto

    def _sprite(self, t, d):
        kapali = any(a <= t < b for a, b in self.kirpmalar)
        if not kapali and self.oto_kirp:
            kapali = any(b <= t < b + 0.12 for b in self._oto_kirpmalar())
        if kapali and "kapali" in self.spr:
            return self.spr["kapali"]
        if "konusma" in self.spr and self.v.zarf(self.id, t) > 0.3 and int(t * 11) % 2 == 0:
            return self.spr["konusma"]
        return self.spr[next(iter(self.spr))]

    def _ek_hareket(self, d, t):
        super()._ek_hareket(d, t)
        e = self.v.zarf(self.id, t)
        d["sq"] += 0.010 * math.sin(2 * math.pi * 0.55 * t + self.faz) + 0.032 * e
        d["yoff"] -= 7 * e
        d["rot"] += 1.1 * math.sin(2 * math.pi * 0.33 * t + self.faz)


# ================================================================== zamanlı ögeler (yazılar, ikonlar)
class Oge:
    def __init__(self, z, t0, t1, fn):
        self.z, self.t0, self.t1, self.fn = z, t0, t1, fn

    def ciz(self, fr, t):
        if self.t0 - 0.05 <= t <= self.t1 + 0.45:
            self.fn(fr, t)


@functools.lru_cache(None)
def etiket_spr(metin):
    spr, anc = text_spr(buyuk(metin), 104, INK, CREAM, 8, 4, 0.25)
    h, w = spr.shape[:2]
    c = np.zeros((h + 40, w + 220, 4), np.float32)
    over(c, spr, 110, 0)
    v = Vec(0, 0, c.shape[1], c.shape[0])
    y = anc[1] + 70
    for side in (-1, 1):
        x0 = 110 + w / 2 + side * (w / 2 - 20)
        v.line((x0, y), (x0 + side * 70, y), GOLD_D, 5)
        v.poly(star_pts(x0 + side * 92, y, 15, 0, 4, 0.45), GOLD, DARK, 2)
    v.to(c)
    return c, (c.shape[1] / 2, anc[1])


@functools.lru_cache(None)
def plaka_spr(metin):
    yazi, anc_y = text_spr(buyuk(metin), 132, CREAM, DARK, 4, 4, 0)
    w = max(560, min(980, yazi.shape[1] + 120))
    h = 190
    v = Vec(0, 0, w + 120, h + 60)
    ox, oy = 60, 30
    for side in (-1, 1):
        x = ox if side < 0 else ox + w
        tail = [(x, oy + 40), (x + 70 * side, oy + 40), (x + 40 * side, oy + h / 2 + 30), (x + 70 * side, oy + h + 20),
                (x, oy + h + 20)]
        v.poly(tail, shade(NAVY, 0.7), DARK, 6)
    v.poly(rrect(ox + 20, oy, ox + w - 20, oy + h - 20, 18), NAVY, DARK, 7)
    v.poly(rrect(ox + 36, oy + 14, ox + w - 36, oy + h - 34, 12), NAVY, GOLD, 5)
    for x in (ox + 60, ox + w - 60):
        v.poly(star_pts(x, oy + h / 2 - 10, 18, 0, 4, 0.4), GOLD, DARK, 2)
    c = v.f32()
    f = min(1.0, (w - 170) / yazi.shape[1])
    if f < 1:
        yazi = cv2.resize(yazi, (int(yazi.shape[1] * f), int(yazi.shape[0] * f)), interpolation=cv2.INTER_AREA)
        anc_y = (anc_y[0] * f, anc_y[1] * f)
    over(c, yazi, int(ox + w / 2 - anc_y[0]), int(oy + h / 2 - 10 - anc_y[1]))
    return c, ((w + 120) / 2, (h + 60) / 2)


@functools.lru_cache(None)
def pin_spr():
    v = Vec(0, 0, 90, 120)
    pts = [(45 + 32 * math.cos(math.radians(a)), 42 + 32 * math.sin(math.radians(a))) for a in range(150, 391, 10)]
    pts.append((45, 108))
    v.poly(pts, RED, DARK, 5)
    v.circle((45, 42), 12, CREAM)
    v.circle((45, 42), 12, DARK, 3)
    return v.f32()


@functools.lru_cache(None)
def carpi_spr(r):
    v = Vec(0, 0, 2 * r + 20, 2 * r + 20)
    c = r + 10
    for a in (45, -45):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        p0, p1 = (c - r * ca, c - r * sa), (c + r * ca, c + r * sa)
        v.line(p0, p1, DARK, r * 0.42)
    for a in (45, -45):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        v.line((c - (r - 6) * ca, c - (r - 6) * sa), (c + (r - 6) * ca, c + (r - 6) * sa), RED, r * 0.27)
    return v.f32()


@functools.lru_cache(None)
def balon_spr(r):
    w = int(2.3 * r)
    v = Vec(0, 0, w + 40, int(1.9 * r) + 40)
    cx, cy = (w + 40) / 2, (1.9 * r + 40) / 2
    puf = [(cx + r * 0.95 * math.cos(a), cy + r * 0.72 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 9)[:-1]]
    for px, py in puf:
        v.circle((px, py), r * 0.42 + 7, DARK)
    v.ellipse((cx, cy), (r * 0.95 + 7, r * 0.72 + 7), 0, 0, 360, DARK)
    for px, py in puf:
        v.circle((px, py), r * 0.42, (255, 253, 246))
    v.ellipse((cx, cy), (r * 0.95, r * 0.72), 0, 0, 360, (255, 253, 246))
    return v.f32(), (cx, cy)


# ================================================================== altyazı
@functools.lru_cache(256)
def altyazi_spr(metin, vurgular):
    from PIL import ImageDraw, ImageFilter
    f = font(88)
    sw = 9
    kelimeler = metin.split()
    spw = f.getlength(" ")
    satirlar, cur, cw = [], [], 0
    for k in kelimeler:
        lw = f.getlength(buyuk(k))
        if cur and cw + spw + lw > 940:
            satirlar.append(cur)
            cur, cw = [], 0
        cur.append(k)
        cw += (spw if len(cur) > 1 else 0) + lw
    satirlar.append(cur)
    lh = 98
    Wt, Ht = 1080, int(lh * len(satirlar) + 70)
    sh = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))
    im = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))
    yer = []
    for li, ln in enumerate(satirlar):
        tot = sum(f.getlength(buyuk(k)) for k in ln) + spw * (len(ln) - 1)
        x = (Wt - tot) / 2
        y = 30 + lh * (li + 1) - 18
        for k in ln:
            yer.append((x, y, buyuk(k), _norm(k) in vurgular))
            x += f.getlength(buyuk(k)) + spw
    ds, di = ImageDraw.Draw(sh), ImageDraw.Draw(im)
    for x, y, k, hl in yer:
        ds.text((x, y + 7), k, font=f, fill=(25, 10, 4, 150), stroke_width=sw, stroke_fill=(25, 10, 4, 150), anchor="ls")
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    im.alpha_composite(sh)
    for x, y, k, hl in yer:
        di.text((x, y), k, font=f, fill=DARK, stroke_width=sw, stroke_fill=DARK, anchor="ls")
    for x, y, k, hl in yer:
        di.text((x, y), k, font=f, fill=GOLD if hl else CREAM, anchor="ls")
    return premul(np.array(im)), (Wt / 2, Ht / 2)


def _parcala(metin, max_harf=18):
    """Altyazıyı 1-4 kelimelik okunur parçalara böler (noktalama sonrası yeni parça)."""
    out, cur = [], []
    for k in metin.split():
        if cur and (len(" ".join(cur + [k])) > max_harf or len(cur) >= 4):
            out.append(cur)
            cur = []
        cur.append(k)
        if k[-1] in ",.!?…:;" and len(" ".join(cur)) >= 6:
            out.append(cur)
            cur = []
    if cur:
        if out and len(" ".join(cur)) <= 5 and len(" ".join(out[-1] + cur)) <= max_harf + 6:
            out[-1] += cur
        else:
            out.append(cur)
    return [" ".join(p) for p in out]


def yazi_tipi_sec(proje):
    """Projenin font seçimini (durum.json > senaryo.json > post.json "font") etkinleştirir, yazı önbelleklerini atar."""
    secim = ayar.proje_fontu(proje)
    M.font_sifirla()
    for fn in (etiket_spr, plaka_spr, altyazi_spr, marka_yazisi):
        fn.cache_clear()
    return secim


@functools.lru_cache(None)
def marka_yazisi(gen, renk=INK):
    """Logo dosyası yokken marka adı (marka.ad) yazıyla: kırpılmış RGBA uint8, genişliği en çok gen px."""
    from PIL import ImageDraw
    ad = buyuk(ayar.marka_adi())
    if not ad:
        return np.zeros((2, 2, 4), np.uint8)
    boy = max(12, int(gen * 0.22))
    f = font(boy)
    while boy > 12 and f.getlength(ad) > gen:
        boy = int(boy * 0.92)
        f = font(boy)
    im = Image.new("RGBA", (int(f.getlength(ad)) + 40, int(boy * 1.6) + 40), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20, 20 + boy * 1.1), ad, font=f, fill=(*renk, 255), anchor="ls")
    bb = im.getchannel("A").getbbox()
    return np.array(im.crop(bb) if bb else im)


# ================================================================== video
class Video:
    def __init__(self, proje, fps=FPS):
        self.dir = os.path.abspath(proje)
        self.id = os.path.basename(self.dir.rstrip("\\/"))
        self.fps = fps
        yazi_tipi_sec(self.dir)     # video başına font: durum.json/senaryo.json "font" alanı
        self.senaryo = self._json("senaryo.json") or {}
        self.zamanlama = self._json("ses", "zamanlama.json") or {}
        self.satirlar = {}
        self.karakterler = {}
        self.nesneler = {}
        self.figurler = []
        self.ogeler = []
        self.arka_planlar = [ArkaPlan("parsomen", 0.0, "kesme", False)]
        self.efektler = []          # (t, ad, seviye, kw)
        self.muzik_turu, self.muzik_seviye = None, 0.13
        self.kapanis_bas = None
        self.kapanis_karakter = None
        self.altyazi_acik = True
        self.uyarilar = []
        self._zarf = {}
        self.konusma_sonu = 0.0
        self.son_sure = None

    def yol(self, *p):
        return os.path.join(self.dir, *p)

    def _json(self, *p):
        y = self.yol(*p)
        if os.path.exists(y):
            with open(y, encoding="utf-8") as f:
                return json.load(f)
        return None

    # ------------------------------------------------------------ ses hattı
    def ses_hatti(self, bas=0.2, bosluk=0.28, ozel_bosluk=None):
        """ses/zamanlama.json'daki parçaları satır sırasıyla zaman çizelgesine yerleştirir."""
        ozel_bosluk = ozel_bosluk or {}
        sen = {s["no"]: s for s in self.senaryo.get("satirlar", [])}
        parcalar = sorted(self.zamanlama.get("parcalar", []), key=lambda p: p["satir"])
        if not parcalar:
            raise SystemExit("ses/zamanlama.json yok ya da boş: önce Seslendirmen ses_bol.py çalıştırmalı.")
        t = bas
        for p in parcalar:
            x = A.yukle(self.yol("ses", p["dosya"]))
            s = sen.get(p["satir"], {})
            sat = Satir(p["satir"], p.get("konusan") or s.get("konusan"), s.get("metin", ""),
                        s.get("altyazi") or s.get("metin", ""), s.get("vurgu"), x, t)
            self.satirlar[sat.no] = sat
            gap = ozel_bosluk.get(sat.no, s.get("sonra_bosluk", bosluk))
            t = sat.bit + gap
        self.konusma_sonu = max(s.bit for s in self.satirlar.values())
        self._zarf = {}
        return self

    def satir(self, no):
        return self.satirlar[no]

    def kaydir(self, no, saniye):
        """no'lu satırı ve sonrasını saniye kadar kaydırır (sahneye nefes payı için)."""
        for s in self.satirlar.values():
            if s.no >= no:
                s.bas += saniye
                s.bit += saniye
                s.orta += saniye
        self.konusma_sonu = max(s.bit for s in self.satirlar.values())
        self._zarf = {}

    def zarf(self, konusan, t):
        if not self._zarf:
            n = int((self.sure() + 1) * self.fps)
            for kim in {s.konusan for s in self.satirlar.values()}:
                iz = np.zeros(int((self.sure() + 1) * SR))
                for s in self.satirlar.values():
                    if s.konusan == kim:
                        i = int(s.bas * SR)
                        iz[i:i + len(s.ses)] += s.ses[:max(0, len(iz) - i)]
                self._zarf[kim] = A.zarf(iz, self.fps, n)
        z = self._zarf.get(konusan)
        if z is None:
            return 0.0
        return float(z[min(len(z) - 1, max(0, int(t * self.fps)))])

    # ------------------------------------------------------------ varlıklar
    def _hazir_yol(self, *adlar):
        for ad in adlar:
            y = self.yol("cizim", "hazir", ad)
            if os.path.exists(y):
                return y
        return None

    def karakter(self, id, boy=900, z=20):
        if id in self.karakterler:
            return self.karakterler[id]
        ana = self._hazir_yol(f"{id}_acik.png", f"{id}.png")
        if not ana:
            raise FileNotFoundError(f"cizim/hazir/{id}_acik.png (ya da {id}.png) yok — Çizer'e talep aç.")
        yollar = {"acik": ana}
        for ad in ("kapali", "konusma"):
            y = self._hazir_yol(f"{id}_{ad}.png")
            if y:
                yollar[ad] = y
        k = Karakter(self, id, yollar, boy, z)
        self.karakterler[id] = k
        self.figurler.append(k)
        return k

    def nesne(self, id, boy=560, z=10):
        if id in self.nesneler:
            return self.nesneler[id]
        y = self._hazir_yol(f"{id}.png", f"{id}_acik.png")
        if not y:
            raise FileNotFoundError(f"cizim/hazir/{id}.png yok — Çizer'e talep aç.")
        n = Nesne(self, id, {"ana": y}, boy, z)
        self.nesneler[id] = n
        self.figurler.append(n)
        return n

    def arka_plan(self, kaynak="parsomen", t=0.0, gecis="kesme", kenburns=True):
        if kaynak != "parsomen" and not os.path.exists(kaynak):
            y = self._hazir_yol(f"{kaynak}.png", f"{kaynak}.jpg", f"{kaynak}.jpeg")
            if not y:
                raise FileNotFoundError(f"Arka plan bulunamadı: {kaynak}")
            kaynak = y
        self.arka_planlar.append(ArkaPlan(kaynak, t, gecis, kenburns))
        self.arka_planlar.sort(key=lambda a: a.t)
        if gecis in ("iris", "kayma"):
            self.efekt("whoosh", t - (0.2 if gecis == "iris" else 0), 0.3)
        return self

    # ------------------------------------------------------------ yazılar ve ikonlar
    def ozel(self, fn, z=25, t0=0.0, t1=999.0):
        """fn(fr, t) imzalı projeye özel çizim fonksiyonu ekler."""
        self.ogeler.append(Oge(z, t0, t1, fn))

    def etiket(self, metin, t0, t1, y=262):
        def ciz(fr, t):
            spr, anc = etiket_spr(metin)
            s = back(prog(t, t0, t0 + 0.32), 2.0) * min(1.0, 1000 / spr.shape[1])
            out = e_in(prog(t, t1, t1 + 0.3))
            blit(fr, spr, anc, (540, y - 60 * out), s, s, 0, 1 - out)
        self.ogeler.append(Oge(30, t0, t1, ciz))
        self.efekt("whoosh", t0, 0.22)

    def isim_plakasi(self, metin, t0, t1, alt=None, y=270):
        def ciz(fr, t):
            spr, anc = plaka_spr(metin)
            x = lerp(-700, 540, back(prog(t, t0, t0 + 0.4), 1.4)) + lerp(0, 900, e_in(prog(t, t1, t1 + 0.3)))
            blit(fr, spr, anc, (x, y), 1, 1, -3 * spring(t, t0 + 0.35, 1, 2.5, 6))
            if alt:
                k = prog(t, t0 + 0.3, t0 + 0.55) * (1 - prog(t, t1, t1 + 0.2))
                spr2, anc2 = text_spr(buyuk(alt), 60, INK, CREAM, 6, 6, 0.2)
                blit(fr, spr2, anc2, (540, y + 148), 1, 1, 0, k)
            sparkles(fr, t, t0 + 0.3, (540, y), 12, 450, 12, 0.8, 24)
        self.ogeler.append(Oge(30, t0, t1, ciz))
        self.efekt("whoosh", t0, 0.3)
        self.efekt("sparkle", t0 + 0.3, 0.25)

    def yil(self, bas_yil, bit_yil, t0, t1, sayac=None, alt=None, y=255):
        sa, sb = sayac or (t0 + 0.1, t0 + 0.1 + min(1.2, 0.6 * (t1 - t0)))

        def ciz(fr, t):
            out = e_in(prog(t, t1, t1 + 0.3))
            u = e_io(prog(t, sa, sb))
            yr = int(round(lerp(bas_yil, bit_yil, u)))
            spr, anc = text_spr(str(yr), 210, GOLD, DARK, 11)
            pop = back(prog(t, t0, t0 + 0.3)) + 0.12 * math.exp(-max(0, t - sb) * 8) * (t > sb)
            jit = 3 * math.sin(t * 90) * (sa < t < sb)
            blit(fr, spr, anc, (540 + jit, y - 80 * out), pop, pop, 0, 1 - out)
            if alt:
                k = prog(t, sb + 0.05, sb + 0.3)
                spr2, anc2 = text_spr(buyuk(alt), 66, INK, CREAM, 6, 3, 0.2)
                blit(fr, spr2, anc2, (540, y + 130), 1, 1, 0, k * (1 - out))
            sparkles(fr, t, sb, (540, y), 10, 260, 8, 0.7, 22)
        self.ogeler.append(Oge(30, t0, t1, ciz))
        self.efekt("rewind", sa, 0.3, d=max(0.4, sb - sa))
        self.efekt("bell", sb, 0.25, f0=880)

    def konum(self, metin, t0, t1, y=390):
        def ciz(fr, t):
            out = e_in(prog(t, t1, t1 + 0.3))
            land = t0 + 0.2
            k2 = prog(t, t0, t0 + 0.15)
            spr, anc = text_spr(buyuk(metin), 54, INK, CREAM, 6, 2, 0.2)
            tw = spr.shape[1]
            blit(fr, spr, anc, (565, y), 1, 1, 0, k2 * (1 - out))
            py = lerp(y - 240, y, e_in(prog(t, t0, land))) if t < land else y + 14 * spring(t, land, 1, 3, 9)
            sq = 0.18 * spring(t, land, 1, 3.5, 9) if t >= land else 0
            blit(fr, pin_spr(), (45, 108), (565 - tw / 2 - 18, py + 22), 0.62 * (1 - sq), 0.62 * (1 + sq), 0, 1 - out)
        self.ogeler.append(Oge(30, t0, t1, ciz))
        self.efekt("thump", t0 + 0.2, 0.3, f0=140)

    def isaret(self, isaret, t0, t1, x=890, y=600, boyut=230):
        """'?' ya da '!' gibi zıplayan büyük işaret."""
        def ciz(fr, t):
            s = back(prog(t, t0, t0 + 0.3), 2.4) * (1 - e_in(prog(t, t1, t1 + 0.25)))
            spr, anc = text_spr(isaret, boyut, GOLD, DARK, 12)
            blit(fr, spr, anc, (x, y + 10 * math.sin(6 * t)), s, s, 12 * math.sin(2 * math.pi * 1.4 * (t - t0)))
        self.ogeler.append(Oge(32, t0, t1, ciz))
        self.efekt("boing" if isaret == "?" else "pop", t0, 0.25)

    def soru_isareti(self, t0, t1, x=890, y=600):
        self.isaret("?", t0, t1, x, y)

    def unlem(self, t0, t1, x=890, y=600):
        self.isaret("!", t0, t1, x, y)

    def carpi(self, t0, t1, x=540, y=700, r=70):
        def ciz(fr, t):
            s = back(prog(t, t0, t0 + 0.25), 2.6) * (1 - e_in(prog(t, t1, t1 + 0.2)))
            spr = carpi_spr(r)
            blit(fr, spr, (spr.shape[1] / 2, spr.shape[0] / 2), (x, y), s, s, 8 * spring(t, t0, 1, 3, 7))
        self.ogeler.append(Oge(32, t0, t1, ciz))
        self.efekt("buzzer", t0, 0.22)

    def buyuk_metin(self, metin, t0, t1, x=540, y=330, boyut=120, renk=GOLD):
        def ciz(fr, t):
            s = back(prog(t, t0, t0 + 0.32), 2.0) * (1 - e_in(prog(t, t1, t1 + 0.25)))
            spr, anc = text_spr(buyuk(metin), boyut, renk, DARK, 10)
            s *= min(1.0, 1000 / spr.shape[1])
            blit(fr, spr, anc, (x, y), s, s, -2 * spring(t, t0 + 0.3, 1, 2.5, 6))
        self.ogeler.append(Oge(31, t0, t1, ciz))
        self.efekt("pop", t0, 0.3)

    def dusunce_balonu(self, t0, t1, x, y, icerik=None, r=150, kuyruk=None):
        """icerik: cizim/hazir'deki varlık id'si ya da kısa metin. kuyruk: balon kabarcıklarının gittiği nokta."""
        img = None
        if icerik:
            yol = self._hazir_yol(f"{icerik}.png", f"{icerik}_acik.png")
            if yol:
                rgba = _yukle_rgba(yol)
                a = rgba[..., 3] > 8
                ys, xs = np.nonzero(a)
                rgba = rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
                f = (1.1 * r) / max(rgba.shape[:2])
                img = premul(M.scaled(rgba, f))

        def ciz(fr, t):
            s = back(prog(t, t0, t0 + 0.35), 1.8) * (1 - e_in(prog(t, t1, t1 + 0.25)))
            if s <= 0.01:
                return
            if kuyruk:
                for k, (u, rr) in enumerate(((0.25, 14), (0.5, 21), (0.75, 30))):
                    kk = prog(t, t0 + 0.05 * k, t0 + 0.05 * k + 0.2) * (1 - e_in(prog(t, t1, t1 + 0.25)))
                    px, py = lerp(kuyruk[0], x, u), lerp(kuyruk[1], y + r * 0.6, u)
                    v = Vec.around(px, py, rr + 8)
                    v.circle((px, py), rr + 5, DARK)
                    v.circle((px, py), rr, (255, 253, 246))
                    v.to(fr, kk)
            spr, anc = balon_spr(r)
            blit(fr, spr, anc, (x, y + 6 * math.sin(3 * t)), s, s)
            if img is not None:
                blit(fr, img, (img.shape[1] / 2, img.shape[0] / 2), (x, y + 6 * math.sin(3 * t)), s, s)
            elif icerik:
                spr2, anc2 = text_spr(buyuk(icerik), 56, INK, CREAM, 0, 2, 0)
                blit(fr, spr2, anc2, (x, y), s, s)
        self.ogeler.append(Oge(33, t0, t1, ciz))
        self.efekt("chirp", t0, 0.15)

    def parilti(self, t, x=540, y=880, n=18, yaricap=420):
        self.ogeler.append(Oge(34, t, t + 1.4, lambda fr, tt: sparkles(fr, tt, t, (x, y), n, yaricap, int(t * 100), 1.0, 28)))
        self.efekt("sparkle", t, 0.3)

    def pirilti_alani(self, t0, t1, x=540, y=880, rx=420, ry=380, n=14):
        self.ogeler.append(Oge(5, t0, t1, lambda fr, t: twinkles(fr, t, t0, t1, (x, y), rx, ry, n, int(t0 * 10))))

    # ------------------------------------------------------------ ses efektleri ve müzik
    def efekt(self, ad, t, seviye=0.5, **kw):
        self.efektler.append((t, ad, seviye, kw))

    def muzik(self, tur="merak", seviye=0.13):
        self.muzik_turu, self.muzik_seviye = (None if tur == "yok" else tur), seviye

    # ------------------------------------------------------------ kapanış
    def kapanis(self, t=None, karakter=None):
        self.kapanis_bas = t if t is not None else self.konusma_sonu + 0.35
        self.kapanis_karakter = karakter
        self.efekt("whoosh", self.kapanis_bas - 0.25, 0.35)
        self.efekt("arpeggio", self.kapanis_bas + 0.35, 0.35)
        self.efekt("sparkle", self.kapanis_bas + 0.45, 0.3)

    def sure(self):
        if self.son_sure:
            return self.son_sure
        if self.kapanis_bas is not None:
            return self.kapanis_bas + 2.9
        return self.konusma_sonu + 0.8

    # ------------------------------------------------------------ otomatik kurgu
    def otomatik_kurgu(self, sahneleme=True):
        """senaryo.json -> satirlar[].ekranda olaylarını motor çağrılarına çevirir.

        sahneleme=True: zemine nesne gelince tek karakter kenara çekilip küçülür, zemin boşalınca ortaya döner.
        Uygulanamayan 'ozel' olaylar self.uyarilar'a yazılır (Animatör elle yapmalı).
        """
        sen = self.senaryo
        konusanlar = [k["id"] for k in sen.get("karakterler", [])]
        tek = len(konusanlar) <= 1
        k_boy = 900 if tek else 760
        nesne_yer = {}         # yer -> [nesne id, çıkış zamanı ya da None]
        gorunen = {}
        k_yer = {}             # karakter -> (x, boy)

        def kar(id):
            return self.karakter(id, boy=k_boy)

        def zaman(s, ol, vars="bas"):
            z = ol.get("zaman", vars)
            if isinstance(z, (int, float)):
                return s.bas + z
            if z == "bas":
                return s.bas
            if z == "orta":
                return s.orta
            if z == "son":
                return s.bit
            if isinstance(z, str) and z.startswith("kelime:"):
                try:
                    return s.kelime(z.split(":", 1)[1])
                except KeyError as e:
                    self.uyarilar.append(str(e))
            return s.bas

        def bitis(s, ol, vars=0.25):
            if "kadar" in ol and ol["kadar"] in self.satirlar:
                return self.satirlar[ol["kadar"]].bit + 0.2
            return s.bit + vars

        def zemin_dolu(t):
            return any(NESNE_YER[y][1] >= ZEMIN_Y and (c is None or c > t) for y, (k, c) in nesne_yer.items())

        def kenara(t, nesne_x):
            if not (sahneleme and tek and len(gorunen) == 1):
                return
            kid = next(iter(gorunen))
            kx, kb = k_yer.get(kid, (540, k_boy))
            hedef_x = 230 if nesne_x >= 540 else 850
            if abs(kx - hedef_x) > 5:
                kar(kid).git(t - 0.35, x=hedef_x, boy=k_boy * 0.6, sure=0.45)
                k_yer[kid] = (hedef_x, k_boy * 0.6)

        def merkeze(t):
            if not (sahneleme and tek and len(gorunen) == 1):
                return
            kid = next(iter(gorunen))
            kx, kb = k_yer.get(kid, (540, k_boy))
            if abs(kx - 540) > 5:
                kar(kid).git(t, x=540, boy=k_boy, sure=0.5)
                k_yer[kid] = (540, k_boy)

        sira = sorted(sen.get("satirlar", []), key=lambda s: s["no"])
        for si, ss in enumerate(sira):
            if ss["no"] not in self.satirlar:
                continue
            s = self.satirlar[ss["no"]]
            olaylar = ss.get("ekranda", [])
            # konuşan karakter sahnede değilse otomatik getir
            if s.konusan and s.konusan not in gorunen and not any(
                    o.get("ne") == "karakter-giris" and o.get("kim") == s.konusan for o in olaylar):
                olaylar = [{"ne": "karakter-giris", "kim": s.konusan, "nasil": "pop",
                            "nereye": "orta" if tek else ("sol" if not gorunen else "sag")}] + olaylar
            for ol in olaylar:
                ne = ol.get("ne")
                kim = ol.get("kim") or (s.konusan if str(ne).startswith("karakter") else None)
                t = zaman(s, ol)
                try:
                    if ne == "karakter-giris":
                        x = YER.get(ol.get("nereye", "orta"), 540)
                        tg = max(0.0, t - 0.3) if si else 0.0
                        kar(kim).gir(tg, ol.get("nasil", "pop"), x=x, boy=k_boy)
                        gorunen[kim] = True
                        k_yer[kim] = (x, k_boy)
                    elif ne == "karakter-git":
                        x = YER.get(ol.get("nereye", "orta"), 540)
                        kar(kim).git(t, x=x)
                        k_yer[kim] = (x, k_yer.get(kim, (x, k_boy))[1])
                    elif ne == "karakter-zipla":
                        kar(kim).zipla(t + 0.05)
                    elif ne == "karakter-sallan":
                        kar(kim).sallan(t, bitis(s, ol, 0))
                    elif ne == "karakter-don":
                        kar(kim).don(t)
                    elif ne == "karakter-cik":
                        kar(kim).cik(zaman(s, ol, "son"), ol.get("nasil", "sag"))
                        gorunen.pop(kim, None)
                    elif ne == "karakter-goz-kirp":
                        kar(kim).goz_kirp(zaman(s, ol, "son") - 0.3)
                    elif ne == "nesne":
                        yer = ol.get("nereye", "sag")
                        x, y = NESNE_YER.get(yer, NESNE_YER["sag"])
                        ust = y < ZEMIN_Y
                        eski = nesne_yer.get(yer)
                        if eski and eski[0] != kim and (eski[1] is None or eski[1] > t):
                            self.nesne(eski[0]).cik(t - 0.25, "sag" if x >= 540 else "sol", 0.3)
                        boy = ol.get("boy", 430 if ust else 620)
                        self.nesne(kim, boy=boy).gir(t, ol.get("nasil", "pop"), x=x, y=y, boy=boy)
                        cikis = None
                        if "kadar" in ol:
                            cikis = bitis(s, ol, 0)
                            self.nesne(kim).cik(cikis, "sag" if x >= 540 else "sol")
                        nesne_yer[yer] = [kim, cikis]
                        if not ust:
                            kenara(t, x)
                    elif ne == "nesne-cik":
                        tc = zaman(s, ol, "son")
                        self.nesne(kim).cik(tc, ol.get("nasil", "sag"))
                        for kayit in nesne_yer.values():
                            if kayit[0] == kim:
                                kayit[1] = tc
                    elif ne == "etiket":
                        self.etiket(ol["metin"], t, bitis(s, ol))
                    elif ne == "isim-plakasi":
                        self.isim_plakasi(ol["metin"], t, bitis(s, ol), alt=ol.get("alt"))
                    elif ne == "yil":
                        self.yil(int(ol["bas"]), int(ol["bit"]), t, bitis(s, ol), alt=ol.get("alt"))
                    elif ne == "konum":
                        self.konum(ol["metin"], t + 0.1, bitis(s, ol))
                    elif ne in ("soru-isareti", "unlem"):
                        hx, hy = (kar(kim).bas_noktasi(t) if kim else (540, 600))
                        xx = min(960, hx + 330) if kim else 890
                        self.isaret("?" if ne == "soru-isareti" else "!", t, bitis(s, ol, 0.1), xx, max(330, hy + 90))
                    elif ne == "carpi":
                        x, y = NESNE_YER.get(ol.get("nereye", "orta-ust"), (540, 760))
                        self.carpi(t, bitis(s, ol, 0.2), x, y - 60)
                    elif ne == "dusunce-balonu":
                        hx, hy = kar(kim).bas_noktasi(t)
                        bx = min(820, max(260, hx + 120))
                        self.dusunce_balonu(t, bitis(s, ol), bx, max(330, hy - 170), ol.get("icindeki"),
                                            kuyruk=(hx + 30, hy - 10))
                    elif ne == "parilti":
                        self.parilti(t)
                    elif ne == "buyuk-metin":
                        self.buyuk_metin(ol["metin"], t, bitis(s, ol))
                    elif ne == "arka-plan":
                        self.arka_plan(kim or "parsomen", t, ol.get("gecis", "kesme"))
                    elif ne == "efekt":
                        self.efekt(ol.get("ses", "pop"), t, ol.get("seviye", 0.45))
                    elif ne == "ozel":
                        self.uyarilar.append(f"Satır {s.no}: ÖZEL olay elle yapılmalı: {ol.get('aciklama', ol)}")
                    else:
                        self.uyarilar.append(f"Satır {s.no}: bilinmeyen olay '{ne}'")
                except FileNotFoundError as e:
                    self.uyarilar.append(f"Satır {s.no}: {e}")
            # zemin bu satır bitmeden boşaldıysa karakter ortaya döner
            biten = [(y, c) for y, (k, c) in nesne_yer.items() if c is not None and c <= s.bit + 0.01]
            zemin_biten = [c for y, c in biten if NESNE_YER[y][1] >= ZEMIN_Y]
            if zemin_biten and not zemin_dolu(s.bit + 0.01):
                merkeze(max(zemin_biten) + 0.1)
            for y, c in biten:
                nesne_yer.pop(y)
        kp = sen.get("kapanis", {})
        if self.kapanis_bas is None:
            ana = kp.get("karakter") or (konusanlar[0] if konusanlar else None)
            self.kapanis(karakter=self.karakterler.get(ana))
        if self.muzik_turu is None and sen.get("muzik", "merak") != "yok":
            self.muzik(sen.get("muzik", "merak"))
        for u in self.uyarilar:
            print("UYARI:", u)
        return self

    # ------------------------------------------------------------ çizim
    def _aktif_arka(self, t):
        aktif = self.arka_planlar[0]
        onceki = None
        for a in self.arka_planlar:
            if a.t <= t:
                onceki, aktif = aktif, a
        return aktif, onceki

    def kare(self, t):
        kb = self.kapanis_bas
        if kb is not None and t >= kb:
            fr = parsomen_acik().copy()
            ortam(fr, t)
            self._kapanis_ciz(fr, t)
            self._iris(fr, t, kb)
            return np.clip(fr, 0, 255).astype(np.uint8)
        aktif, onceki = self._aktif_arka(t)
        fr = aktif.ciz(t, self.sure())
        if aktif.gecis == "kayma" and onceki is not None and t < aktif.t + 0.45:
            u = e_io(prog(t, aktif.t, aktif.t + 0.45))
            eski = onceki.ciz(t, self.sure())
            dx = int(W * u)
            fr = np.concatenate([eski[:, dx:], fr[:, :dx]], axis=1) if dx > 0 else eski
        for o in sorted(self.figurler + self.ogeler, key=lambda o: o.z):
            o.ciz(fr, t)
        if self.altyazi_acik:
            self._altyazi_ciz(fr, t)
        for a in self.arka_planlar[1:]:
            if a.gecis == "iris":
                self._iris(fr, t, a.t)
            elif a.gecis == "flas" and a.t - 0.1 <= t <= a.t + 0.3:
                k = bump(t, a.t - 0.1, a.t + 0.3, 0.12)
                fr[:] = fr * (1 - 0.85 * k) + 255 * 0.85 * k
        if kb is not None:
            self._iris(fr, t, kb)
        return np.clip(fr, 0, 255).astype(np.uint8)

    _UZAK = None

    def _iris(self, fr, t, tm):
        if not (tm - 0.3 <= t < tm + 0.3):
            return
        if Video._UZAK is None:
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            Video._UZAK = np.sqrt((xx - 540) ** 2 + (yy - 840) ** 2)
        r = lerp(1300, 0, e_in(prog(t, tm - 0.3, tm))) if t < tm else lerp(0, 1300, e_out(prog(t, tm, tm + 0.3)))
        a = np.clip(Video._UZAK - r, 0, 2.5)[..., None] / 2.5
        fr[:] = fr * (1 - a) + np.array((40, 24, 16), np.float32) * a

    def _altyazi_pencereleri(self):
        if getattr(self, "_ap", None) is not None:
            return self._ap
        parcalar = []
        for s in sorted(self.satirlar.values(), key=lambda s: s.no):
            vurgu = frozenset(_norm(v) for v in s.vurgu)
            ks = s._kelime_zamanlari()
            i = 0
            for p in (s.parcalar or _parcala(s.altyazi)):
                n = len(p.split())
                dilim = ks[i:i + n]
                i += n
                if not dilim:
                    continue
                parcalar.append((p, dilim[0][1], dilim[-1][2], vurgu))
        out = []
        for i, (p, a, b, vg) in enumerate(parcalar):
            nxt = parcalar[i + 1][1] if i + 1 < len(parcalar) else 1e9
            bitisik = nxt - b < 0.12
            son = nxt - 0.04 if bitisik else min(nxt - 0.06, b + 0.3)
            out.append((p, a - 0.04, son, bitisik, vg))
        self._ap = out
        return out

    def _altyazi_ciz(self, fr, t):
        for p, a, b, bitisik, vg in self._altyazi_pencereleri():
            if a <= t < b:
                spr, anc = altyazi_spr(p, vg)
                pp = prog(t, a, a + 0.2)
                s = lerp(0.72, 1.0, back(pp, 2.2))
                al = prog(t, a, a + 0.07) * (1 if bitisik else 1 - prog(t, b - 0.06, b))
                blit(fr, spr, anc, (540, ALTYAZI_Y), s, s, 0, al)

    @functools.lru_cache(None)
    def _logo(self):
        if not LOGO:
            return premul(marka_yazisi(800, INK))
        lg = np.array(Image.open(LOGO).convert("RGBA"))
        ys, xs = np.nonzero(lg[..., 3] > 10)
        lg = lg[max(0, ys.min() - 4):ys.max() + 5, max(0, xs.min() - 4):xs.max() + 5].astype(np.float32)
        f = 800 / lg.shape[1]
        big = cv2.resize(lg, (800, int(lg.shape[0] * f)), interpolation=cv2.INTER_CUBIC)
        blur = cv2.GaussianBlur(big, (0, 0), 1.2)
        big = np.clip(big * 1.6 - blur * 0.6, 0, 255)
        big[..., :3] = np.array(INK, np.float32)
        return premul(big.astype(np.uint8))

    def _kapanis_ciz(self, fr, t):
        kb = self.kapanis_bas + 0.3
        logo_t, slogan_t = kb + 0.05, kb + 0.6
        spr = self._logo()
        k = prog(t, logo_t, logo_t + 0.45)
        s = lerp(0.82, 1.0, back(k, 1.6))
        cy = 800
        blit(fr, spr, (spr.shape[1] / 2, spr.shape[0] / 2), (540, cy), s, s, 0, e_out(prog(t, logo_t, logo_t + 0.3)))
        sparkles(fr, t, logo_t + 0.1, (540, cy), 16, 460, 44, 1.0, 26)
        tk = e_out(prog(t, slogan_t, slogan_t + 0.4))
        if SLOGAN:
            spr2, anc2 = text_spr(buyuk(SLOGAN), 60, INK, CREAM, 0, 7, 0)
            blit(fr, spr2, anc2, (540, 985 + 25 * (1 - tk)), 1, 1, 0, tk)
        v = Vec(140, 1035, 800, 30)
        w2 = 330 * tk
        v.line((540 - 40 - w2, 1050), (540 - 40, 1050), GOLD_D, 3)
        v.line((540 + 40, 1050), (540 + 40 + w2, 1050), GOLD_D, 3)
        v.poly(star_pts(540, 1050, 13, 0, 4, 0.45), GOLD, DARK, 2)
        v.to(fr, tk)
        k3 = e_out(prog(t, slogan_t + 0.25, slogan_t + 0.6))
        if ALT_SLOGAN:
            spr3, anc3 = text_spr(buyuk(ALT_SLOGAN), 42, KAHVE, CREAM, 0, 5, 0)
            blit(fr, spr3, anc3, (540, 1098), 1, 1, 0, k3)
        twinkles(fr, t, kb + 0.3, kb + 3.0, (540, 1350), 330, 200, 10, 9)
        kar = self.kapanis_karakter
        if kar is not None:
            spr_k = kar.spr.get("kapali") if (kb + 1.6 <= t < kb + 2.1 and "kapali" in kar.spr) else kar.spr[next(iter(kar.spr))]
            sc = 400 / kar.spr_boy * back(prog(t, kb + 0.15, kb + 0.5), 1.8)
            yoff = -30 * math.sin(math.pi * prog(t, kb + 0.15, kb + 0.45))
            sq = 0.010 * math.sin(2 * math.pi * 0.55 * t)
            if sc > 0.01:
                shadow_ellipse(fr, 540, 1566, 0.27 * 400, 0.035 * 400, 0.18)
                blit(fr, spr_k, kar.ayak, (540, 1560 + yoff), sc * (1 - 0.5 * sq), sc * (1 + sq),
                     1.1 * math.sin(2 * math.pi * 0.33 * t))

    # ------------------------------------------------------------ ses mikslemesi
    def _efekt_sesi(self, ad, kw):
        fns = {"pop": S.pop, "boing": S.boing, "thump": S.thump, "whoosh": S.whoosh, "tick": S.tick,
               "bell": lambda **k: S.bell(k.pop("f0", 880), **k), "trumpet": S.trumpet, "water": lambda **k: S.water(k.get("d", 1.0)),
               "drip": S.drip, "gears": lambda **k: S.gears(k.get("d", 1.0), 8, 14), "rewind": S.rewind,
               "beeps": S.beeps, "sparkle": S.sparkle, "chirp": S.chirp, "zupp": S.zupp, "power_up": S.power_up,
               "hum": lambda **k: S.hum(k.get("d", 1.0)), "zap": S.zap, "clank": S.clank, "buzzer": S.buzzer,
               "slide_whistle": S.slide_whistle, "cricket": S.cricket, "tweets": S.tweets, "fanfare": S.fanfare,
               "pad_chord": S.pad_chord,
               "arpeggio": lambda **k: S.arpeggio(k.get("freqs", (587.33, 739.99, 880.0, 1174.66)))}
        if ad not in fns:
            self.uyarilar.append(f"Bilinmeyen efekt: {ad}")
            return None
        try:
            return fns[ad](**kw)
        except TypeError:
            return fns[ad]()

    def _muzik_sesi(self, n):
        y = np.zeros(n)
        bitis = (self.kapanis_bas or self.sure()) - 0.05
        if self.muzik_turu in ("merak", "gizem"):
            NOTA = dict(D3=146.83, D4=293.66, Eb4=311.13, Fs4=369.99, G4=392.0, A4=440.0, Bb4=466.16, C5=523.25,
                        D5=587.33)
            A_ = ["A4", "-", "Bb4", "A4", "G4", "-", "Fs4", "G4", "A4", "-", "-", "-", "G4", "Fs4", "Eb4", "D4"]
            B_ = ["D4", "-", "Eb4", "Fs4", "G4", "-", "A4", "Bb4", "A4", "G4", "Fs4", "G4", "A4", "-", "-", "-"]
            e8 = 60 / (104 if self.muzik_turu == "merak" else 80) / 2
            seq = (A_ + B_) * 12
            for k, nm in enumerate(seq):
                t0 = 0.3 + k * e8
                if t0 > bitis:
                    break
                if nm != "-" and (self.muzik_turu == "merak" or k % 4 == 0):
                    span = 1
                    while k + span < len(seq) and seq[k + span] == "-":
                        span += 1
                    S.place_into(y, S.ks(NOTA[nm], span * e8 + 0.5, 0.65) * 0.55, t0)
                if k % 8 == 0:
                    S.place_into(y, S.ks(NOTA["D3"], 1.2, 0.35, 0.997) * 0.6, t0)
                if self.muzik_turu == "merak" and k % 8 in (0, 4):
                    S.place_into(y, S.thump(78, 0.32, 0.25) * (0.9 if k % 8 == 0 else 0.7) * 0.8, t0)
            kad = ["D4", "Fs4", "A4", "D5"]
            for j, nm in enumerate(kad):
                S.place_into(y, S.ks(NOTA[nm], 2.4, 0.6, 0.998) * 0.5, bitis + 0.4 + j * 0.06)
            t = np.arange(n) / SR
            dr = (S.osc(146.83, t) + 0.6 * S.osc(220.0, t)) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * t) ** 2) * 0.05
            y += dr * np.clip((bitis + 0.5 - t) / 0.5, 0, 1)
        elif self.muzik_turu == "neseli":
            notalar = [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5]
            e8 = 60 / 120 / 2
            rng = np.random.default_rng(4)
            k = 0
            while 0.3 + k * e8 < bitis:
                t0 = 0.3 + k * e8
                if k % 2 == 0 or rng.random() < 0.3:
                    S.place_into(y, S.synth_pluck(notalar[[0, 2, 4, 3, 1, 2, 5, 4][k % 8]], 0.25) * 0.5, t0)
                if k % 4 == 0:
                    S.place_into(y, S.synth_pluck([130.81, 174.61, 196.0, 130.81][(k // 8) % 4], 0.5, 4) * 0.7, t0)
                    S.place_into(y, S.thump(70, 0.25, 0.2) * 0.6, t0)
                k += 1
            S.place_into(y, S.arpeggio((523.25, 659.25, 783.99, 1046.5)) * 0.6, bitis + 0.4)
        t = np.arange(n) / SR
        return S.norm(y) * np.clip(t / 0.4, 0, 1) if np.abs(y).max() > 0 else y

    def miks(self):
        n = int(self.sure() * SR) + SR // 2
        ses = np.zeros(n)
        for s in self.satirlar.values():
            S.place_into(ses, A.seviye_esitle(s.ses), s.bas)
        ses = S.norm(ses, 0.82) if np.abs(ses).max() > 0 else ses
        env = A.zarf(ses, self.fps)
        duck = np.interp(np.arange(n) / SR, np.arange(len(env)) / self.fps, np.clip(env, 0, 1))
        sfx = np.zeros(n)
        for t, ad, seviye, kw in self.efektler:
            snd = self._efekt_sesi(ad, dict(kw))
            if snd is not None:
                S.place_into(sfx, S.norm(snd) * seviye, t)
        mus = self._muzik_sesi(n) * self.muzik_seviye * (1 - 0.5 * duck) if self.muzik_turu else np.zeros(n)
        sfx *= (1 - 0.35 * duck)
        sol = ses + mus * 0.9 + sfx
        sag = ses + mus * 1.1 + np.concatenate([np.zeros(12), sfx[:-12]])
        st = np.stack([sol, sag], 1)
        st = np.tanh(st * 1.15) / np.tanh(1.15)
        st = S.norm(st, 0.89)
        os.makedirs(self.yol("animasyon", "build"), exist_ok=True)
        yol = self.yol("animasyon", "build", "mix.wav")
        A.kaydet(yol, st[:int(self.sure() * SR)])
        return yol

    # ------------------------------------------------------------ çıktı
    def otomatik_kare_zamanlari(self):
        ts = [0.1]
        for s in sorted(self.satirlar.values(), key=lambda s: s.no):
            ts.append(round(s.orta, 2))
        for a in self.arka_planlar[1:]:
            ts.append(round(a.t + 0.6, 2))
        if self.kapanis_bas is not None:
            ts.append(round(self.kapanis_bas + 1.8, 2))
        return sorted(set(ts))

    def kareler(self, zamanlar):
        d = self.yol("animasyon", "kareler")
        os.makedirs(d, exist_ok=True)
        for t in zamanlar:
            yol = os.path.join(d, f"t{t:05.2f}.png")
            Image.fromarray(self.kare(t)).save(yol)
            print("kare", yol)

    def render(self, cikti=None):
        cikti = cikti or self.yol("cikti", f"{self.id}.mp4")
        os.makedirs(os.path.dirname(cikti), exist_ok=True)
        mix = self.miks()
        d = self.sure()
        n = int(round(d * self.fps))
        cmd = [A.FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(self.fps),
               "-i", "-", "-i", mix, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
               "-pix_fmt", "yuv420p", "-profile:v", "high", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100",
               "-c:a", "aac", "-b:a", "192k", "-t", f"{d:.3f}", "-movflags", "+faststart", cikti]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for i in range(n):
            p.stdin.write(self.kare(i / self.fps).tobytes())
            if i % 90 == 0:
                print(f"kare {i}/{n}", flush=True)
        p.stdin.close()
        p.wait()
        if p.returncode:
            raise SystemExit(f"ffmpeg hata kodu {p.returncode}")
        print("bitti:", cikti, f"({d:.1f} sn)")
        return cikti

    def calistir(self):
        sys.stdout.reconfigure(encoding="utf-8")
        args = sys.argv[1:]
        if args[:1] == ["--kareler"]:
            z = args[1] if len(args) > 1 else "otomatik"
            self.kareler(self.otomatik_kare_zamanlari() if z == "otomatik" else [float(x) for x in z.split(",")])
        elif args[:1] == ["--kapak"]:
            t = float(args[1])
            os.makedirs(self.yol("cikti"), exist_ok=True)
            Image.fromarray(self.kare(t)).save(self.yol("cikti", "kapak.png"))
            print("kapak:", self.yol("cikti", "kapak.png"))
        elif args[:1] == ["--ses"]:
            print("miks:", self.miks())
        elif args[:1] == ["--bilgi"]:
            for s in sorted(self.satirlar.values(), key=lambda s: s.no):
                print(s)
            print(f"kapanış {self.kapanis_bas}, toplam {self.sure():.2f} sn")
        else:
            self.render()
