"""Demo görselleri: chibi "kaşif" karakteri (açık / kapalı göz / konuşma) + Ay ve Dünya nesneleri.

  python hazirla.py [proje_klasoru]      (varsayılan: bu dosyanın klasörü)
Çıktı: <proje>/cizim/hazir/kasif_acik.png, kasif_kapali.png, kasif_konusma.png, ay.png, dunya.png
Şeffaf arka planlı PNG; motorun beklediği adlandırma (<id>_acik/_kapali/_konusma, nesnede <id>.png).
Yalnızca Pillow kullanır; 2x büyük çizilip küçültülür (yumuşak kenar).
"""
import math
import os
import sys

from PIL import Image, ImageChops, ImageDraw

S = 2                                   # süper örnekleme katsayısı
CIZGI = (44, 20, 20, 255)               # motorun kontur rengiyle aynı
TEN = (255, 221, 188, 255)
YANAK = (255, 163, 150, 255)
SAPKA = (206, 172, 108, 255)
SAPKA_K = (174, 138, 80, 255)
BANT = (176, 72, 52, 255)
SAC = (110, 66, 40, 255)
GOMLEK = (236, 220, 178, 255)
YELEK = (118, 140, 92, 255)
PANTOLON = (150, 116, 72, 255)
BOT = (92, 58, 40, 255)
FULAR = (214, 62, 52, 255)
ALTIN = (238, 178, 64, 255)
GOZ = (44, 24, 20, 255)
BEYAZ = (255, 255, 255, 255)
AGIZ = (150, 48, 48, 255)
DIL = (232, 112, 110, 255)
CAM = (214, 238, 250, 255)
LW = 10                                 # kontur kalınlığı (son boyutta px)


def k(*v):
    """Son boyuttaki koordinatları süper örnekleme ölçeğine çevirir."""
    return [x * S for x in v]


class Tuval:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def elips(self, x0, y0, x1, y1, renk, cizgi=True, lw=LW):
        self.d.ellipse(k(x0, y0, x1, y1), fill=renk, outline=CIZGI if cizgi else None, width=lw * S if cizgi else 0)

    def daire(self, cx, cy, r, renk, cizgi=True, lw=LW):
        self.elips(cx - r, cy - r, cx + r, cy + r, renk, cizgi, lw)

    def kiris(self, x0, y0, x1, y1, a0, a1, renk, cizgi=True, lw=LW):
        self.d.chord(k(x0, y0, x1, y1), a0, a1, fill=renk, outline=CIZGI if cizgi else None, width=lw * S if cizgi else 0)

    def yay(self, x0, y0, x1, y1, a0, a1, lw=LW, renk=CIZGI):
        self.d.arc(k(x0, y0, x1, y1), a0, a1, fill=renk, width=lw * S)

    def kutu(self, x0, y0, x1, y1, r, renk, cizgi=True, lw=LW):
        self.d.rounded_rectangle(k(x0, y0, x1, y1), radius=r * S, fill=renk, outline=CIZGI if cizgi else None,
                                 width=lw * S if cizgi else 0)

    def cokgen(self, pts, renk, cizgi=True, lw=LW):
        self.d.polygon([(x * S, y * S) for x, y in pts], fill=renk, outline=CIZGI if cizgi else None,
                       width=lw * S if cizgi else 0)

    def cizgi(self, pts, lw=LW, renk=CIZGI):
        self.d.line([(x * S, y * S) for x, y in pts], fill=renk, width=lw * S, joint="curve")
        for x, y in (pts[0], pts[-1]):
            r = lw * S / 2
            self.d.ellipse((x * S - r, y * S - r, x * S + r, y * S + r), fill=renk)

    def kaydet(self, yol):
        out = self.im.convert("RGBa").resize((self.w, self.h), Image.LANCZOS).convert("RGBA")
        out.save(yol, optimize=True)
        print("  ", yol)


