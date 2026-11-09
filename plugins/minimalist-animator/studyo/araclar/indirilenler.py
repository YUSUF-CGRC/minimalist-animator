"""İndirilenler klasöründeki son dosyaları bulur ve (isteğe bağlı) proje klasörüne taşır.

  ma indirilenler --son-dakika 15 --uzanti png,jpg,jpeg,webp
  ma indirilenler --son-dakika 15 --uzanti mp3 --tasi sirket/projeler/<proje>/ses/ham
  ma indirilenler --son-dakika 15 --uzanti png --tasi <klasor> --adlar kasif_acik.png,kasif_kapali.png
--adlar verilirse dosyalar indirilme sırasına (eskiden yeniye) göre bu adlarla kaydedilir.
İndirilenler klasörü: ayarlar.json -> araclar.indirilenler_klasoru (varsayılan ~/Downloads). Göreli --tasi yolu
proje köküne göredir.
"""
import argparse
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "motor"))  # eklenti içi
import ayar  # noqa: E402

INDIRILENLER = os.path.normpath(os.path.expanduser(str(ayar.al("araclar.indirilenler_klasoru", "") or "~/Downloads")))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--son-dakika", type=float, default=15)
    ap.add_argument("--uzanti", default="png,jpg,jpeg,webp,mp3,wav")
    ap.add_argument("--tasi")
    ap.add_argument("--adlar")
    ap.add_argument("--klasor", default=INDIRILENLER)
    a = ap.parse_args()
    if a.tasi and not os.path.isabs(a.tasi) and ayar.kok_var_mi():
        a.tasi = ayar.yol(a.tasi)
    if not os.path.isdir(a.klasor):
        print(f"İndirilenler klasörü yok: {a.klasor} (ayarlar.json -> araclar.indirilenler_klasoru)")
        return 1
    uz = {"." + u.strip().lower().lstrip(".") for u in a.uzanti.split(",")}
    sinir = time.time() - a.son_dakika * 60
    dosyalar = []
    for ad in os.listdir(a.klasor):
        y = os.path.join(a.klasor, ad)
        if not os.path.isfile(y) or os.path.splitext(ad)[1].lower() not in uz:
            continue
        if ad.endswith((".crdownload", ".tmp", ".part")):
            continue
        mt = os.path.getmtime(y)
        if mt >= sinir:
            dosyalar.append((mt, y))
    dosyalar.sort()
    bekleyen = [x for x in os.listdir(a.klasor) if x.endswith(".crdownload")]
    if bekleyen:
        print(f"UYARI: henüz bitmemiş indirme var: {bekleyen}")
    if not dosyalar:
        print(f"Son {a.son_dakika:g} dakikada {', '.join(sorted(uz))} uzantılı dosya yok ({a.klasor}).")
        return 1
    adlar = [x.strip() for x in a.adlar.split(",")] if a.adlar else None
    if adlar and len(adlar) != len(dosyalar):
        print(f"UYARI: {len(dosyalar)} dosya var ama {len(adlar)} ad verildi; taşıma yapılmadı.")
        adlar, a.tasi = None, None
    for i, (mt, y) in enumerate(dosyalar):
        boy = os.path.getsize(y) / 1e6
        zaman = time.strftime("%H:%M:%S", time.localtime(mt))
        if a.tasi:
            os.makedirs(a.tasi, exist_ok=True)
            hedef = os.path.join(a.tasi, adlar[i] if adlar else os.path.basename(y))
            shutil.move(y, hedef)
            print(f"{zaman}  {boy:5.2f} MB  {os.path.basename(y)}  ->  {hedef}")
        else:
            print(f"{zaman}  {boy:5.2f} MB  {y}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
