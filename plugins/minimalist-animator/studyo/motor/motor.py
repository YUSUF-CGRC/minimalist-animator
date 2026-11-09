"""Reels animasyonları için ortak çizim motoru: sprite bindirme, vektör çizim, yazı, dekupe araçları."""
import functools, math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import ayar

W, H = 1080, 1920
FONT = ayar.font_yolu("kalin_dar")[0]   # bilgi amaçlı; font() türe göre ayar.font_yolu'ndan seçer

# marka renkleri: varsayılanlar burada, ayarlar.json -> gorsel.renkler ile ezilebilir
DARK = ayar.renk("DARK", (44, 22, 20)); INK = ayar.renk("INK", (58, 34, 20)); GOLD = ayar.renk("GOLD", (238, 178, 64))
GOLD_D = ayar.renk("GOLD_D", (188, 126, 40)); CREAM = ayar.renk("CREAM", (253, 245, 226)); RED = ayar.renk("RED", (214, 62, 52))
NAVY = ayar.renk("NAVY", (36, 52, 88))
WATER = (84, 170, 230); WATER_L = (196, 234, 252)
STEEL = (180, 198, 216); STEEL_D = (120, 140, 162); WOOD = (156, 98, 56)
WOOD_D = (112, 66, 36); CYAN = (110, 236, 255); SKYGLOW = (255, 214, 120); PURPLE = (176, 110, 255)
OUTLINE = np.array([44, 20, 20], np.float32)


# ------------------------------------------------------------------ zaman eğrileri
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def prog(t, t0, t1):
    return clamp((t - t0) / (t1 - t0))


def lerp(a, b, u):
    return a + (b - a) * u


def e_out(u):
    return 1 - (1 - u) ** 3


def e_in(u):
    return u ** 3


def e_io(u):
    return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2


def back(u, s=1.9):
    u -= 1
    return 1 + (s + 1) * u ** 3 + s * u ** 2


def bump(t, t0, t1, ramp=0.2):
    return e_io(prog(t, t0, t0 + ramp)) * (1 - e_io(prog(t, t1 - ramp, t1)))


def spring(t, t0, amp=1.0, freq=3.2, decay=7.0):
    if t < t0:
        return 0.0
    d = t - t0
    return amp * math.exp(-d * decay) * math.cos(2 * math.pi * freq * d)


def shade(c, k):
    return tuple(int(clamp(v * k, 0, 255)) for v in c)


# ------------------------------------------------------------------ bindirme
def premul(rgba):
    a = rgba[..., 3:4].astype(np.float32) / 255
    return np.dstack([rgba[..., :3].astype(np.float32) * a, a])


def over(dst, src, x, y, alpha=1.0):
    h, w = src.shape[:2]
    Hd, Wd = dst.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(Wd, x + w), min(Hd, y + h)
    if x1 <= x0 or y1 <= y0 or alpha <= 0.002:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    a = s[..., 3:4] * alpha
    d = dst[y0:y1, x0:x1]
    if dst.shape[2] == 3:
        d *= (1 - a)
        d += s[..., :3] * alpha
    else:
        d[..., :3] = d[..., :3] * (1 - a) + s[..., :3] * alpha
        d[..., 3:4] = d[..., 3:4] * (1 - a) + a


def affine(anchor, pos, sx, sy, rot):
    r = math.radians(rot)
    c, s = math.cos(r), math.sin(r)
    A = np.array([[c * sx, s * sy], [-s * sx, c * sy]])
    b = np.asarray(pos, float) - A @ np.asarray(anchor, float)
    return A, b


def xform(p, anchor, pos, sx=1.0, sy=None, rot=0.0):
    A, b = affine(anchor, pos, sx, sx if sy is None else sy, rot)
    return A @ np.asarray(p, float) + b


def rot_pt(p, piv, ang):
    """cv2.getRotationMatrix2D ile aynı yönde döndürür (pozitif = saat yönü tersi)."""
    r = math.radians(ang)
    c, s = math.cos(r), math.sin(r)
    dx, dy = p[0] - piv[0], p[1] - piv[1]
    return (piv[0] + dx * c + dy * s, piv[1] - dx * s + dy * c)


