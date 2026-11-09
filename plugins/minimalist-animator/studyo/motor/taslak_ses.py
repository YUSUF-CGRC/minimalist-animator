"""Taslak ses: gerçek seslendirme gelmeden kurguyu denemek için satır başına yumuşak bir "mırıltı" üretir.

  ma taslak-ses <proje> [--zorla]
Çıktı: ses/parcalar/NN_<konusan>.wav + ses/zamanlama.json (ses_bol.py ile aynı şema; "kaynak": "taslak").
Süre: satırın karakter sayısı / konuşma hızı (ayarlar -> icerik.konusma_hizi_kar_sn, dile göre); süre hecelere
bölünür, her hece ayrı bir ses darbesi olur -> motorun konuşma zarfı ağız ve zıplama animasyonunu oynatır.
Gerçek ses (kaynak != "taslak") varsa üzerine yazmaz; --zorla ile yazar.
"""
import argparse
import json
import math
import os
import sys
import zlib

import numpy as np

import ayar
import ses_araclari as A

SR = A.SR
DURAK = {",": 0.12, ";": 0.16, ":": 0.14, ".": 0.24, "!": 0.24, "?": 0.24, "…": 0.3}


def _hece(kelime):
    rak = sum(ch.isdigit() for ch in kelime)
    return max(2, int(rak * 1.5)) if rak else A.hece_sayisi(kelime)


def plan(metin, hiz):
    """-> [(hece süresi, sonrasındaki boşluk, kelime sonu mu, cümle sonu işareti)], toplam süre"""
    kelimeler = metin.split()
    if not kelimeler:
        return [], 0.5
    hedef = max(0.6, len(metin) / hiz)
    durak = [DURAK.get(k.rstrip("\"'”’)»")[-1:], 0.04) if k.rstrip("\"'”’)»") else 0.04 for k in kelimeler]
    durak[-1] = 0.0
    heceler = [_hece(k) for k in kelimeler]
    hece_sn = (hedef - sum(durak)) / sum(heceler)
    hece_sn = min(0.30, max(0.10, hece_sn))
    out = []
    for k, h, d in zip(kelimeler, heceler, durak):
        son = k.rstrip("\"'”’)»")[-1:] if k.rstrip("\"'”’)»") else ""
        for i in range(h):
            out.append((hece_sn, d if i == h - 1 else 0.0, i == h - 1, son if i == h - 1 else ""))
    return out, sum(a + b for a, b, _, _ in out)


def mirilti(metin, hiz, tohum, soru=False):
    """Hece darbelerinden oluşan yumuşak, ünlü benzeri ses (mono float64)."""
    rng = np.random.default_rng(tohum)
    adimlar, toplam = plan(metin, hiz)
    f0 = 170 + (tohum % 60)                     # konuşana göre sabit perde
    n = int((toplam + 0.12) * SR)
    y = np.zeros(n)
    t0, faz0, kelime_basi = 0.04, 0.0, True
    for i, (sure, bosluk, kelime_sonu, isaret) in enumerate(adimlar):
        m = int(sure * SR)
        t = np.arange(m) / SR
        u = t / max(sure, 1e-3)
        ilerleme = i / max(1, len(adimlar) - 1)
        perde = f0 * (1.0 + 0.06 * math.sin(2.3 * i) - 0.08 * ilerleme)
        if soru and ilerleme > 0.8:
            perde *= 1 + 0.25 * (ilerleme - 0.8) / 0.2
        perde = perde * (1 + 0.03 * np.sin(2 * np.pi * 5.5 * t) + 0.04 * (u - 0.5))
        faz = faz0 + 2 * np.pi * np.cumsum(perde) / SR               # faz heceler arasında sürekli (tık yok)
        faz0 = float(faz[-1]) if m else faz0
        dalga = (np.sin(faz) + 0.45 * np.sin(2 * faz) + 0.22 * np.sin(3 * faz) + 0.08 * np.sin(4 * faz))
        dalga += 0.015 * rng.standard_normal(m)
        # hece darbesi: kelime içinde heceler arası 0.3'e iner (ağız kapanıp açılır), kelime başı/sonu sıfırdan
        taban = (0.0 if kelime_basi else 0.3) * (1 - u) + (0.0 if kelime_sonu else 0.3) * u
        zarf = taban + (1 - taban) * np.sin(np.pi * np.clip(u, 0, 1)) ** 0.7
        bas = int(t0 * SR)
        y[bas:bas + m] += (dalga * zarf)[:max(0, n - bas)]
        t0 += sure + bosluk
        kelime_basi = kelime_sonu
    a = int(0.01 * SR)
    y[:a] *= np.linspace(0, 1, a)
    y[-a:] *= np.linspace(1, 0, a)
    m = np.abs(y).max()
    return y * (0.5 / m) if m > 0 else y


def uret(proje, zorla=False):
    with open(os.path.join(proje, "senaryo.json"), encoding="utf-8") as f:
        sen = json.load(f)
    zyol = os.path.join(proje, "ses", "zamanlama.json")
    if os.path.exists(zyol) and not zorla:
        with open(zyol, encoding="utf-8") as f:
            eski = json.load(f)
        gercek = [p for p in eski.get("parcalar", []) if p.get("kaynak") != "taslak"]
        if gercek:
            sys.exit(f"ses/zamanlama.json gerçek ses içeriyor ({len(gercek)} parça); taslak yazılmadı. --zorla ile üzerine yazılır.")
    pdir = os.path.join(proje, "ses", "parcalar")
    os.makedirs(pdir, exist_ok=True)
    hiz = ayar.konusma_hizi()
    zam = {"parcalar": [], "kaynak": "taslak"}
    for s in sorted(sen.get("satirlar", []), key=lambda s: s["no"]):
        metin = s.get("metin") or s.get("altyazi") or ""
        tohum = zlib.crc32(str(s.get("konusan", "")).encode())
        x = mirilti(metin, hiz, tohum, soru=metin.rstrip().endswith("?"))
        ad = f"{s['no']:02d}_{s['konusan']}.wav"
        A.kaydet(os.path.join(pdir, ad), x)
        sure = A.sure(x)
        zam["parcalar"].append({"satir": s["no"], "konusan": s["konusan"], "dosya": f"parcalar/{ad}",
                                "sure": round(sure, 3), "kaynak": "taslak", "kaynak_bas": 0.0,
                                "kaynak_bit": round(sure, 3)})
        print(f"  {ad:<26} {sure:5.2f} sn  '{metin[:40]}'")
    zam["toplam_konusma_sn"] = round(sum(p["sure"] for p in zam["parcalar"]), 2)
    with open(zyol, "w", encoding="utf-8") as f:
        json.dump(zam, f, ensure_ascii=False, indent=2)
    print(f"taslak zamanlama.json yazıldı ({hiz:g} kar/sn). Toplam konuşma {zam['toplam_konusma_sn']} sn.")
    return zyol


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("proje")
    ap.add_argument("--zorla", action="store_true", help="gerçek sesin üzerine yaz")
    a = ap.parse_args()
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "araclar"))
    from proje import bul
    uret(bul(a.proje), a.zorla)
    return 0


if __name__ == "__main__":
    sys.exit(main())
