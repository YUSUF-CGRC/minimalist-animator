"""Beyaz zeminli çizimleri dekupe eder (şeffaf PNG) ve kontrol önizlemesi üretir.

Örnekler:
  ma dekupe cizim/ham/teleskop.jpeg --cikti cizim/hazir
  ma dekupe cizim/ham/kasif_acik.png cizim/ham/kasif_kapali.png --grup --cikti cizim/hazir
  ma dekupe cizim/ham/teleskop.jpeg --cikti cizim/hazir --tohum 952,777 --tohum 1298,766
  ma dekupe cizim/ham/gece-gokyuzu.png --arka-plan --cikti cizim/hazir
(Göreli yollar çalışma klasörüne göredir: proje klasöründen çalıştırın.)

--grup      : aynı karakterin varyantları (acik/kapali/konusma). Hizalanır ve aynı kutuyla kırpılır.
--tohum x,y : figürün içinde kalmış ama aslında zemin olan beyaz alan (kol ile gövde arası gibi). Önizlemedeki
              numaralı sarı işaretler aday alanlardır; koordinatlar stdout'ta yazar.
--arka-plan : dekupe yapılmaz; 9:16'ya kırpılıp PNG yapılır (--filigran ile sağ alt köşe temizlenir).
Önizlemeler <cikti>/../onizleme/ altına yazılır: solda orijinal, sağda koyu zemin üstünde dekupe.
"""
import argparse
import os
import sys

import cv2
import numpy as np
from PIL import Image

OUTLINE = np.array([44, 20, 20], np.float32)


def yukle(yol):
    return np.array(Image.open(yol).convert("RGB"))


def dekupe(img, tohumlar=(), esik=222):
    beyaz = (img.min(axis=2) > esik).astype(np.uint8)
    _, lab = cv2.connectedComponents(beyaz, connectivity=4)
    zemin = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    for x, y in tohumlar:
        if not beyaz[y, x]:
            pencere = beyaz[max(0, y - 60):y + 61, max(0, x - 60):x + 61]
            ys, xs = np.nonzero(pencere)
            if len(xs):
                k = np.argmin((xs - min(60, x)) ** 2 + (ys - min(60, y)) ** 2)
                x, y = max(0, x - 60) + xs[k], max(0, y - 60) + ys[k]
        zemin.add(lab[y, x])
    zemin.discard(0)
    bg = np.isin(lab, list(zemin))
    yakin = cv2.dilate(bg.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool) & ~bg
    lum = img.astype(np.float32).mean(axis=2)
    alfa = np.where(bg, 0.0, 1.0).astype(np.float32)
    kenar = np.clip((255 - lum) / (255 - 60), 0, 1)
    alfa[yakin] = np.minimum(1.0, kenar[yakin] * 1.15)
    rgb = img.astype(np.float32)
    rgb[yakin] = OUTLINE
    return np.dstack([rgb, alfa * 255]).clip(0, 255).astype(np.uint8), lab, zemin


def mer_x(st, i):
    return st[i, cv2.CC_STAT_LEFT] + st[i, cv2.CC_STAT_WIDTH] / 2


def mer_y(st, i):
    return st[i, cv2.CC_STAT_TOP] + st[i, cv2.CC_STAT_HEIGHT] / 2


def adalari_temizle(rgba, oran=0.015):
    """Ana figürden kopuk küçük parçaları (Gemini köşe filigranı, kırıntılar) siler."""
    a = (rgba[..., 3] > 20).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(a, connectivity=8)
    if n <= 2:
        return rgba, 0
    alanlar = st[1:, cv2.CC_STAT_AREA]
    ana = int(np.argmax(alanlar)) + 1
    buyuk = alanlar.max()
    pay = int(0.04 * max(rgba.shape[:2]))
    x0, y0 = st[ana, cv2.CC_STAT_LEFT] - pay, st[ana, cv2.CC_STAT_TOP] - pay
    x1 = st[ana, cv2.CC_STAT_LEFT] + st[ana, cv2.CC_STAT_WIDTH] + pay
    y1 = st[ana, cv2.CC_STAT_TOP] + st[ana, cv2.CC_STAT_HEIGHT] + pay
    # küçük VE ana figürün çevresinden uzak parçalar silinir (yakındaki küçük detaylar kalır)
    sil = [i for i in range(1, n) if i != ana and st[i, cv2.CC_STAT_AREA] < buyuk * oran
           and not (x0 <= mer_x(st, i) <= x1 and y0 <= mer_y(st, i) <= y1)]
    out = rgba.copy()
    if sil:
        out[np.isin(lab, sil), 3] = 0
    return out, len(sil)


