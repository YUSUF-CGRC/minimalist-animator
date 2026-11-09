"""<PROJE> animasyonu — Animatör bu şablonu sirket/projeler/<proje>/animasyon/render.py olarak kopyalar
(ma render <proje> yoksa kendisi kopyalar).

  ma render <proje> --bilgi              -> satır zamanlamaları
  ma render <proje> --kareler otomatik   -> animasyon/kareler/ altına kontrol kareleri
  ma render <proje> --kareler 1.2,7.5    -> seçili saniyeler
  ma render <proje> --kapak 3.2          -> cikti/kapak.png
  ma render <proje>                      -> cikti/<proje>.mp4
Motor API: eklentideki studyo/motor/KURGU-REHBERI.md. Doğrudan "python animasyon/render.py" da çalışır: motor
klasörü MA_EKLENTI / CLAUDE_PLUGIN_ROOT ortam değişkeninden ya da proje kökündeki sirket/.eklenti dosyasından bulunur.
"""
import json
import os
import sys

PROJE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _eklenti():
    adaylar = [os.environ.get("MA_EKLENTI"), os.environ.get("CLAUDE_PLUGIN_ROOT")]
    d = PROJE
    while True:                       # proje kökü: "_tur" işaretli ayarlar.json'un olduğu klasör
        try:
            with open(os.path.join(d, "ayarlar.json"), encoding="utf-8") as f:
                isaretli = json.load(f).get("_tur") == "minimalist-animator"
        except (OSError, ValueError, AttributeError):
            isaretli = False
        if isaretli:
            os.environ.setdefault("MA_KOK", d)
            try:
                with open(os.path.join(d, "sirket", ".eklenti"), encoding="utf-8") as g:
                    adaylar.append(g.read().strip())
            except OSError:
                pass
            break
        ust = os.path.dirname(d)
        if ust == d:
            break
        d = ust
    for a in adaylar:
        if a and os.path.isfile(os.path.join(a, "studyo", "motor", "kurgu.py")):
            return a
    sys.exit("Motor bulunamadı: 'ma render <proje>' ile çalıştırın (ya da MA_EKLENTI=<eklenti klasörü>).")


sys.path.insert(0, os.path.join(_eklenti(), "studyo", "motor"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kurgu import Video  # noqa: E402

v = Video(PROJE)
v.ses_hatti()             # ses/zamanlama.json -> satırlar zaman çizelgesine (bosluk=0.28 varsayılan)
v.otomatik_kurgu()        # senaryo.json "ekranda" olayları

# ---- ince ayar: otomatik kurgunun üstüne projeye özel dokunuşlar ----
# s = v.satir
# k = v.karakterler["<karakter-id>"]
# k.zipla(s(3).kelime("Ay"))
# v.parilti(s(4).bit - 0.2, 540, 700)
# from ozel import ciz_yildizlar; v.ozel(ciz_yildizlar, z=15, t0=s(2).bas, t1=s(2).bit)

v.calistir()
