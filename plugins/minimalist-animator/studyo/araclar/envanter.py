"""Arşiv envanteri: çizilmiş görseller, ses kimlikleri, işlenmiş konular.

  ma envanter ara ay dünya               -> arşivde ara (yeni çizimden ÖNCE zorunlu)
  ma envanter listele [--tur karakter]
  ma envanter kullan kasif <proje>        -> dekupe dosyaları projenin cizim/hazir klasörüne kopyalar
  ma envanter ekle --tur karakter --id kasif --varyant acik --dosya <ham> --dekupe <png> \
         --proje <proje> --prompt "..." --kaynak "<görsel aracı sohbet linki>" [--ad "Kaşif"] [--aciklama ...] [--etiket a,b]
  ma envanter ses kasif                   -> ses kimliğini göster
  ma envanter ses-ornek kasif <dosya>
  ma envanter konu-ara ay
  ma envanter konu-ekle --id ay-yuzu --baslik "..." --proje <proje> --durum uretildi
Arşiv proje kökünde: sirket/arsiv/ (gorsel-envanteri.json, ses-kimlikleri.json, islenen-konular.json).
"""
import argparse
import datetime
import json
import os
import shutil
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "motor"))  # eklenti içi
import ayar  # noqa: E402

KOK = ayar.kok()
ARSIV = os.path.join(KOK, "sirket", "arsiv")
GORSEL = os.path.join(ARSIV, "gorsel-envanteri.json")
SES = os.path.join(ARSIV, "ses-kimlikleri.json")
KONU = os.path.join(ARSIV, "islenen-konular.json")
KLASOR = {"karakter": "karakterler", "nesne": "nesneler", "arka-plan": "arka-planlar"}


def rel(p):
    return os.path.relpath(p, KOK).replace("\\", "/")


def absol(p):
    return p if os.path.isabs(p) else os.path.join(KOK, p)


def oku(yol, bos):
    if os.path.exists(yol):
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    return bos


def yaz(yol, veri):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def norm(s):
    """Arama için: küçük harf (dile göre), aksanlar atılır (ç->c, ı->i, é->e)."""
    s = ayar.kucuk(str(s)).replace("ı", "i")
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))
    return "".join(ch if ch.isalnum() else " " for ch in s)


def proje_yolu(p):
    if os.path.isdir(p):
        return os.path.abspath(p)
    d = os.path.join(KOK, "sirket", "projeler")
    adaylar = [x for x in os.listdir(d) if p in x]
    if len(adaylar) == 1:
        return os.path.join(d, adaylar[0])
    sys.exit(f"Proje bulunamadı/çok anlamlı: {p} -> {adaylar}")


def bugun():
    return datetime.date.today().isoformat()


# ------------------------------------------------------------------ görseller
def cmd_ara(a):
    env = oku(GORSEL, {"ogeler": []})
    terimler = [norm(t).strip() for t in a.terim]
    bulunan = []
    for o in env["ogeler"]:
        metin = norm(" ".join([o["id"], o.get("ad", ""), o.get("aciklama", ""), " ".join(o.get("etiketler", []))]))
        puan = sum(1 for t in terimler if t and t in metin)
        if puan:
            bulunan.append((puan, o))
    if not bulunan:
        print("Arşivde eşleşme yok -> yeni çizim gerekebilir:", " ".join(a.terim))
        return
    bulunan.sort(key=lambda x: -x[0])
    for puan, o in bulunan:
        print(f"[{o['tur']}] {o['id']} — {o.get('ad', '')}  (puan {puan})")
        if o.get("aciklama"):
            print(f"    {o['aciklama']}")
        for v, d in o.get("varyantlar", {}).items():
            print(f"    varyant {v}: dekupe={d.get('dekupe')}  ham={d.get('ham')}")
        print(f"    projeler: {', '.join(o.get('projeler', [])) or '-'}")


def cmd_listele(a):
    env = oku(GORSEL, {"ogeler": []})
    for o in env["ogeler"]:
        if a.tur and o["tur"] != a.tur:
            continue
        print(f"[{o['tur']}] {o['id']:<28} varyantlar: {', '.join(o.get('varyantlar', {}))}  ({o.get('tarih', '')})")


def cmd_ekle(a):
    env = oku(GORSEL, {"ogeler": []})
    o = next((x for x in env["ogeler"] if x["id"] == a.id), None)
    if o is None:
        o = {"id": a.id, "tur": a.tur, "ad": a.ad or a.id, "aciklama": a.aciklama or "",
             "etiketler": [e.strip() for e in (a.etiket or "").split(",") if e.strip()], "varyantlar": {},
             "prompt": "", "kaynak": "", "tarih": bugun(), "projeler": [], "not": ""}
        env["ogeler"].append(o)
    varyant = a.varyant or ("acik" if a.tur == "karakter" else "ana")
    if varyant in o["varyantlar"] and not a.uzerine:
        sys.exit(f"{a.id}/{varyant} zaten arşivde. Değiştirmek kritik bir karar olabilir; gerekiyorsa --uzerine.")
    hedef = os.path.join(ARSIV, KLASOR[a.tur], a.id)
    os.makedirs(hedef, exist_ok=True)
    kayit = {}
    if a.dosya:
        uz = os.path.splitext(a.dosya)[1].lower()
        y = os.path.join(hedef, f"{a.id}_{varyant}_ham{uz}")
        shutil.copy2(absol(a.dosya), y)
        kayit["ham"] = rel(y)
    if a.dekupe:
        ad = f"{a.id}.png" if varyant == "ana" else f"{a.id}_{varyant}.png"
        y = os.path.join(hedef, ad)
        shutil.copy2(absol(a.dekupe), y)
        kayit["dekupe"] = rel(y)
    o["varyantlar"][varyant] = kayit
    for alan in ("ad", "aciklama", "prompt", "kaynak"):
        if getattr(a, alan):
            o[alan] = getattr(a, alan)
    if a.etiket:
        o["etiketler"] = sorted(set(o.get("etiketler", []) + [e.strip() for e in a.etiket.split(",") if e.strip()]))
    if a.proje:
        pid = os.path.basename(proje_yolu(a.proje))
        if pid not in o["projeler"]:
            o["projeler"].append(pid)
    yaz(GORSEL, env)
    print(f"arşive eklendi: {a.id}/{varyant} -> {kayit}")