def kapali_beyazlar(img, rgba, lab, zemin, esik, min_alan=1200):
    """Figürün içinde kalan saf beyaz alanlar: zemin olabilir (aday), beyaz kıyafet de olabilir."""
    beyaz = (img.min(axis=2) > max(esik, 240)).astype(np.uint8) & (rgba[..., 3] > 0)
    n, l2, st, mer = cv2.connectedComponentsWithStats(beyaz, connectivity=4)
    out = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] >= min_alan:
            cx, cy = int(mer[i][0]), int(mer[i][1])
            ys, xs = np.nonzero(l2 == i)
            k = len(xs) // 2
            out.append((int(xs[k]), int(ys[k]), int(st[i, cv2.CC_STAT_AREA])))
    out.sort(key=lambda a: -a[2])
    return out[:12]


def kenar_beyaz_mi(img, esik):
    kenar = np.concatenate([img[0], img[-1], img[:, 0], img[:, -1]])
    return float((kenar.min(axis=1) > esik).mean())


def hizala(ref, img):
    g0 = cv2.cvtColor(ref, cv2.COLOR_RGB2GRAY).astype(np.float32)
    g1 = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)
    (dx, dy), _ = cv2.phaseCorrelate(g0, g1)
    if abs(dx) < 0.5 and abs(dy) < 0.5 or abs(dx) > 60 or abs(dy) > 60:
        return img, (0.0, 0.0)
    M = np.float32([[1, 0, -dx], [0, 1, -dy]])
    out = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]), borderValue=(255, 255, 255))
    return out, (dx, dy)


def filigran_temizle(img):
    """Sağ alt köşedeki küçük filigranı çevresiyle doldurur (arka plan görselleri için)."""
    h, w = img.shape[:2]
    y0, x0 = int(h * 0.9), int(w * 0.88)
    kose = img[y0:, x0:]
    med = cv2.medianBlur(kose, 31)
    fark = np.abs(kose.astype(np.int16) - med.astype(np.int16)).max(axis=2)
    maske = np.zeros((h, w), np.uint8)
    maske[y0:, x0:] = (fark > 28).astype(np.uint8) * 255
    maske = cv2.dilate(maske, np.ones((9, 9), np.uint8))
    if maske.sum() == 0:
        return img
    return cv2.inpaint(img, maske, 7, cv2.INPAINT_TELEA)


def kirp(rgba, kutu):
    x0, y0, x1, y1 = kutu
    return rgba[y0:y1, x0:x1]


def kutu_bul(*katmanlar, pay=8):
    a = np.zeros(katmanlar[0].shape[:2], bool)
    for k in katmanlar:
        a |= k[..., 3] > 8
    ys, xs = np.nonzero(a)
    h, w = a.shape
    return max(0, xs.min() - pay), max(0, ys.min() - pay), min(w, xs.max() + pay + 1), min(h, ys.max() + pay + 1)