def elips_bandi(cx, cy, a, b, y0, y1, n=24):
    """Elipsin y0..y1 arasındaki yatay şeridi (çokgen)."""
    sol, sag = [], []
    for i in range(n + 1):
        y = y0 + (y1 - y0) * i / n
        dx = a * math.sqrt(max(0.0, 1 - ((y - cy) / b) ** 2))
        sol.append((cx - dx, y))
        sag.append((cx + dx, y))
    return sol + sag[::-1]


# ------------------------------------------------------------------ karakter
def kasif(goz="acik", agiz="gulumse"):
    t = Tuval(1000, 1400)
    # bacaklar ve botlar
    t.kutu(392, 1150, 474, 1320, 30, PANTOLON)
    t.kutu(526, 1150, 608, 1320, 30, PANTOLON)
    t.kutu(366, 1282, 484, 1366, 34, BOT)
    t.kutu(516, 1282, 634, 1366, 34, BOT)
    # kollar (gövdenin arkasında başlar)
    t.kutu(250, 800, 348, 1062, 46, GOMLEK)
    t.kutu(652, 800, 750, 1062, 46, GOMLEK)
    # gövde: gömlek + yelek + kemer
    t.kutu(330, 752, 670, 1208, 120, GOMLEK)
    t.cokgen([(338, 820), (452, 770), (452, 1100), (336, 1100)], YELEK, lw=8)
    t.cokgen([(662, 820), (548, 770), (548, 1100), (664, 1100)], YELEK, lw=8)
    t.kutu(362, 930, 428, 990, 10, YELEK, lw=7)          # cepler
    t.kutu(572, 930, 638, 990, 10, YELEK, lw=7)
    t.kutu(332, 1092, 668, 1136, 14, BOT, lw=8)
    t.kutu(478, 1088, 522, 1140, 8, ALTIN, lw=7)          # toka
    # eller ve büyüteç
    t.daire(299, 1078, 46, TEN)
    t.cizgi([(712, 1066), (752, 1018)], 22, BOT)
    t.daire(786, 975, 64, CAM, lw=12)
    t.yay(752, 940, 800, 990, 200, 260, 8, BEYAZ)
    t.daire(701, 1078, 46, TEN)
    # fular
    t.cokgen([(392, 742), (608, 742), (500, 862)], FULAR, lw=8)
    t.daire(500, 760, 28, FULAR, lw=8)
    # kulaklar ve baş
    t.daire(206, 505, 52, TEN)
    t.daire(794, 505, 52, TEN)
    t.daire(500, 470, 300, TEN)
    # saç (şapkanın altından görünen perçem)
    t.kiris(214, 236, 786, 500, 180, 360, SAC, lw=8)
    for x in (300, 380, 620, 700):
        t.kiris(x - 52, 300, x + 52, 400, 0, 180, SAC, cizgi=False)
    # yüz
    if goz == "acik":
        for cx in (390, 610):
            t.elips(cx - 52, 452, cx + 52, 584, GOZ, cizgi=False)
            t.daire(cx - 18, 492, 19, BEYAZ, cizgi=False)
            t.daire(cx + 16, 548, 8, BEYAZ, cizgi=False)
    else:
        for cx in (390, 610):
            t.yay(cx - 54, 470, cx + 54, 560, 20, 160, 11)
    t.elips(278, 604, 362, 650, YANAK, cizgi=False)
    t.elips(638, 604, 722, 650, YANAK, cizgi=False)
    if agiz == "acik":
        t.kiris(458, 588, 542, 676, 0, 180, AGIZ, lw=8)
        t.kiris(478, 630, 522, 672, 0, 180, DIL, cizgi=False)
    else:
        t.yay(452, 578, 548, 650, 25, 155, 9)
    # şapka: arka kenar, kubbe, bant, rozet, ön kenar
    t.kiris(146, 246, 854, 330, 180, 360, SAPKA_K)
    t.kiris(235, 100, 765, 474, 180, 360, SAPKA)
    t.cokgen(elips_bandi(500, 287, 265, 187, 250, 287), BANT, lw=7)
    t.daire(500, 268, 15, ALTIN, lw=6)
    t.kiris(146, 246, 854, 330, 0, 180, SAPKA_K)
    t.yay(190, 252, 810, 318, 15, 165, 5, SAPKA)
    return t