def blit(dst, src, anchor, pos, sx=1.0, sy=None, rot=0.0, alpha=1.0):
    sy = sx if sy is None else sy
    if alpha <= 0.003 or abs(sx) < 2e-3 or abs(sy) < 2e-3:
        return
    ax, ay = anchor
    m = max(abs(sx), abs(sy))
    if m < 0.7:
        f = m / 0.9
        nw, nh = max(1, int(round(src.shape[1] * f))), max(1, int(round(src.shape[0] * f)))
        fx, fy = nw / src.shape[1], nh / src.shape[0]
        src = cv2.resize(src, (nw, nh), interpolation=cv2.INTER_AREA)
        ax, ay, sx, sy = ax * fx, ay * fy, sx / fx, sy / fy
    A, b = affine((ax, ay), pos, sx, sy, rot)
    h, w = src.shape[:2]
    cx = A @ np.array([[0, w, w, 0], [0, 0, h, h]], float) + b[:, None]
    Hd, Wd = dst.shape[:2]
    x0, x1 = max(0, int(math.floor(cx[0].min()))), min(Wd, int(math.ceil(cx[0].max())) + 1)
    y0, y1 = max(0, int(math.floor(cx[1].min()))), min(Hd, int(math.ceil(cx[1].max())) + 1)
    if x1 <= x0 or y1 <= y0:
        return
    M = np.hstack([A, (b - [x0, y0])[:, None]])
    out = cv2.warpAffine(src, M, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                         borderValue=(0, 0, 0, 0))
    over(dst, out, x0, y0, alpha)


def rotate_layer(src, piv, ang):
    if abs(ang) < 0.05:
        return src
    M = cv2.getRotationMatrix2D(piv, ang, 1.0)
    return cv2.warpAffine(src, M, (src.shape[1], src.shape[0]), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))


class Vec:
    """Kenar yumuşatmalı vektör çizim yüzeyi (premultiplied RGBA uint8)."""

    def __init__(self, x0, y0, w, h):
        self.x0, self.y0 = int(math.floor(x0)), int(math.floor(y0))
        self.img = np.zeros((max(1, int(h)), max(1, int(w)), 4), np.uint8)

    @classmethod
    def around(cls, cx, cy, r):
        return cls(cx - r, cy - r, 2 * r + 2, 2 * r + 2)

    def _p(self, pts):
        return np.round((np.asarray(pts, np.float64).reshape(-1, 2) - [self.x0, self.y0]) * 16).astype(np.int32)

    def poly(self, pts, col, line=None, th=0):
        p = self._p(pts)
        cv2.fillPoly(self.img, [p], (*col, 255), cv2.LINE_AA, 4)
        if line is not None and th > 0:
            cv2.polylines(self.img, [p], True, (*line, 255), max(1, int(round(th))), cv2.LINE_AA, 4)

    def polyline(self, pts, col, th, closed=False):
        cv2.polylines(self.img, [self._p(pts)], closed, (*col, 255), max(1, int(round(th))), cv2.LINE_AA, 4)

    def circle(self, c, r, col, th=-1):
        p = self._p([c])[0]
        cv2.circle(self.img, (int(p[0]), int(p[1])), max(1, int(round(r * 16))), (*col, 255),
                   -1 if th <= 0 else max(1, int(round(th))), cv2.LINE_AA, 4)

    def ellipse(self, c, axes, ang, a0, a1, col, th=-1):
        p = self._p([c])[0]
        cv2.ellipse(self.img, (int(p[0]), int(p[1])), (max(1, int(axes[0] * 16)), max(1, int(axes[1] * 16))), ang,
                    a0, a1, (*col, 255), -1 if th <= 0 else max(1, int(round(th))), cv2.LINE_AA, 4)

    def line(self, p0, p1, col, th):
        a, b = self._p([p0, p1])
        cv2.line(self.img, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (*col, 255), max(1, int(round(th))),
                 cv2.LINE_AA, 4)

    def f32(self):
        f = self.img.astype(np.float32)
        f[..., 3] /= 255
        return f

    def to(self, dst, alpha=1.0):
        over(dst, self.f32(), self.x0, self.y0, alpha)


def rrect(x0, y0, x1, y1, r, n=6):
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def star_pts(cx, cy, r, rot=0.0, k=4, inner=0.3):
    pts = []
    for i in range(2 * k):
        rr = r if i % 2 == 0 else r * inner
        a = rot + math.pi * i / k - math.pi / 2
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def gear_poly(cx, cy, r, n, ang):
    P = 2 * math.pi / n
    rin = r * 0.82
    pts = []
    for i in range(n):
        a = ang + i * P
        for f, rr in ((0.0, rin), (0.40, rin), (0.50, r), (0.86, r), (0.96, rin)):
            pts.append((cx + rr * math.cos(a + f * P), cy + rr * math.sin(a + f * P)))
    return pts


