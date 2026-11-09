"""Proje (video/gönderi) klasörü ve durum takibi. Projeler proje kökünde: sirket/projeler/<tarih>_<slug>/

  ma proje yeni ay-yuzu "Ay neden hep aynı yüzünü gösterir?" [--format monolog] [--tarih 2026-10-19]
  ma proje yeni ay-yuzu "..." --mod kendi-aynen --metin metnim.md     -> kullanıcının metni aynen kullanılır
  ma proje asama <proje> senaryo "Araştırma KK'dan geçti"
  ma proje bekle <proje> "9 dosya indirme onayı"      -> kullanıcı bekleniyor
  ma proje devam <proje> "onaylandı"                  -> bekleme kalkar
  ma proje revizyon <proje> gorsel
  ma proje gunluk <proje> "Çizer: 3 görsel hazır" [--kim cizer]
  ma proje pano                                        -> tüm projelerin özeti
<proje>: klasör yolu, klasör adı ya da adın benzersiz bir parçası (ör. "ay-yuzu").

Senaryo modları (--mod; varsayılan ayarlar.json -> akis.varsayilan_senaryo_modu):
  ajan           konuyu ekip araştırır, metni Senarist yazar
  kendi-arastir  kullanıcının metni/notları temeldir; ekip bilgileri doğrular, senaryoyu buna göre yazar
  kendi-duzenle  kullanıcının metni temeldir; Senarist akış ve süre için düzenler, anlamı korur
  kendi-aynen    kullanıcının metni sözcüğü sözcüğüne kullanılır; ekip yalnızca sahneler ve görselleri ekler
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "motor"))  # eklenti içi
import ayar  # noqa: E402

KOK = ayar.kok()
PROJELER = os.path.join(KOK, "sirket", "projeler")
GELEN_KUTUSU = os.path.join(KOK, "sirket", "kullanici")
ASAMALAR = ["brief", "arastirma", "senaryo", "senaryo-kontrol", "gorsel-hazirlik", "ses-hazirlik", "indirme-onayi",
            "indirme-isleme", "animasyon", "son-kontrol", "kullanici-onayi", "revizyon", "tamam", "yayinlandi", "iptal",
            "demo"]
BITMIS = {"tamam", "yayinlandi", "iptal", "demo"}
FORMATLAR = ["monolog", "zaman-yolcusu", "biliyor-muydun", "post-carousel", "post-karikatur"]
MODLAR = {
    "ajan": "konuyu ekip araştırır, metni Senarist yazar",
    "kendi-arastir": "kullanıcının metni/notları temeldir; ekip bilgileri doğrular, senaryoyu buna göre yazar",
    "kendi-duzenle": "kullanıcının metni temeldir; Senarist akış ve süre için düzenler, anlamı korur",
    "kendi-aynen": "kullanıcının metni sözcüğü sözcüğüne kullanılır; ekip yalnızca sahneleri ve görselleri ekler",
}
METIN_DOSYASI = "kullanici-metni.md"
SURE = {"monolog": "30–35 sn", "zaman-yolcusu": "30–40 sn", "biliyor-muydun": "12–18 sn", "post-carousel": "5–7 kare",
        "post-karikatur": "1–4 panel"}

BRIEF = """# Brief — {baslik}

