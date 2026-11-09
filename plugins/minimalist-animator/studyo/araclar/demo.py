"""Çevrimdışı demo: eklentideki ornek/demo/ projesini proje köküne kopyalar ve uçtan uca çalıştırır.

  ma demo              -> kopyala, çiz (hazirla.py), taslak ses, render, kontrol; MP4 yolunu yazar
  ma demo --kareler    -> render yerine yalnızca kontrol kareleri (hızlı)
Proje: sirket/projeler/0000-00-00_demo/ ("0000-00-00_" öneki kilit etkinliğinde sayılmaz). Ağ, görsel aracı ya da
ses aracı gerekmez. Demo kaynak dosyaları (senaryo.json, brief.md, hazirla.py) her çalıştırmada yenilenir.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

STUDYO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))   # eklenti içi
sys.path.insert(0, os.path.join(STUDYO, "motor"))
import ayar  # noqa: E402

DEMO_ID = "0000-00-00_demo"
KAYNAK = os.path.join(ayar.eklenti_kok(), "ornek", "demo")
SABLON_RENDER = os.path.join(STUDYO, "sablon", "render.py")


def ortam():
    env = dict(os.environ)
    env["MA_KOK"] = ayar.kok()
    env["MA_EKLENTI"] = ayar.eklenti_kok()
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def calis(ad, args, cwd):
    print(f"\n-- {ad}", flush=True)
    p = subprocess.run([sys.executable, *args], cwd=cwd, env=ortam())
    if p.returncode:
        print(f"[HATA] {ad} (çıkış {p.returncode})")
    return p.returncode


def hazirla(sessiz=False):
    """Demo projesini kurar (kopya + durum dosyaları + render.py). -> proje klasörü"""
    hedef = ayar.yol("sirket", "projeler", DEMO_ID)
    for alt in ("cizim/ham", "cizim/hazir", "ses/ham", "ses/parcalar", "animasyon", "cikti"):
        os.makedirs(os.path.join(hedef, alt), exist_ok=True)
    for ad in os.listdir(KAYNAK):
        k = os.path.join(KAYNAK, ad)
        if os.path.isfile(k):
            shutil.copy2(k, os.path.join(hedef, ad))
    shutil.copy2(SABLON_RENDER, os.path.join(hedef, "animasyon", "render.py"))
    simdi = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
    if not os.path.exists(os.path.join(hedef, "durum.json")):
        durum = {"id": DEMO_ID, "baslik": "Demo: Ay neden hep aynı yüzünü gösterir? (motor testi ve örnek proje)",
                 "format": "monolog", "senaryo_modu": "ajan", "asama": "demo", "olusturma": simdi,
                 "kullanici_bekleniyor": False, "bekleyen_onay": None,
                 "revizyon": {"senaryo": 0, "gorsel": 0, "ses": 0, "animasyon": 0},
                 "gecmis": [{"zaman": simdi, "asama": "demo", "not": "Motor ve araçların çevrimdışı uçtan uca testi"}]}
        with open(os.path.join(hedef, "durum.json"), "w", encoding="utf-8") as f:
            json.dump(durum, f, ensure_ascii=False, indent=2)
    for ad, bas in (("gunluk.md", f"# Günlük — {DEMO_ID}\n\n"), ("talepler.md", f"# Talepler — {DEMO_ID}\n\n")):
        if not os.path.exists(os.path.join(hedef, ad)):
            with open(os.path.join(hedef, ad), "w", encoding="utf-8") as f:
                f.write(bas)
    if not sessiz:
        print("demo projesi:", hedef)
    return hedef


def varliklar(hedef):
    """Görseller + taslak ses (render öncesi her şey). -> hata sayısı"""
    hata = calis("görseller (hazirla.py)", [os.path.join(hedef, "hazirla.py"), hedef], hedef)
    hata += calis("taslak ses", [os.path.join(STUDYO, "motor", "taslak_ses.py"), hedef, "--zorla"], hedef)
    return hata


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kareler", action="store_true", help="tam render yerine kontrol kareleri")
    a = ap.parse_args()
    hedef = hazirla()
    hata = varliklar(hedef)
    render = os.path.join(hedef, "animasyon", "render.py")
    kontrol = os.path.join(STUDYO, "araclar", "kontrol.py")
    hata += calis("senaryo kontrolü", [kontrol, hedef, "--senaryo"], hedef)
    if hata:
        print("\nDemo yarıda kaldı: yukarıdaki hatalara bakın (ma doktor).")
        return 1
    if a.kareler:
        hata += calis("kontrol kareleri", [render, "--kareler", "otomatik"], hedef)
        print(f"\nKareler: {os.path.join(hedef, 'animasyon', 'kareler')}")
        return 1 if hata else 0
    hata += calis("render", [render], hedef)
    mp4 = os.path.join(hedef, "cikti", DEMO_ID + ".mp4")
    hata += calis("video kontrolü", [kontrol, hedef], hedef)
    print(f"\nDemo videosu: {mp4}" if os.path.exists(mp4) else "\nDemo videosu üretilemedi.")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
