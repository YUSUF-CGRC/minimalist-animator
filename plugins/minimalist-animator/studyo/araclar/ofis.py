"""Ofis paneli konuşmaları: kullanıcının panelden ajanlara yazdığı mesajlar ve cevaplar.

Her ajanın konuşması proje kökünde `sirket/kullanici/sohbet/<ajan>.jsonl` dosyasında, satır başına bir mesaj:
{"zaman": "2026-10-21T01:05", "kim": "kullanici" | "<ajan>" | "yonetici", "metin": "..."}
Ofis paneli bu dosyaları okur; kullanıcının mesajını panel kendisi yazar. "kim" alanı ajan adı olmayan her mesaj
(eski kayıtlarda kullanıcının adı) kullanıcı mesajı sayılır.

  ma ofis yanit cizer "Not aldım, bir dahakine kubbeyi büyük çizeceğim."
  ma ofis yanit cizer "..." --kim yonetici   # Yönetici'nin araya girdiği not
  ma ofis mesaj cizer "..."                  # kullanıcı adına (deneme için)
  ma ofis oku cizer [--son 10]
  ma ofis bekleyen                           # cevapsız kalan kullanıcı mesajları
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "motor"))  # eklenti içi
import ayar  # noqa: E402

KOK = ayar.kok()
KLASOR = os.path.join(KOK, "sirket", "kullanici", "sohbet")
AJANLAR = ["yonetici", "analist", "arastirmaci", "senarist", "cizer", "seslendirmen", "animator"]
KULLANICI = "kullanici"


def yol(ajan):
    return os.path.join(KLASOR, f"{ajan}.jsonl")


def kullanici_mi(kim):
    return kim not in AJANLAR


def oku(ajan):
    if not os.path.exists(yol(ajan)):
        return []
    mesajlar = []
    with open(yol(ajan), encoding="utf-8") as f:
        for satir in f:
            satir = satir.strip()
            if satir:
                try:
                    mesajlar.append(json.loads(satir))
                except json.JSONDecodeError:
                    pass
    return mesajlar


def ekle(ajan, kim, metin):
    os.makedirs(KLASOR, exist_ok=True)
    kayit = {"zaman": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M"), "kim": kim, "metin": metin.strip()}
    with open(yol(ajan), "a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    return kayit


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = ap.add_subparsers(dest="komut", required=True)
    p = alt.add_parser("yanit"); p.add_argument("ajan", choices=AJANLAR); p.add_argument("metin"); p.add_argument("--kim")
    p = alt.add_parser("mesaj"); p.add_argument("ajan", choices=AJANLAR); p.add_argument("metin")
    p = alt.add_parser("oku"); p.add_argument("ajan", choices=AJANLAR); p.add_argument("--son", type=int, default=10)
    alt.add_parser("bekleyen")
    a = ap.parse_args()

    if a.komut == "yanit":
        k = ekle(a.ajan, a.kim or a.ajan, a.metin)
        print(f"yazıldı: {a.ajan} ← {k['kim']} ({k['zaman']})")
    elif a.komut == "mesaj":
        k = ekle(a.ajan, KULLANICI, a.metin)
        print(f"yazıldı: {ayar.kullanici()} → {a.ajan} ({k['zaman']})")
    elif a.komut == "oku":
        for m in oku(a.ajan)[-a.son:]:
            kim = ayar.kullanici() if kullanici_mi(m.get("kim")) else m.get("kim")
            print(f"{m['zaman']}  {kim:>12}: {m['metin']}")
    elif a.komut == "bekleyen":
        bos = True
        for ajan in AJANLAR:
            mesajlar = oku(ajan)
            if mesajlar and kullanici_mi(mesajlar[-1].get("kim")):
                bos = False
                print(f"{ajan}: {mesajlar[-1]['zaman']}  {mesajlar[-1]['metin']}")
        if bos:
            print("cevapsız mesaj yok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