- **Proje:** {id}
- **Format:** {format}
- **Senaryo modu:** {mod} — {mod_aciklama}{metin_satiri}
- **Hedef süre:** {sure}
- **Neden bu konu, neden şimdi:** (fikir havuzu / analiz / özel gün / kullanıcının isteği)
- **Hedef duygu:** (ör. merak → şaşkınlık → "bunu birine göstermeliyim")
- **Hook fikri:** (ilk 1.5 sn'de ne söylenecek / görünecek)
- **Anlatılacak 3 şey:**
  1.
  2.
  3.
- **Kaçınılacaklar:** (doğrulanmamış iddialar, abartı, önceki içerikle tekrar)
- **Arşivden kullanılabilecekler:** (ma envanter ara ...)
- **Kapanış çağrısı:**
"""


def simdi():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")


def bul(p):
    if os.path.isdir(p) and os.path.exists(os.path.join(p, "durum.json")):
        return os.path.abspath(p)
    if not os.path.isdir(PROJELER):
        sys.exit(f"Proje klasörü yok: {PROJELER} (önce: ma kurulum)")
    adaylar = [x for x in os.listdir(PROJELER) if p in x and os.path.isdir(os.path.join(PROJELER, x))]
    if len(adaylar) == 1:
        return os.path.join(PROJELER, adaylar[0])
    tam = [x for x in adaylar if x == p or x.endswith("_" + p)]
    if len(tam) == 1:
        return os.path.join(PROJELER, tam[0])
    sys.exit(f"Proje bulunamadı ya da birden fazla eşleşti: '{p}' -> {adaylar}")


def asama_adi(a):
    """Eski '<ad>-onayi' aşamalarını 'kullanici-onayi' kabul eder."""
    if a not in ASAMALAR and re.fullmatch(r"[a-z]+-onayi", a or ""):
        return "kullanici-onayi"
    return a


def _eski_adlar(durum):
    """Eski durum.json alanlarını yeni adlara çevirir (<ad>_bekleniyor -> kullanici_bekleniyor, <ad>-onayi aşaması)."""
    for k in [k for k in durum if re.fullmatch(r"[a-z]+_bekleniyor", k) and k != "kullanici_bekleniyor"]:
        v = durum.pop(k)
        durum.setdefault("kullanici_bekleniyor", v)
    durum.setdefault("kullanici_bekleniyor", False)
    durum["asama"] = asama_adi(durum.get("asama", "brief"))
    for g in durum.get("gecmis", []):
        g["asama"] = asama_adi(g.get("asama", ""))
    return durum


def oku(d):
    with open(os.path.join(d, "durum.json"), encoding="utf-8") as f:
        return _eski_adlar(json.load(f))


def yaz(d, durum):
    with open(os.path.join(d, "durum.json"), "w", encoding="utf-8") as f:
        json.dump(durum, f, ensure_ascii=False, indent=2)


def gunluge(d, metin, kim="yonetici"):
    with open(os.path.join(d, "gunluk.md"), "a", encoding="utf-8") as f:
        f.write(f"- {simdi()} **{kim}**: {metin}\n")


def sha256(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 16), b""):
            h.update(parca)
    return h.hexdigest()


def cmd_yeni(a):
    if not re.fullmatch(r"[a-z0-9-]+", a.slug):
        sys.exit("slug yalnızca küçük harf, rakam ve tire: ay-yuzu")
    mod = a.mod or str(ayar.al("akis.varsayilan_senaryo_modu", "ajan") or "ajan")
    if mod not in MODLAR:
        sys.exit(f"Geçersiz senaryo modu '{mod}' (akis.varsayilan_senaryo_modu?). Geçerli: {', '.join(MODLAR)}")
    if a.metin and not os.path.isfile(a.metin):
        sys.exit(f"Metin dosyası yok: {a.metin}")
    tarih = a.tarih or datetime.date.today().isoformat()
    pid = f"{tarih}_{a.slug}"
    d = os.path.join(PROJELER, pid)
    if os.path.exists(d):
        sys.exit(f"Zaten var: {d}")
    for alt in ("cizim/ham", "cizim/hazir", "ses/ham", "ses/parcalar", "animasyon", "cikti"):
        os.makedirs(os.path.join(d, alt), exist_ok=True)
    durum = {"id": pid, "baslik": a.baslik, "format": a.format, "senaryo_modu": mod, "asama": "brief",
             "olusturma": simdi(), "kullanici_bekleniyor": False, "bekleyen_onay": None,
             "revizyon": {"senaryo": 0, "gorsel": 0, "ses": 0, "animasyon": 0},
             "gecmis": [{"zaman": simdi(), "asama": "brief", "not": "Proje açıldı"}]}
    metin_satiri = ""
    if a.metin:
        hedef = os.path.join(d, METIN_DOSYASI)
        shutil.copyfile(a.metin, hedef)
        durum["kullanici_metni"] = {"dosya": METIN_DOSYASI, "sha256": sha256(hedef)}
        metin_satiri = f"\n- **Kullanıcı metni:** `{METIN_DOSYASI}`" + (" (aynen kullanılır)" if mod == "kendi-aynen" else "")
    elif mod.startswith("kendi-"):
        metin_satiri = f"\n- **Kullanıcı metni:** henüz yok — `{METIN_DOSYASI}` olarak eklenecek"
        print(f"UYARI: '{mod}' modunda kullanıcı metni verilmedi; proje klasörüne {METIN_DOSYASI} eklenmeli "
              "(ya da --metin <dosya>).", file=sys.stderr)
    yaz(d, durum)
    with open(os.path.join(d, "brief.md"), "w", encoding="utf-8") as f:
        f.write(BRIEF.format(baslik=a.baslik, id=pid, format=a.format, mod=mod, mod_aciklama=MODLAR[mod],
                             metin_satiri=metin_satiri, sure=SURE.get(a.format, "30–35 sn")))
    with open(os.path.join(d, "talepler.md"), "w", encoding="utf-8") as f:
        f.write(f"# Talepler — {pid}\n\nFormat: eklentideki `protokoller/iletisim.md`\n\n")
    with open(os.path.join(d, "gunluk.md"), "w", encoding="utf-8") as f:
        f.write(f"# Günlük — {pid}\n\n")
    gunluge(d, f"Proje açıldı (format {a.format}, senaryo modu {mod}" + (", kullanıcı metni eklendi)" if a.metin else ")"))
    print(os.path.relpath(d, KOK).replace("\\", "/"))


def cmd_asama(a):
    asama = asama_adi(a.asama)
    if asama not in ASAMALAR:
        sys.exit(f"Geçersiz aşama '{a.asama}'. Geçerli: {', '.join(ASAMALAR)}")
    d = bul(a.proje)
    durum = oku(d)
    durum["asama"] = asama
    durum["gecmis"].append({"zaman": simdi(), "asama": asama, "not": a.not_ or ""})
    yaz(d, durum)
    gunluge(d, f"Aşama → {asama}. {a.not_ or ''}")
    print(f"{durum['id']}: {asama}")


def cmd_bekle(a):
    d = bul(a.proje)
    durum = oku(d)
    durum["kullanici_bekleniyor"] = True
    durum["bekleyen_onay"] = {"ne": a.ne, "zaman": simdi()}
    yaz(d, durum)
    gunluge(d, f"{ayar.kullanici()} bekleniyor: {a.ne}")
    print(f"{durum['id']}: {ayar.kullanici()} bekleniyor — {a.ne}")


def cmd_devam(a):
    d = bul(a.proje)
    durum = oku(d)
    durum["kullanici_bekleniyor"] = False
    eski = durum.get("bekleyen_onay")
    durum["bekleyen_onay"] = None
    durum["gecmis"].append({"zaman": simdi(), "asama": durum["asama"],
                            "not": f"{ayar.kullanici()} yanıtladı: {a.not_ or ''}"})
    yaz(d, durum)
    gunluge(d, f"{ayar.kullanici()} yanıtladı ({(eski or {}).get('ne', '')}): {a.not_ or ''}")
    print(f"{durum['id']}: devam")


def cmd_revizyon(a):
    d = bul(a.proje)
    durum = oku(d)
    durum["revizyon"][a.alan] = durum["revizyon"].get(a.alan, 0) + 1
    yaz(d, durum)
    n = durum["revizyon"][a.alan]
    gunluge(d, f"{a.alan} revizyonu #{n}")
    print(f"{a.alan} revizyonu #{n}" + (f"  -> 3. tur: sonuç alınamazsa kullanıcıya ({ayar.kullanici()}) sor"
                                        if n >= 3 else ""))


def cmd_gunluk(a):
    d = bul(a.proje)
    gunluge(d, a.metin, a.kim)


def acik_talep_sayisi(d):
    y = os.path.join(d, "talepler.md")
    if not os.path.exists(y):
        return 0
    with open(y, encoding="utf-8") as f:
        return sum(1 for ln in f if ln.startswith("### ") and ("| ACIK" in ln or "| ILETILDI" in ln))


def pano():
    if not os.path.isdir(PROJELER):
        print("Proje yok.")
        return
    satirlar = []
    for x in sorted(os.listdir(PROJELER)):
        d = os.path.join(PROJELER, x)
        if not os.path.exists(os.path.join(d, "durum.json")):
            continue
        du = oku(d)
        satirlar.append((du, d))
    acik = [(du, d) for du, d in satirlar if du["asama"] not in BITMIS]
    print(f"Açık proje: {len(acik)} | Toplam: {len(satirlar)}\n")
    for du, d in satirlar:
        bek = (f"  ⏳ {ayar.buyuk(ayar.kullanici())}: {du['bekleyen_onay']['ne']}"
               if du.get("kullanici_bekleniyor") and du.get("bekleyen_onay") else "")
        tal = acik_talep_sayisi(d)
        tal = f"  📨 {tal} açık talep" if tal else ""
        son = du["gecmis"][-1]["zaman"] if du.get("gecmis") else ""
        mod = du.get("senaryo_modu", "ajan")
        mod = f" [{mod}]" if mod != "ajan" else ""
        print(f"- {du['id']:<38} {du['asama']:<16} (son: {son}){mod}{bek}{tal}")
    ozet = os.path.join(GELEN_KUTUSU, "onay-bekleyenler.md")
    if os.path.exists(ozet):
        print(f"\nGelen kutusu ({ayar.kullanici()}): {os.path.relpath(ozet, KOK)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = ap.add_subparsers(dest="komut", required=True)
    p = alt.add_parser("yeni"); p.add_argument("slug"); p.add_argument("baslik")
    p.add_argument("--format", default="monolog", choices=FORMATLAR); p.add_argument("--tarih")
    p.add_argument("--mod", choices=list(MODLAR), help="senaryo modu (varsayılan: akis.varsayilan_senaryo_modu)")
    p.add_argument("--metin", help=f"kullanıcının metin dosyası -> <proje>/{METIN_DOSYASI}")
    p.set_defaults(f=cmd_yeni)
    p = alt.add_parser("asama"); p.add_argument("proje"); p.add_argument("asama"); p.add_argument("not_", nargs="?")
    p.set_defaults(f=cmd_asama)
    p = alt.add_parser("bekle"); p.add_argument("proje"); p.add_argument("ne"); p.set_defaults(f=cmd_bekle)
    p = alt.add_parser("devam"); p.add_argument("proje"); p.add_argument("not_", nargs="?"); p.set_defaults(f=cmd_devam)
    p = alt.add_parser("revizyon"); p.add_argument("proje"); p.add_argument("alan"); p.set_defaults(f=cmd_revizyon)
    p = alt.add_parser("gunluk"); p.add_argument("proje"); p.add_argument("metin"); p.add_argument("--kim", default="yonetici")
    p.set_defaults(f=cmd_gunluk)
    p = alt.add_parser("pano"); p.set_defaults(f=lambda a: pano())
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