def draw_gear(v, cx, cy, r, n, ang, col=GOLD, th=None):
    th = th or max(2.0, r * 0.07)
    v.poly(gear_poly(cx, cy, r, n, ang), col, DARK, th)
    v.circle((cx, cy), r * 0.58, shade(col, 0.86))
    v.circle((cx, cy), r * 0.58, DARK, th * 0.8)
    for k in range(4):
        a = ang + k * math.pi / 2 + 0.4
        v.circle((cx + r * 0.36 * math.cos(a), cy + r * 0.36 * math.sin(a)), r * 0.1, shade(col, 0.62))
    v.circle((cx, cy), r * 0.17, DARK)
    v.circle((cx, cy), r * 0.08, shade(col, 1.1))


def gear_pair(c1, r1, c2, r2, theta1):
    n1, n2 = max(6, round(r1 / 9.5)), max(6, round(r2 / 9.5))
    al = math.atan2(c2[1] - c1[1], c2[0] - c1[0])
    P1, P2 = 2 * math.pi / n1, 2 * math.pi / n2
    return (n1, al - 0.68 * P1 + theta1), (n2, al + math.pi - 0.18 * P2 - theta1 * n1 / n2)


# ------------------------------------------------------------------ yazı
@functools.lru_cache(None)
def font(size, var="Bold Condensed"):
    """var: "Bold Condensed" (kalin_dar) | "Bold SemiCondensed" (kalin_yari_dar) ya da tür adı."""
    yol, vary = ayar.font_yolu(var)
    if yol is None:
        return ImageFont.load_default(size)
    f = ImageFont.truetype(yol, size)
    if vary:
        try:
            f.set_variation_by_name(vary)
        except (OSError, ValueError):
            ayar.uyar(f"{yol} değişken font değil ya da '{vary}' varyasyonu yok; varsayılan ağırlık kullanılıyor")
    return f


def font_sifirla():
    """Yazı tipi seçimi değişince (ayar.proje_fontu) önbellekteki font ve yazı sprite'larını atar."""
    font.cache_clear()
    text_spr.cache_clear()


def tr_up(s):
    """Geriye uyum: dile göre büyük harf (ayar.buyuk)."""
    return ayar.buyuk(s)


@functools.lru_cache(512)
def text_spr(text, size, fill=CREAM, stroke=DARK, sw=8, spacing=0, shadow=0.35, var="Bold Condensed"):
    f = font(size, var)
    widths = [f.getlength(ch) for ch in text] if spacing else [f.getlength(text)]
    tw = sum(widths) + spacing * max(0, len(text) - 1)
    m = sw + 24
    Wt, Ht = int(tw + 2 * m), int(size * 1.45 + 2 * m)
    base_y = m + size * 1.05

    def draw(dr, col, scol, sww):
        if spacing:
            x = m
            for ch, wch in zip(text, widths):
                dr.text((x, base_y), ch, font=f, fill=col, stroke_width=sww, stroke_fill=scol, anchor="ls")
                x += wch + spacing
        else:
            dr.text((m, base_y), text, font=f, fill=col, stroke_width=sww, stroke_fill=scol, anchor="ls")

    im = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))
        draw(ImageDraw.Draw(sh), (30, 14, 6, int(255 * shadow)), (30, 14, 6, int(255 * shadow)), sw)
        sh = sh.filter(ImageFilter.GaussianBlur(5))
        im.alpha_composite(sh, (0, 6))
    draw(ImageDraw.Draw(im), fill, stroke, sw)
    return premul(np.array(im)), (Wt / 2, base_y - size * 0.36)


@functools.lru_cache(None)
def glow_spr(r, col=SKYGLOW, power=2.0, peak=0.7):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float32)
    a = np.clip(1 - np.sqrt(xx ** 2 + yy ** 2) / r, 0, 1) ** power * peak
    return np.dstack([np.array(col, np.float32)[None, None, :] * a[..., None], a])


def sparkles(fr, t, t0, center, n, radius, seed, dur=0.9, size=24, col=(255, 236, 160)):
    if not (t0 <= t <= t0 + dur + 0.5):
        return
    rng = np.random.default_rng(seed)
    for k in range(n):
        a = rng.uniform(0, 2 * math.pi)
        dist = radius * rng.uniform(0.35, 1.0)
        dl = rng.uniform(0, 0.25)
        dd = dur * rng.uniform(0.6, 1.0)
        p = prog(t, t0 + dl, t0 + dl + dd)
        if p <= 0 or p >= 1:
            continue
        x = center[0] + math.cos(a) * dist * e_out(p)
        y = center[1] + math.sin(a) * dist * e_out(p) * 0.8
        r = size * rng.uniform(0.6, 1.2) * math.sin(math.pi * p)
        v = Vec.around(x, y, r + 4)
        v.poly(star_pts(x, y, r, p * 2), col, GOLD_D, 2)
        v.to(fr)


