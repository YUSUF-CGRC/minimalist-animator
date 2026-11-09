"""Yeni proje kökü kurar: eklentideki sablon/ iskeletini hedef klasöre kopyalar (yalnızca standart kütüphane).

  ma kurulum [hedef] [--ayar anahtar=değer ...] [--python-yenile]
  ma kurulum ~/Videolarim --ayar marka.ad="Bilim Kutusu" --ayar kullanici.ad=Deniz --ayar icerik.dil=tr

Yapılanlar (var olan hiçbir dosyanın üzerine yazılmaz):
  ayarlar.json                  <- sablon/ayarlar.varsayilan.json (yoksa); --ayar alanları noktalı yolla doldurulur
  CLAUDE.md                     <- sablon/CLAUDE.md (yoksa)
  sirket/...                    <- sablon/sirket/ (izinli-alanlar.json, bilgi-bankasi/, boş arşiv şemaları)
  sirket/{projeler, arsiv/fontlar, arsiv/marka, bilgi-bankasi, kullanici/metinler, kullanici/sohbet}/
  sirket/.python                <- numpy, Pillow, cv2, imageio_ffmpeg yüklü ilk Python (bulunursa)
  sirket/.eklenti               <- eklenti klasörü (animasyon/render.py motoru buradan bulur)
pip çalıştırılmaz; bağımlılıklar eksikse kurulum komutu yazdırılır.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

EKLENTI = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SABLON = os.path.join(EKLENTI, "sablon")
GEREKSINIM = os.path.join(EKLENTI, "studyo", "requirements.txt")
KLASORLER = ["sirket/projeler", "sirket/arsiv/fontlar", "sirket/arsiv/marka", "sirket/arsiv/stil-referansi",
             "sirket/bilgi-bankasi", "sirket/kullanici/metinler", "sirket/kullanici/sohbet"]
SINAMA = ("import sys, numpy, cv2, PIL, imageio_ffmpeg; "
          "v = tuple(int(x) for x in PIL.__version__.split('.')[:2]); "
          "print(sys.executable); print(PIL.__version__); sys.exit(0 if v >= (10, 1) else 3)")


def deger_coz(s):
    """--ayar değeri: JSON olarak okunabiliyorsa (sayı, true, liste...) o, değilse düz metin."""
    try:
        return json.loads(s)
    except ValueError:
        return s


def yola_yaz(veri, nokta_yolu, deger):
    d = veri
    parcalar = nokta_yolu.split(".")
    for k in parcalar[:-1]:
        if not isinstance(d.get(k), dict):
            d[k] = {}
        d = d[k]
    d[parcalar[-1]] = deger


def yoldan_oku(veri, nokta_yolu):
    d = veri
    for k in nokta_yolu.split("."):
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def python_sina(komut):
    """komut (liste) bağımlılıklarla çalışıyorsa -> (yorumlayıcı yolu, Pillow sürümü), değilse None."""
    try:
        p = subprocess.run([*komut, "-c", SINAMA], capture_output=True, text=True, timeout=90)
    except (OSError, subprocess.SubprocessError):
        return None
    satirlar = p.stdout.strip().splitlines()
    if p.returncode == 0 and len(satirlar) >= 2:
        return satirlar[0].strip(), satirlar[1].strip()
    if p.returncode == 3 and satirlar:
        print(f"  {' '.join(komut)}: Pillow {satirlar[-1]} eski (>= 10.1 gerekli)")
    return None


def python_adaylari(ayar_python=""):
    adaylar = []
    if ayar_python:
        adaylar.append([ayar_python])
    adaylar.append([sys.executable])
    for ad in ("python3", "python"):
        y = shutil.which(ad)
        if y:
            adaylar.append([y])
    if shutil.which("py"):
        adaylar.append(["py", "-3"])
        try:
            liste = subprocess.run(["py", "-0p"], capture_output=True, text=True, timeout=20).stdout
            for satir in liste.splitlines():
                parca = satir.strip().split()
                if parca and parca[-1].lower().endswith("python.exe") and os.path.isfile(parca[-1]):
                    adaylar.append([parca[-1]])
        except (OSError, subprocess.SubprocessError):
            pass
    gorulen, out = set(), []
    for a in adaylar:
        anahtar = os.path.normcase(os.path.abspath(a[0])) if len(a) == 1 and os.path.isfile(a[0]) else " ".join(a)
        if anahtar not in gorulen:
            gorulen.add(anahtar)
            out.append(a)
    return out


def kopyala(kaynak, hedef, yapilan, atlanan):
    if os.path.exists(hedef):
        atlanan.append(hedef)
        return False
    os.makedirs(os.path.dirname(hedef), exist_ok=True)
    shutil.copy2(kaynak, hedef)
    yapilan.append(hedef)
    return True


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("hedef", nargs="?", help="proje kökü (varsayılan: MA_KOK ya da çalışma klasörü)")
    ap.add_argument("--ayar", action="append", default=[], metavar="anahtar=değer")
    ap.add_argument("--python-yenile", action="store_true", help="sirket/.python dosyasını yeniden belirle")
    a = ap.parse_args()
    hedef = os.path.abspath(os.path.expanduser(a.hedef or os.environ.get("MA_KOK") or os.getcwd()))
    os.makedirs(hedef, exist_ok=True)
    yapilan, atlanan = [], []
    print(f"Kurulum: {hedef}\n  eklenti: {EKLENTI}")

    # ayarlar.json
    ayar_yolu = os.path.join(hedef, "ayarlar.json")
    yeni_ayar = not os.path.exists(ayar_yolu)
    if yeni_ayar:
        shutil.copyfile(os.path.join(SABLON, "ayarlar.varsayilan.json"), ayar_yolu)
        yapilan.append(ayar_yolu)
    else:
        atlanan.append(ayar_yolu)
    if a.ayar:
        with open(ayar_yolu, encoding="utf-8") as f:
            veri = json.load(f)
        with open(os.path.join(SABLON, "ayarlar.varsayilan.json"), encoding="utf-8") as f:
            varsayilan = json.load(f)
        for atama in a.ayar:
            if "=" not in atama:
                sys.exit(f"--ayar anahtar=değer biçiminde olmalı: {atama}")
            anahtar, deger = atama.split("=", 1)
            anahtar = anahtar.strip()
            if yoldan_oku(varsayilan, anahtar) is None:
                print(f"  UYARI: '{anahtar}' varsayılan ayarlarda yok (yine de yazıldı)")
            yola_yaz(veri, anahtar, deger_coz(deger))
            print(f"  ayar: {anahtar} = {json.dumps(yoldan_oku(veri, anahtar), ensure_ascii=False)}")
        veri["_tur"] = veri.get("_tur") or "minimalist-animator"
        with open(ayar_yolu, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
            f.write("\n")
    else:
        with open(ayar_yolu, encoding="utf-8") as f:
            veri = json.load(f)
    if veri.get("_tur") != "minimalist-animator":
        print("  UYARI: ayarlar.json'da \"_tur\": \"minimalist-animator\" yok; araçlar bu klasörü proje kökü sayamaz")

    # CLAUDE.md ve sirket/ iskeleti
    if os.path.isfile(os.path.join(SABLON, "CLAUDE.md")):
        kopyala(os.path.join(SABLON, "CLAUDE.md"), os.path.join(hedef, "CLAUDE.md"), yapilan, atlanan)
    for k in KLASORLER:
        os.makedirs(os.path.join(hedef, k), exist_ok=True)
    kaynak_sirket = os.path.join(SABLON, "sirket")
    for kok, _, dosyalar in os.walk(kaynak_sirket):
        for d in dosyalar:
            k = os.path.join(kok, d)
            kopyala(k, os.path.join(hedef, "sirket", os.path.relpath(k, kaynak_sirket)), yapilan, atlanan)

    # eklenti yolu (render.py doğrudan çalıştırılırsa motoru buradan bulur) — makine yerel bilgisi, her kurulumda tazelenir
    with open(os.path.join(hedef, "sirket", ".eklenti"), "w", encoding="utf-8") as f:
        f.write(EKLENTI.replace("\\", "/") + "\n")

    # Python yorumlayıcısı
    py_yolu = os.path.join(hedef, "sirket", ".python")
    if os.path.exists(py_yolu) and not a.python_yenile:
        with open(py_yolu, encoding="utf-8") as f:
            mevcut = f.read().strip()
        durum = python_sina([mevcut]) if mevcut else None
        print(f"  sirket/.python zaten var: {mevcut} ({'çalışıyor' if durum else 'ÇALIŞMIYOR — --python-yenile'})")
    else:
        secilen = None
        for aday in python_adaylari(str(yoldan_oku(veri, "araclar.python") or "")):
            secilen = python_sina(aday)
            if secilen:
                break
        if secilen:
            with open(py_yolu, "w", encoding="utf-8") as f:
                f.write(secilen[0].replace("\\", "/") + "\n")
            yapilan.append(py_yolu)
            print(f"  Python: {secilen[0]} (Pillow {secilen[1]}) -> sirket/.python")
        else:
            print("  UYARI: numpy, Pillow>=10.1, opencv ve imageio-ffmpeg yüklü bir Python bulunamadı. Kurmak için:\n"
                  f'    "{sys.executable}" -m pip install -r "{GEREKSINIM}"\n'
                  "  sonra: ma kurulum --python-yenile")

    for y in yapilan:
        print("  + " + os.path.relpath(y, hedef).replace("\\", "/"))
    if atlanan:
        print(f"  ({len(atlanan)} dosya zaten vardı, dokunulmadı)")
    print("Hazır. Sıradaki adım: ma doktor  ·  ma demo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