# ------------------------------------------------------------------ nesneler
def daire_maskesi(w, h, cx, cy, r):
    m = Image.new("L", (w * S, h * S), 0)
    ImageDraw.Draw(m).ellipse(k(cx - r, cy - r, cx + r, cy + r), fill=255)
    return m


def ay():
    t = Tuval(800, 800)
    t.daire(400, 400, 360, (212, 206, 184, 255), cizgi=False)
    t.daire(386, 384, 334, (241, 237, 221, 255), cizgi=False)
    for cx, cy, r in ((226, 236, 52), (566, 214, 38), (606, 566, 60), (238, 572, 30), (420, 664, 26), (676, 380, 22)):
        t.daire(cx, cy, r, (214, 208, 186, 255), lw=6)
        t.yay(cx - r + 6, cy - r + 6, cx + r - 6, cy + r - 6, 200, 300, 5, (250, 247, 236, 255))
    for cx in (322, 478):
        t.elips(cx - 30, 360, cx + 30, 440, GOZ, cizgi=False)
        t.daire(cx - 10, 380, 11, BEYAZ, cizgi=False)
    t.elips(254, 452, 314, 484, YANAK, cizgi=False)
    t.elips(486, 452, 546, 484, YANAK, cizgi=False)
    t.yay(352, 430, 448, 500, 25, 155, 9)
    t.daire(400, 400, 360, None, lw=12)          # yalnızca kontur (dolgu None: içi silinmez)
    return t


def _leke(cx, cy, r, tohum, n=64):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = r * (1 + 0.22 * math.sin(3 * a + tohum) + 0.12 * math.sin(5 * a + 2 * tohum))
        pts.append((cx + rr * math.cos(a), cy + rr * 0.85 * math.sin(a)))
    return pts


def dunya():
    t = Tuval(800, 800)
    t.daire(400, 400, 360, (64, 146, 214, 255), cizgi=False)
    t.daire(384, 382, 330, (92, 176, 236, 255), cizgi=False)
    kara = Tuval(800, 800)
    for cx, cy, r, s in ((250, 300, 120, 1.0), (520, 250, 90, 2.3), (560, 520, 140, 4.1), (240, 600, 80, 5.2)):
        kara.cokgen(_leke(cx, cy, r, s), (118, 192, 92, 255), lw=7)
    for cx, cy, r in ((300, 150, 34), (600, 640, 30)):
        kara.elips(cx - r * 2.2, cy - r * 0.7, cx + r * 2.2, cy + r * 0.7, (255, 255, 255, 230), cizgi=False)
    maske = daire_maskesi(800, 800, 400, 400, 356)
    kara.im.putalpha(ImageChops.multiply(kara.im.getchannel("A"), maske))
    t.im.alpha_composite(kara.im)
    t.yay(110, 110, 690, 690, 200, 250, 10, (200, 236, 255, 255))
    t.daire(400, 400, 360, None, lw=12)          # yalnızca kontur (dolgu None: içi silinmez)
    return t


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    proje = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    hazir = os.path.join(proje, "cizim", "hazir")
    os.makedirs(hazir, exist_ok=True)
    print("demo görselleri ->", hazir)
    kasif("acik").kaydet(os.path.join(hazir, "kasif_acik.png"))
    kasif("kapali").kaydet(os.path.join(hazir, "kasif_kapali.png"))
    kasif("acik", "acik").kaydet(os.path.join(hazir, "kasif_konusma.png"))
    ay().kaydet(os.path.join(hazir, "ay.png"))
    dunya().kaydet(os.path.join(hazir, "dunya.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