def twinkles(fr, t, t0, t1, center, rx, ry, n, seed, col=(255, 244, 190), edge=GOLD_D):
    if not (t0 <= t <= t1):
        return
    rng = np.random.default_rng(seed)
    k_on = prog(t, t0, t0 + 0.3) * (1 - prog(t, t1 - 0.3, t1))
    for k in range(n):
        x = center[0] + rx * rng.uniform(-1, 1)
        y = center[1] + ry * rng.uniform(-1, 1)
        ph, sp = rng.uniform(0, 1), rng.uniform(1.2, 2.2)
        u = (t * sp + ph) % 1.0
        r = 20 * math.sin(math.pi * u) * rng.uniform(0.6, 1.1)
        if r < 1:
            continue
        v = Vec.around(x, y, r + 3)
        v.poly(star_pts(x, y, r, 0, 4, 0.28), col, edge, 2)
        v.to(fr, k_on)


def shadow_ellipse(fr, x, y, rx, ry, alpha=0.28):
    v = Vec.around(x, y, rx + 4)
    v.ellipse((x, y), (rx, ry), 0, 0, 360, (30, 18, 12))
    f = v.f32()
    f = cv2.GaussianBlur(f, (0, 0), max(1.0, ry * 0.35))
    over(fr, f, v.x0, v.y0, alpha)


# ------------------------------------------------------------------ dekupe (hazırlık)
def cutout(img, extra_seeds=()):
    """Beyaz arka planı (kenara değen + seed ile işaretlenen kapalı alanlar) şeffaf yapar."""
    white = (img.min(axis=2) > 222).astype(np.uint8)
    _, lab = cv2.connectedComponents(white, connectivity=4)
    bg_labels = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    for x, y in extra_seeds:
        if not white[y, x]:
            # kıvrık alanların ağırlık merkezi alanın dışına düşebilir: en yakın beyaz piksele kay
            win = white[max(0, y - 60):y + 61, max(0, x - 60):x + 61]
            ys, xs = np.nonzero(win)
            if len(xs):
                k = np.argmin((xs - min(60, x)) ** 2 + (ys - min(60, y)) ** 2)
                x, y = max(0, x - 60) + xs[k], max(0, y - 60) + ys[k]
        bg_labels.add(lab[y, x])
    bg_labels.discard(0)
    bg = np.isin(lab, list(bg_labels))
    near = cv2.dilate(bg.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool) & ~bg
    lum = img.astype(np.float32).mean(axis=2)
    alpha = np.where(bg, 0.0, 1.0).astype(np.float32)
    edge_a = np.clip((255 - lum) / (255 - 60), 0, 1)
    alpha[near] = np.minimum(1.0, edge_a[near] * 1.15)
    rgb = img.astype(np.float32)
    rgb[near] = OUTLINE
    return np.dstack([rgb, alpha * 255]).clip(0, 255).astype(np.uint8)


def poly_mask(shape, pts):
    m = np.zeros(shape[:2], np.uint8)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 255, cv2.LINE_AA)
    return m.astype(np.float32) / 255


def scaled(rgba, s):
    h, w = rgba.shape[:2]
    pm = rgba.astype(np.float32)
    pm[..., :3] *= pm[..., 3:4] / 255
    pm = cv2.resize(pm, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
    a = pm[..., 3:4]
    rgb = np.where(a > 0.5, pm[..., :3] * 255 / np.maximum(a, 1e-3), 0)
    return np.dstack([rgb, a]).clip(0, 255).astype(np.uint8)


def bbox(*layers, pad=12):
    a = np.zeros(layers[0].shape[:2], bool)
    for l in layers:
        a |= l[..., 3] > 8
    ys, xs = np.nonzero(a)
    return xs.min() - pad, ys.min() - pad, xs.max() + pad, ys.max() + pad


def closed_eye(rgba, cx, cy, rx, ry, skin, shape="blink"):
    out = rgba.copy()
    cv2.ellipse(out, (cx, cy), (rx + 6, ry + 4), 0, 0, 360, (*skin, 255), -1, cv2.LINE_AA)
    col = (*[int(c) for c in OUTLINE], 255)
    if shape == "blink":
        cv2.ellipse(out, (cx, cy + 4), (rx + 2, 16), 0, 10, 170, col, 14, cv2.LINE_AA)
    else:
        cv2.ellipse(out, (cx, cy + 22), (rx + 4, 34), 0, 195, 345, col, 15, cv2.LINE_AA)
    return out
