"""Ses aracından (ör. ElevenLabs) inen sesi senaryo satırlarına böler -> ses/parcalar/NN_<konusan>.wav + ses/zamanlama.json

  ma ses-bol <proje> --girdi ses/ham/kasif_tum.mp3 --konusan kasif
  ma ses-bol <proje> --girdi ses/ham/satir04.mp3 --satir 4
  ma ses-bol <proje> --girdi ses/ham/x.mp3 --konusan kasif --sinirlar     (sadece analiz)
  ma ses-bol <proje> --girdi ses/ham/x.mp3 --konusan kasif --elle 3.42,7.10,9.85

Konuşanın senaryodaki satır sayısı kadar parçaya, en uzun iç duraklamalardan böler. Her parçanın sesli kısmı
kırpılır, seviyesi eşitlenir. Beklenen süreden (ayarlar -> icerik.konusma_hizi_kar_sn, dile göre) çok sapan
parçalar için UYARI basar. Gerçek ses gelmeden kurguyu denemek için: ma taslak-ses <proje>.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "motor"))  # eklenti içi
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ayar  # noqa: E402
import ses_araclari as A  # noqa: E402
from proje import bul  # noqa: E402

HIZ = ayar.konusma_hizi()  # karakter/sn (dile ve ayara göre; etiketsiz metin)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("proje")
    ap.add_argument("--girdi", required=True)
    ap.add_argument("--konusan")
    ap.add_argument("--satir", type=int)
    ap.add_argument("--elle")
    ap.add_argument("--sinirlar", action="store_true")
    a = ap.parse_args()

    d = bul(a.proje)
    with open(os.path.join(d, "senaryo.json"), encoding="utf-8") as f:
        sen = json.load(f)
    satirlar = sorted(sen["satirlar"], key=lambda s: s["no"])
    if a.satir:
        hedef = [s for s in satirlar if s["no"] == a.satir]
    elif a.konusan:
        hedef = [s for s in satirlar if s["konusan"] == a.konusan]
    else:
        sys.exit("--konusan ya da --satir gerekli")
    if not hedef:
        sys.exit("Senaryoda eşleşen satır yok.")

    girdi = a.girdi if os.path.isabs(a.girdi) else os.path.join(d, a.girdi)
    x = A.yukle(girdi)
    print(f"girdi: {os.path.basename(girdi)}  {A.sure(x):.2f} sn, {len(hedef)} satır")

    if a.sinirlar:
        print("Sessizlikler (bas-bit, süre):")
        for s, e in A.sessizlikler(x):
            print(f"  {s:6.2f} - {e:6.2f}  ({e - s:.2f})")
        try:
            for i, (s, e) in enumerate(A.bol(x, len(hedef))):
                print(f"  otomatik parça {i + 1}: {s:.2f}-{e:.2f}")
        except ValueError as e:
            print("  ", e)
        return

    elle = [float(v) for v in a.elle.split(",")] if a.elle else None
    try:
        araliklar = A.bol(x, len(hedef), elle=elle)
    except ValueError as e:
        sys.exit(f"HATA: {e}")

    pdir = os.path.join(d, "ses", "parcalar")
    os.makedirs(pdir, exist_ok=True)
    zyol = os.path.join(d, "ses", "zamanlama.json")
    zam = {"parcalar": []}
    if os.path.exists(zyol):
        with open(zyol, encoding="utf-8") as f:
            zam = json.load(f)
    nolar = {s["no"] for s in hedef}
    zam["parcalar"] = [p for p in zam.get("parcalar", []) if p["satir"] not in nolar]

    uyari = 0
    for s, (bas, bit) in zip(hedef, araliklar):
        parca = A.seviye_esitle(A.kes(x, bas, bit))
        ad = f"{s['no']:02d}_{s['konusan']}.wav"
        A.kaydet(os.path.join(pdir, ad), parca)
        sure = A.sure(parca)
        beklenen = max(0.5, len(s["metin"]) / HIZ)
        oran = sure / beklenen
        isaret = ""
        if (oran < 0.6 or oran > 1.6) and abs(sure - beklenen) > 0.7:
            isaret = "  <-- UYARI: beklenenden çok farklı (yanlış bölme / atlanan kelime?)"
            uyari += 1
        print(f"  {ad:<26} {bas:6.2f}-{bit:6.2f}  {sure:5.2f} sn (beklenen ~{beklenen:.1f})  '{s['metin'][:40]}'{isaret}")
        zam["parcalar"].append({"satir": s["no"], "konusan": s["konusan"], "dosya": f"parcalar/{ad}",
                                "sure": round(sure, 3), "kaynak": os.path.relpath(girdi, d).replace("\\", "/"),
                                "kaynak_bas": round(bas, 3), "kaynak_bit": round(bit, 3)})
    zam["parcalar"].sort(key=lambda p: p["satir"])
    zam["toplam_konusma_sn"] = round(sum(p["sure"] for p in zam["parcalar"]), 2)
    with open(zyol, "w", encoding="utf-8") as f:
        json.dump(zam, f, ensure_ascii=False, indent=2)
    eksik = sorted({s["no"] for s in satirlar} - {p["satir"] for p in zam["parcalar"]})
    print(f"zamanlama.json güncellendi. Toplam konuşma {zam['toplam_konusma_sn']} sn."
          + (f" Sesi olmayan satırlar: {eksik}" if eksik else " Tüm satırların sesi var."))
    if uyari:
        print(f"{uyari} parça şüpheli: --sinirlar ile duraklamalara bak, gerekirse --elle ile kesim noktası ver.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
