"""Çalışma kilidi: iki Yönetici oturumunun aynı anda çalışmasını (ve tarayıcıyı paylaşmasını) önler.

  ma kilit durum                       -> çıkış 0: boş (devam edebilirsin), 3: başka oturum çalışıyor
  ma kilit al gunluk-2026-10-21 [--dakika 90]
  ma kilit tazele ["Çizer bitti"]      -> her ajan dönüşünde (kilidin süresini uzatır)
  ma kilit birak                       -> oturum kullanıcıyı beklemeye geçince ya da iş bitince

Kilit "dolu" sayılır: kilit dosyası süresi dolmamışsa VEYA son 45 dakikada sirket/projeler altında bir dosya değiştiyse
(ajanlar çalışırken dosya yazar). İkisi de değilse önceki oturum düşmüş/limit dolmuş kabul edilir ve iş devralınabilir.
"0000-00-00_" önekli projeler (demo) etkinlik sayılmaz.
"""
import argparse
import datetime
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "motor"))  # eklenti içi
import ayar  # noqa: E402

KOK = ayar.kok()
KILIT = os.path.join(KOK, "sirket", ".kilit.json")
PROJELER = os.path.join(KOK, "sirket", "projeler")
ETKINLIK_DK = 45


def simdi():
    return datetime.datetime.now().replace(microsecond=0)


def oku():
    if os.path.exists(KILIT):
        with open(KILIT, encoding="utf-8") as f:
            return json.load(f)
    return None


def yaz(k):
    os.makedirs(os.path.dirname(KILIT), exist_ok=True)
    with open(KILIT, "w", encoding="utf-8") as f:
        json.dump(k, f, ensure_ascii=False, indent=2)


def son_etkinlik():
    """sirket/projeler altındaki en son dosya değişikliği (demo hariç)."""
    en = 0.0
    yol = None
    for kok, dirs, dosyalar in os.walk(PROJELER):
        if "0000-00-00_" in kok:
            continue
        for d in dosyalar:
            y = os.path.join(kok, d)
            try:
                m = os.path.getmtime(y)
            except OSError:
                continue
            if m > en:
                en, yol = m, y
    return en, yol


def durum_hesapla():
    k = oku()
    sebep = []
    if k:
        bitis = datetime.datetime.fromisoformat(k["bitis"])
        if bitis > simdi():
            sebep.append(f"kilit '{k['sahip']}' {bitis:%H:%M}'e kadar geçerli (son not: {k.get('not', '')})")
    m, yol = son_etkinlik()
    if m and time.time() - m < ETKINLIK_DK * 60:
        dk = int((time.time() - m) / 60)
        sebep.append(f"{dk} dk önce proje dosyası değişti ({os.path.relpath(yol, KOK)})")
    return k, sebep


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("durum")
    p = alt.add_parser("al"); p.add_argument("sahip"); p.add_argument("--dakika", type=int, default=90)
    p.add_argument("--zorla", action="store_true")
    p = alt.add_parser("tazele"); p.add_argument("not_", nargs="?", default=""); p.add_argument("--dakika", type=int, default=90)
    alt.add_parser("birak")
    a = ap.parse_args()

    if a.komut == "durum":
        k, sebep = durum_hesapla()
        if sebep:
            print("DOLU — başka bir oturum çalışıyor görünüyor:\n  - " + "\n  - ".join(sebep))
            return 3
        print("BOŞ — çalışan oturum yok" + (f" (son kilit: {k['sahip']}, {k['bitis']})" if k else ""))
        return 0

    if a.komut == "al":
        k, sebep = durum_hesapla()
        if sebep and not a.zorla and not (k and k["sahip"] == a.sahip):
            print("ALINAMADI — " + "; ".join(sebep))
            return 3
        k = {"sahip": a.sahip, "baslangic": simdi().isoformat(), "bitis": (simdi() + datetime.timedelta(minutes=a.dakika)).isoformat(),
             "not": "başladı"}
        yaz(k)
        print(f"kilit alındı: {a.sahip} ({k['bitis']}'e kadar)")
        return 0

    if a.komut == "tazele":
        k = oku()
        if not k:
            print("kilit yok — önce 'al'")
            return 1
        k["bitis"] = (simdi() + datetime.timedelta(minutes=a.dakika)).isoformat()
        k["not"] = a.not_
        yaz(k)
        print(f"kilit tazelendi: {k['sahip']} ({k['bitis']}'e kadar)")
        return 0

    if a.komut == "birak":
        if os.path.exists(KILIT):
            k = oku()
            k["bitis"] = simdi().isoformat()
            k["not"] = "bırakıldı"
            yaz(k)
        print("kilit bırakıldı")
        return 0


if __name__ == "__main__":
    sys.exit(main())