def cmd_kullan(a):
    env = oku(GORSEL, {"ogeler": []})
    o = next((x for x in env["ogeler"] if x["id"] == a.id), None)
    if o is None:
        sys.exit(f"Arşivde yok: {a.id}  (envanter.py ara ile bak)")
    pd = proje_yolu(a.proje)
    hazir = os.path.join(pd, "cizim", "hazir")
    os.makedirs(hazir, exist_ok=True)
    for v, d in o["varyantlar"].items():
        if not d.get("dekupe"):
            print(f"  {v}: dekupe dosyası yok, atlandı")
            continue
        ad = f"{a.id}.png" if v == "ana" else f"{a.id}_{v}.png"
        shutil.copy2(absol(d["dekupe"]), os.path.join(hazir, ad))
        print(f"  {v} -> {rel(os.path.join(hazir, ad))}")
    pid = os.path.basename(pd)
    if pid not in o["projeler"]:
        o["projeler"].append(pid)
        yaz(GORSEL, env)


# ------------------------------------------------------------------ sesler
def cmd_ses(a):
    s = oku(SES, {"karakterler": {}})["karakterler"].get(a.karakter)
    if not s:
        print(f"'{a.karakter}' için ses kimliği yok -> Seslendirmen yeni kimlik önermeli (kritik karar).")
        return
    print(json.dumps(s, ensure_ascii=False, indent=2))


def cmd_ses_ornek(a):
    hedef = os.path.join(ARSIV, "sesler", a.karakter)
    os.makedirs(hedef, exist_ok=True)
    y = os.path.join(hedef, f"{bugun()}_{os.path.basename(a.dosya)}")
    shutil.copy2(absol(a.dosya), y)
    veri = oku(SES, {"karakterler": {}})
    k = veri["karakterler"].get(a.karakter)
    if k is not None:
        k.setdefault("ornekler", []).append(rel(y))
        yaz(SES, veri)
    print("ses örneği arşivlendi:", rel(y))


# ------------------------------------------------------------------ konular
def cmd_konu_ara(a):
    veri = oku(KONU, {"konular": []})
    t = norm(" ".join(a.terim)).strip()
    say = 0
    for k in veri["konular"]:
        if t in norm(" ".join([k["id"], k.get("baslik", ""), k.get("not", "")])):
            print(f"{k['id']} — {k.get('baslik', '')} | {k.get('durum')} | {k.get('format', '')} | {k.get('proje', '')} | {k.get('tarih', '')}")
            say += 1
    if not say:
        print("Bu konu daha önce işlenmemiş:", " ".join(a.terim))


def cmd_konu_ekle(a):
    veri = oku(KONU, {"konular": []})
    pid = os.path.basename(proje_yolu(a.proje)) if a.proje else ""
    k = next((x for x in veri["konular"] if x["id"] == a.id and x.get("proje") == pid), None)
    if k is None:
        k = {"id": a.id, "baslik": a.baslik or a.id, "proje": pid, "tarih": bugun()}
        veri["konular"].append(k)
    for alan in ("baslik", "durum", "format", "not", "link"):
        if getattr(a, alan, None):
            k[alan] = getattr(a, alan)
    yaz(KONU, veri)
    print("konu kaydedildi:", k)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = ap.add_subparsers(dest="komut", required=True)
    p = alt.add_parser("ara"); p.add_argument("terim", nargs="+"); p.set_defaults(f=cmd_ara)
    p = alt.add_parser("listele"); p.add_argument("--tur"); p.set_defaults(f=cmd_listele)
    p = alt.add_parser("ekle")
    p.add_argument("--tur", required=True, choices=list(KLASOR)); p.add_argument("--id", required=True)
    for x in ("varyant", "dosya", "dekupe", "proje", "prompt", "kaynak", "ad", "aciklama", "etiket"):
        p.add_argument("--" + x)
    p.add_argument("--uzerine", action="store_true"); p.set_defaults(f=cmd_ekle)
    p = alt.add_parser("kullan"); p.add_argument("id"); p.add_argument("proje"); p.set_defaults(f=cmd_kullan)
    p = alt.add_parser("ses"); p.add_argument("karakter"); p.set_defaults(f=cmd_ses)
    p = alt.add_parser("ses-ornek"); p.add_argument("karakter"); p.add_argument("dosya"); p.set_defaults(f=cmd_ses_ornek)
    p = alt.add_parser("konu-ara"); p.add_argument("terim", nargs="+"); p.set_defaults(f=cmd_konu_ara)
    p = alt.add_parser("konu-ekle")
    for x in ("id", "baslik", "proje", "durum", "format", "not", "link"):
        p.add_argument("--" + x, required=(x == "id"))
    p.set_defaults(f=cmd_konu_ekle)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
