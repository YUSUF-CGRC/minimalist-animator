"""Tarayıcıda indirme düğmesine bastıktan sonra indirilenler klasörüne düşen dosyayı bekler ve doğru adla proje
klasörüne taşır. Klasör: ayarlar.json -> araclar.indirilenler_klasoru (varsayılan ~/Downloads); göreli hedef proje köküne göre.

  ma indir-bekle <hedef_klasor> <ad_uzantisiz> [desen] [--sure 40]

  desen varsayılanı Gemini için "Gemini_Generated_Image_*"; ElevenLabs için "ElevenLabs_*".
  Son 5 dakikada değişmiş, eşleşen en yeni dosya alınır; uzantısı korunur.
  Çıkış 0: taşındı · 1: süre içinde dosya gelmedi (indirme engellenmiş olabilir — gerçek tıklamayla tekrar dene).

Her indirmeden hemen sonra çalıştır: böylece dosya sırası karışmaz.
"""
import argparse
import glob
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "motor"))  # eklenti içi
import ayar  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("hedef")
    ap.add_argument("ad")
    ap.add_argument("desen", nargs="?", default="Gemini_Generated_Image_*")
    ap.add_argument("--sure", type=int, default=40)
    a = ap.parse_args()

    indirilenler = os.path.normpath(os.path.expanduser(str(ayar.al("araclar.indirilenler_klasoru", "") or "~/Downloads")))
    if not os.path.isabs(a.hedef) and ayar.kok_var_mi():  # göreli hedef proje köküne göre
        a.hedef = ayar.yol(a.hedef)
    os.makedirs(a.hedef, exist_ok=True)
    for _ in range(a.sure):
        adaylar = [p for p in glob.glob(os.path.join(indirilenler, a.desen))
                   if not p.endswith(".crdownload") and time.time() - os.path.getmtime(p) < 300]
        if adaylar:
            kaynak = max(adaylar, key=os.path.getmtime)
            time.sleep(1)  # yazma bitsin
            yeni = os.path.join(a.hedef, a.ad + os.path.splitext(kaynak)[1].lower())
            shutil.move(kaynak, yeni)
            print(f"{os.path.basename(kaynak)} -> {yeni} ({os.path.getsize(yeni) / 1e6:.2f} MB)")
            return 0
        time.sleep(1)
    print("YOK: süre içinde indirilen dosya görünmedi")
    return 1


if __name__ == "__main__":
    sys.exit(main())