def onizleme(yol, orijinal, rgba, adaylar, kutu):
    h = 900
    o = Image.fromarray(orijinal)
    o = o.resize((int(o.width * h / o.height), h))
    zemin = np.zeros((rgba.shape[0], rgba.shape[1], 3), np.uint8)
    zemin[:] = (38, 64, 96)
    zemin[(np.indices(zemin.shape[:2]).sum(0) // 40) % 2 == 0] = (46, 76, 112)
    a = rgba[..., 3:4].astype(np.float32) / 255
    birlesik = (rgba[..., :3] * a + zemin * (1 - a)).astype(np.uint8)
    x0, y0 = kutu[0], kutu[1]
    for i, (x, y, _) in enumerate(adaylar):
        px, py = x - x0, y - y0
        if 0 <= px < birlesik.shape[1] and 0 <= py < birlesik.shape[0]:
            cv2.circle(birlesik, (px, py), 26, (255, 214, 0), 5, cv2.LINE_AA)
            cv2.putText(birlesik, str(i + 1), (px - 12, py + 12), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 214, 0), 3,
                        cv2.LINE_AA)
    d = Image.fromarray(birlesik)
    d = d.resize((max(1, int(d.width * h / d.height)), h))
    tuval = Image.new("RGB", (o.width + d.width + 20, h), (20, 20, 20))
    tuval.paste(o, (0, 0))
    tuval.paste(d, (o.width + 20, 0))
    tuval.save(yol)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("girdi", nargs="+")
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--ad", help="tek girdi için çıktı dosya adı (uzantısız)")
    ap.add_argument("--grup", action="store_true")
    ap.add_argument("--arka-plan", action="store_true")
    ap.add_argument("--filigran", action="store_true")
    ap.add_argument("--esik", type=int, default=222)
    ap.add_argument("--tohum", action="append", default=[], help="x,y (orijinal görsel koordinatı)")
    ap.add_argument("--adalari-koru", action="store_true")
    a = ap.parse_args()

    os.makedirs(a.cikti, exist_ok=True)
    oniz = os.path.join(os.path.dirname(os.path.abspath(a.cikti)), "onizleme")
    os.makedirs(oniz, exist_ok=True)
    tohumlar = [tuple(int(v) for v in t.split(",")) for t in a.tohum]

    if a.arka_plan:
        for g in a.girdi:
            img = yukle(g)
            if a.filigran:
                img = filigran_temizle(img)
            h, w = img.shape[:2]
            hedef = 9 / 16
            if w / h > hedef:
                nw = int(h * hedef)
                img = img[:, (w - nw) // 2:(w - nw) // 2 + nw]
            elif w / h < hedef - 0.01:
                nh = int(w / hedef)
                img = img[(h - nh) // 2:(h - nh) // 2 + nh]
            ad = a.ad or os.path.splitext(os.path.basename(g))[0]
            yol = os.path.join(a.cikti, ad + ".png")
            Image.fromarray(img).save(yol)
            print(f"arka plan: {yol} ({img.shape[1]}x{img.shape[0]})")
        return

    ref = None
    sonuclar = []
    for g in a.girdi:
        img = yukle(g)
        kayma = (0.0, 0.0)
        if a.grup:
            if ref is None:
                ref = img
            else:
                if img.shape != ref.shape:
                    img = cv2.resize(img, (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_AREA)
                img, kayma = hizala(ref, img)
        beyaz_oran = kenar_beyaz_mi(img, a.esik)
        rgba, lab, zemin = dekupe(img, tohumlar, a.esik)
        silinen = 0
        if not a.adalari_koru:
            rgba, silinen = adalari_temizle(rgba)
        adaylar = kapali_beyazlar(img, rgba, lab, zemin, a.esik)
        sonuclar.append((g, img, rgba, adaylar, beyaz_oran, silinen, kayma))

    kutu_ortak = kutu_bul(*[r[2] for r in sonuclar]) if a.grup else None
    for g, img, rgba, adaylar, beyaz_oran, silinen, kayma in sonuclar:
        kutu = kutu_ortak or kutu_bul(rgba)
        ad = a.ad if (a.ad and len(sonuclar) == 1) else os.path.splitext(os.path.basename(g))[0]
        yol = os.path.join(a.cikti, ad + ".png")
        Image.fromarray(kirp(rgba, kutu), "RGBA").save(yol)
        oy = os.path.join(oniz, ad + "_onizleme.png")
        onizleme(oy, img, kirp(rgba, kutu), adaylar, kutu)
        print(f"dekupe: {yol}  boyut={kutu[2] - kutu[0]}x{kutu[3] - kutu[1]}  önizleme={oy}")
        if beyaz_oran < 0.97:
            print(f"  UYARI: kenarların sadece %{beyaz_oran * 100:.0f}'i beyaz — zemin düz beyaz değil, dekupe bozuk olabilir.")
        if silinen:
            print(f"  bilgi: {silinen} küçük kopuk parça silindi (filigran/kırıntı). Gerekirse --adalari-koru.")
        if a.grup and (abs(kayma[0]) > 0 or abs(kayma[1]) > 0):
            print(f"  bilgi: varyant referansa göre ({kayma[0]:.1f}, {kayma[1]:.1f}) px kaydırılarak hizalandı.")
        if adaylar:
            print("  Figür içinde kalan beyaz alanlar (zemin olabilir; öyleyse --tohum x,y ile ver):")
            for i, (x, y, ar) in enumerate(adaylar):
                print(f"    #{i + 1}: --tohum {x},{y}   alan={ar}px")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
