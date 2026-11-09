"""Teknik kalite kontrol.

  ma kontrol <proje> --senaryo   -> senaryo.json şema ve içerik kontrolü
  ma kontrol <proje> --post      -> post.json şema ve içerik kontrolü
  ma kontrol <proje>             -> cikti/<proje>.mp4 teknik kontrolü
  ma kontrol --video dosya.mp4
Çıkış kodu: 0 temiz, 1 hata var (uyarılar ve bilgi notları hata sayılmaz).

Senaryo modu (durum.json -> senaryo_modu) kontrolü etkiler:
  kendi-aynen  satirlar[].altyazi birleşimi kullanici-metni.md ile sözcük sözcüğe aynı olmalı (büyük/küçük harf,
               noktalama ve boşluk yok sayılır) -> değilse HATA. metin, altyazıdan yalnızca rakam/sembol/kısaltma
               içeren sözcüklerde ayrılabilir ("27" -> "yirmi yedi") -> başka bir sözcükte ayrılırsa HATA.
               Gönderide (--post) her karenin metni kullanici-metni.md'deki "## Kare N" bölümüyle aynı olmalı.
  kendi-*      süre aralığı, kaynak eksikliği ve hook önerisi yalnızca BİLGİ notudur (sonucu etkilemez).
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "motor"))  # eklenti içi
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ayar  # noqa: E402

OLAYLAR = {"karakter-giris", "karakter-git", "karakter-zipla", "karakter-sallan", "karakter-don", "karakter-cik",
           "karakter-goz-kirp", "nesne", "nesne-cik", "etiket", "isim-plakasi", "yil", "konum", "soru-isareti",
           "unlem", "carpi", "dusunce-balonu", "parilti", "buyuk-metin", "arka-plan", "efekt", "ozel"}
POST_TURLERI = {"carousel", "karikatur"}
KARE_ROLLERI = {"kanca", "bilgi", "panel", "kapanis"}
ISARET = re.compile(r"\*\*(.+?)\*\*")
NOKTALAMA = set(".,;:!?…'\"’‘“”«»()[]{}-–—")
METIN_DOSYASI = "kullanici-metni.md"


class Rapor:
    def __init__(self):
        self.hata, self.uyari, self.bilgi = [], [], []

    def h(self, m):
        self.hata.append(m)

    def u(self, m):
        self.uyari.append(m)

    def b(self, m):
        self.bilgi.append(m)

    def bitir(self, baslik):
        print(f"== {baslik} ==")
        for m in self.hata:
            print("  HATA  :", m)
        for m in self.uyari:
            print("  UYARI :", m)
        for m in self.bilgi:
            print("  BİLGİ :", m)
        if not self.hata and not self.uyari:
            print("  Temiz.")
        print(f"  Sonuç: {len(self.hata)} hata, {len(self.uyari)} uyarı" + (f", {len(self.bilgi)} bilgi" if self.bilgi else ""))
        return 1 if self.hata else 0


# ------------------------------------------------------------------ sözcük karşılaştırma
def sozcukler(metin):
    """Karşılaştırma için sözcükler: küçük harf (dile göre), noktalama/semboller atılır, boşlar düşer."""
    out = []
    for k in metin.split():
        n = "".join(ch for ch in ayar.kucuk(k) if ch.isalnum())
        if n:
            out.append(n)
    return out


def ozel_sozcuk(k):
    """Rakam, sembol ya da kısaltma içeren sözcük: seslendirmede yazıyla açılabilir ("27" -> "yirmi yedi")."""
    if any(ch.isdigit() for ch in k):
        return True
    if any(not ch.isalnum() and not ch.isspace() and ch not in NOKTALAMA for ch in k):
        return True          # %, °, &, +, /, $ ...
    harf = [ch for ch in k if ch.isalpha()]
    if len(harf) >= 2 and all(ch.isupper() for ch in harf):
        return True          # NASA, MÖ
    return bool(re.search(r"\w\.\w", k))   # M.Ö., a.k.a.


def farklar(a_ham, b_ham, en_cok=6):
    """İki metnin sözcük farkları -> ['"x" yerine "y"', ...]; boşluk farkı sayılmaz."""
    a, b = sozcukler(a_ham), sozcukler(b_ham)
    if "".join(a) == "".join(b):
        return []
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        sa, sb = " ".join(a[i1:i2]), " ".join(b[j1:j2])
        out.append(f'"{sa}" yerine "{sb}"' if sa and sb else (f'"{sa}" eksik' if sa else f'"{sb}" fazladan'))
        if len(out) >= en_cok:
            out.append("...")
            break
    return out


def metin_altyazi_farki(metin, altyazi):
    """metin altyazıdan yalnızca rakam/sembol/kısaltmalı sözcüklerde ayrılabilir; başka farklar listelenir."""
    ham_alt = altyazi.split()
    alt = [("".join(ch for ch in ayar.kucuk(k) if ch.isalnum()), k) for k in ham_alt]
    alt = [(n, k) for n, k in alt if n]
    met = sozcukler(metin)
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, [n for n, _ in alt], met, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        kaynak = [k for _, k in alt[i1:i2]]
        if kaynak and all(ozel_sozcuk(k) for k in kaynak):
            continue
        if not kaynak and op == "insert":
            # altyazıda karşılığı olmayan ek sözcük: öncesindeki ya da sonrasındaki özel sözcüğün açılımı olabilir
            komsu = [k for _, k in alt[max(0, i1 - 1):i1 + 1]]
            if any(ozel_sozcuk(k) for k in komsu):
                continue
        if not kaynak:
            out.append(f'metinde fazladan "{" ".join(met[j1:j2])}"')
        elif j1 == j2:
            out.append(f'metinde eksik "{" ".join(kaynak)}"')
        else:
            out.append(f'altyazı "{" ".join(kaynak)}" ↔ metin "{" ".join(met[j1:j2])}"')
    return out


def kullanici_metni(d):
    y = os.path.join(d, METIN_DOSYASI)
    if not os.path.exists(y):
        return None
    with open(y, encoding="utf-8") as f:
        return f.read()


def _yorumsuz(md):
    return re.sub(r"<!--.*?-->", " ", md, flags=re.S)


def video_metni(md):
    """kullanici-metni.md -> karşılaştırılacak düz metin (# başlık satırları ve HTML yorumları hariç)."""
    return "\n".join(ln for ln in _yorumsuz(md).splitlines() if not ln.lstrip().startswith("#"))


def kare_bolumleri(md):
    """'## Kare N' bölümleri -> {N: metin}."""
    out, cur, buf = {}, None, []
    for ln in _yorumsuz(md).splitlines():
        m = re.match(r"^\s*#{1,6}\s*kare\s*(\d+)\b", ln, re.I)
        if m:
            if cur is not None:
                out[cur] = "\n".join(buf)
            cur, buf = int(m.group(1)), []
        elif re.match(r"^\s*#", ln):
            if cur is not None:
                out[cur] = "\n".join(buf)
            cur, buf = None, []
        elif cur is not None:
            buf.append(ln)
    if cur is not None:
        out[cur] = "\n".join(buf)
    return out


def font_kontrol(d, veri, r, ad):
    """Üst düzey isteğe bağlı "font" alanı: dosya yolu ya da {kalin_dar, kalin_yari_dar}; dosyalar bulunmalı."""
    if not isinstance(veri, dict) or "font" not in veri or veri["font"] in (None, "", {}):
        return
    f = veri["font"]
    if not isinstance(f, (str, dict)):
        r.h(f"{ad}: 'font' bir dosya yolu ya da {{kalin_dar, kalin_yari_dar}} olmalı")
        return
    secim = ayar.font_alani(f)
    if not secim:
        r.h(f"{ad}: 'font' alanında dosya yolu yok")
    for tur in ("kalin_dar", "kalin_yari_dar"):
        if secim.get(tur) and not ayar.proje_font_dosyasi(secim[tur], d):
            r.u(f"{ad}: font dosyası bulunamadı: {secim[tur]} (proje köküne ya da {ayar.FONT_KLASORU}/ altına göre) "
                "-> ayarlardaki font kullanılır")


def durum_oku(d):
    try:
        with open(os.path.join(d, "durum.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


# ------------------------------------------------------------------ senaryo
def senaryo_kontrol(d):
    r = Rapor()
    mod = durum_oku(d).get("senaryo_modu", "ajan")
    kendi = str(mod).startswith("kendi-")
    not_ = r.b if kendi else r.u        # kendi-* modlarında öneri niteliğindeki notlar bilgi düzeyinde
    yol = os.path.join(d, "senaryo.json")
    try:
        with open(yol, encoding="utf-8") as f:
            s = json.load(f)
    except Exception as e:
        r.h(f"senaryo.json okunamadı: {e}")
        return r.bitir("Senaryo")
    for k in ("proje", "format", "karakterler", "varliklar", "satirlar"):
        if k not in s:
            r.h(f"eksik alan: {k}")
    font_kontrol(d, s, r, "senaryo.json")
    font_kontrol(d, durum_oku(d), r, "durum.json")
    kar = {k.get("id") for k in s.get("karakterler", [])}
    var = {v.get("id"): v for v in s.get("varliklar", [])}
    hiz = ayar.konusma_hizi()
    toplam = 0
    nolar = []
    satirlar = s.get("satirlar", [])
    for st in satirlar:
        no = st.get("no")
        nolar.append(no)
        for k in ("no", "konusan", "metin", "altyazi"):
            if k not in st:
                r.h(f"satır {no}: eksik alan '{k}'")
        if st.get("konusan") not in kar:
            r.h(f"satır {no}: konuşan '{st.get('konusan')}' karakterler listesinde yok")
        if re.search(r"\d", st.get("metin", "")):
            r.u(f"satır {no}: seslendirilen metinde rakam var — yazıyla yazılmalı")
        if "kaynak" not in st:
            not_(f"satır {no}: 'kaynak' alanı yok (bilgi içeriyorsa kaynağa bağla, içermiyorsa null yaz)")
        toplam += len(st.get("metin", ""))
        if not st.get("ekranda"):
            r.u(f"satır {no}: 'ekranda' boş — ekran durağan kalabilir")
        for ol in st.get("ekranda", []):
            ne = ol.get("ne")
            if ne not in OLAYLAR:
                r.h(f"satır {no}: bilinmeyen ekran olayı '{ne}'")
            if ne in ("nesne", "nesne-cik") and ol.get("kim") not in var:
                r.h(f"satır {no}: nesne '{ol.get('kim')}' varliklar listesinde yok")
            if ne == "arka-plan" and ol.get("kim") not in (None, "parsomen") and ol.get("kim") not in var:
                r.h(f"satır {no}: arka plan '{ol.get('kim')}' varliklar listesinde yok")
            if ne == "dusunce-balonu" and ol.get("icindeki") and ol["icindeki"] not in var:
                r.u(f"satır {no}: balon içeriği '{ol['icindeki']}' varlık değil, metin olarak gösterilecek")
            if ne in ("etiket", "isim-plakasi", "konum", "buyuk-metin") and not ol.get("metin"):
                r.h(f"satır {no}: '{ne}' için 'metin' gerekli")
            if ne == "yil" and not ("bas" in ol and "bit" in ol):
                r.h(f"satır {no}: 'yil' için 'bas' ve 'bit' gerekli")
            if ne == "ozel":
                r.u(f"satır {no}: özel olay (Animatör elle yapacak): {ol.get('aciklama', '')}")
        if mod == "kendi-aynen" and "metin" in st:
            for f_ in metin_altyazi_farki(st.get("metin", ""), st.get("altyazi") or st.get("metin", "")):
                r.h(f"satır {no}: metin altyazıdan ayrılıyor (kendi-aynen: yalnızca rakam/sembol/kısaltma açılabilir): {f_}")
    if nolar != sorted(nolar, key=lambda x: (x is None, x if x is not None else 0)) or len(set(nolar)) != len(nolar):
        r.h("satır numaraları sıralı ve benzersiz değil")
    if satirlar:
        ilk = min(satirlar, key=lambda x: x.get("no") or 0)
        ilk_sn = len(ilk.get("metin", "")) / hiz
        if ilk_sn > 4:
            not_(f"hook önerisi: ilk satır ≈{ilk_sn:.1f} sn; ilk 1.5–3 sn'de merak uyandıran kısa bir cümle önerilir")
    hedef = s.get("hedef_sure_sn", 33)
    alt_s, ust_s = round(25 * hiz), round(43.75 * hiz)
    if hedef >= 25 and not (alt_s <= toplam <= ust_s):
        not_(f"konuşma metni {toplam} karakter (≈{toplam / hiz:.0f} sn); 30-35 sn için "
             f"{round(28 * hiz, -1):.0f}-{round(40.6 * hiz, -1):.0f} önerilir")
    for v in s.get("varliklar", []):
        if v.get("arsivde_var") and not v.get("dosya"):
            r.u(f"varlık {v.get('id')}: arsivde_var=true ama dosya yolu yok")
    if mod == "kendi-aynen":
        md = kullanici_metni(d)
        if md is None:
            r.h(f"kendi-aynen modu ama {METIN_DOSYASI} yok")
        else:
            birlesik = " ".join((st.get("altyazi") or st.get("metin", "")) for st in sorted(
                satirlar, key=lambda x: x.get("no") or 0))
            fark = farklar(video_metni(md), birlesik)
            if fark:
                r.h(f"altyazılar {METIN_DOSYASI} ile aynı değil (kendi-aynen): " + "; ".join(fark))
    elif kendi and kullanici_metni(d) is None:
        r.b(f"'{mod}' modu: {METIN_DOSYASI} yok")
    print(f"Konuşma metni: {toplam} karakter ≈ {toplam / hiz:.1f} sn ({hiz:g} kar/sn), {len(nolar)} satır, mod {mod}")
    return r.bitir("Senaryo")


# ------------------------------------------------------------------ gönderi
def _kelime_sayisi(metin):
    return len(ISARET.sub(r"\1", metin or "").split())


def post_kontrol(d):
    r = Rapor()
    mod = durum_oku(d).get("senaryo_modu", "ajan")
    kendi = str(mod).startswith("kendi-")
    not_ = r.b if kendi else r.u
    try:
        with open(os.path.join(d, "post.json"), encoding="utf-8") as f:
            post = json.load(f)
    except Exception as e:
        r.h(f"post.json okunamadı: {e}")
        return r.bitir("Gönderi")
    if not isinstance(post, dict):
        r.h("post.json bir nesne olmalı")
        return r.bitir("Gönderi")
    tur = post.get("tur", "carousel")
    if tur not in POST_TURLERI:
        r.h(f"tur '{tur}' geçersiz ({' | '.join(sorted(POST_TURLERI))})")
    kareler = post.get("kareler")
    if not isinstance(kareler, list) or not kareler:
        r.h("kareler listesi yok ya da boş")
        return r.bitir("Gönderi")
    for alan, tip in (("baslik", str), ("aciklama", str), ("varliklar", list), ("gorsel_klasorleri", list),
                      ("sayfa_no", bool)):
        if alan in post and not isinstance(post[alan], tip):
            r.h(f"'{alan}' alanı {tip.__name__} olmalı")
    font_kontrol(d, post, r, "post.json")
    font_kontrol(d, durum_oku(d), r, "durum.json")
    if post.get("rozet", "bilgi") not in ("bilgi", "kare", "yok"):
        r.h(f"rozet '{post.get('rozet')}' geçersiz (bilgi | kare | yok)")
    var = {v.get("id") for v in post.get("varliklar", []) if isinstance(v, dict)}
    roller = []
    for i, k in enumerate(kareler, 1):
        if not isinstance(k, dict):
            r.h(f"kare {i}: nesne olmalı")
            continue
        rol = k.get("rol")
        roller.append(rol)
        if rol not in KARE_ROLLERI:
            r.u(f"kare {i}: bilinmeyen rol '{rol}' ({' | '.join(sorted(KARE_ROLLERI))}) -> 'bilgi' gibi çizilir")
        if k.get("no") not in (None, i):
            r.u(f"kare {i}: 'no' alanı {k.get('no')} (sıra {i})")
        for alan in ("metin", "alt_metin", "arka_plan", "cta", "sahne", "kaynak"):
            if alan in k and k[alan] is not None and not isinstance(k[alan], str):
                r.h(f"kare {i}: '{alan}' metin olmalı")
        if "vurgu" in k and not (isinstance(k["vurgu"], list) and all(isinstance(x, str) for x in k["vurgu"])):
            r.h(f"kare {i}: 'vurgu' metin listesi olmalı")
        g = k.get("gorsel")
        gorseller = [g] if isinstance(g, str) else g
        if g is not None and not (isinstance(gorseller, list) and all(isinstance(x, str) for x in gorseller)):
            r.h(f"kare {i}: 'gorsel' bir id ya da id listesi olmalı")
            gorseller = []
        for gid in gorseller or []:
            if var and gid not in var:
                r.u(f"kare {i}: görsel '{gid}' varliklar listesinde yok")
        ks = k.get("konusma")
        if ks is not None and not isinstance(ks, str):
            if not (isinstance(ks, list) and all(isinstance(b, dict) and isinstance(b.get("metin", ""), str) for b in ks)):
                r.h(f"kare {i}: 'konusma' metin ya da [{{kim, metin}}] listesi olmalı")
        if rol in ("kanca", "bilgi", "panel") and not gorseller:
            r.u(f"kare {i}: '{rol}' karesinde görsel yok")
        if rol != "panel" and not (k.get("metin") or "").strip():
            r.u(f"kare {i}: metin boş")
        n = _kelime_sayisi(k.get("metin"))
        if n > 20:
            r.u(f"kare {i}: metin {n} kelime (sınır 20)")
        if rol == "bilgi" and not k.get("kaynak"):
            not_(f"kare {i}: bilgi karesinde 'kaynak' alanı boş")
    if tur == "carousel":
        if not 5 <= len(kareler) <= 7:
            r.u(f"carousel {len(kareler)} kare (öneri 5-7)")
        if roller[:1] != ["kanca"]:
            r.u("1. kare 'kanca' değil")
        if roller[-1:] != ["kapanis"]:
            r.u("son kare 'kapanis' değil")
    elif tur == "karikatur" and not 1 <= len(kareler) <= 4:
        r.u(f"karikatür {len(kareler)} panel (öneri 1-4)")
    if mod == "kendi-aynen":
        md = kullanici_metni(d)
        if md is None:
            r.h(f"kendi-aynen modu ama {METIN_DOSYASI} yok")
        else:
            bolum = kare_bolumleri(md)
            if not bolum:
                r.h(f"{METIN_DOSYASI} içinde '## Kare N' bölümü yok")
            for i, k in enumerate(kareler, 1):
                if not isinstance(k, dict):
                    continue
                if i not in bolum:
                    if (k.get("metin") or "").strip():
                        r.h(f"kare {i}: {METIN_DOSYASI} içinde '## Kare {i}' bölümü yok")
                    continue
                fark = farklar(bolum[i], ISARET.sub(r"\1", k.get("metin") or ""))
                if fark:
                    r.h(f"kare {i}: metin '## Kare {i}' bölümüyle aynı değil (kendi-aynen): " + "; ".join(fark))
            fazla = sorted(set(bolum) - set(range(1, len(kareler) + 1)))
            if fazla:
                r.h(f"{METIN_DOSYASI} içindeki kareler post.json'da yok: {fazla}")
    print(f"Gönderi: {tur}, {len(kareler)} kare, mod {mod}")
    return r.bitir("Gönderi")


# ------------------------------------------------------------------ video
def ffmpeg_bilgi(yol, *ek):
    import imageio_ffmpeg
    p = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", yol, *ek], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return p.stderr


def video_kontrol(yol):
    r = Rapor()
    if not os.path.exists(yol):
        r.h(f"video yok: {yol}")
        return r.bitir("Video")
    bilgi = ffmpeg_bilgi(yol)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", bilgi)
    sure = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0
    v = re.search(r"Video: (\w+).*?(\d{3,4})x(\d{3,4}).*?([\d.]+) fps", bilgi)
    if not v:
        r.h("video akışı bulunamadı")
    else:
        if v.group(1) != "h264":
            r.u(f"kodek {v.group(1)} (h264 bekleniyor)")
        if (v.group(2), v.group(3)) != ("1080", "1920"):
            r.h(f"çözünürlük {v.group(2)}x{v.group(3)} (1080x1920 olmalı)")
        if abs(float(v.group(4)) - 30) > 0.01:
            r.u(f"fps {v.group(4)} (30 bekleniyor)")
    if "Audio:" not in bilgi:
        r.h("ses akışı yok")
    if not (12 <= sure <= 60):
        r.u(f"süre {sure:.1f} sn (12-60 aralığı dışında)")
    lo = ffmpeg_bilgi(yol, "-af", "ebur128=peak=true", "-f", "null", "-")
    mi = re.findall(r"I:\s+(-?[\d.]+) LUFS", lo)
    mp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", lo)
    if mi:
        lufs = float(mi[-1])
        if not (-17 <= lufs <= -11):
            r.u(f"ses yüksekliği {lufs} LUFS (hedef ≈ -14)")
    if mp and float(mp[-1]) > -0.5:
        r.u(f"ses tepesi {mp[-1]} dBFS (kırpılma riski)")
    bd = ffmpeg_bilgi(yol, "-vf", "blackdetect=d=0.4:pix_th=0.08", "-an", "-f", "null", "-")
    for b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", bd):
        r.h(f"siyah kare: {b[0]}-{b[1]} sn")
    fd = ffmpeg_bilgi(yol, "-vf", "freezedetect=n=0.0005:d=3", "-an", "-f", "null", "-")
    for b in re.findall(r"freeze_start: ([\d.]+)", fd):
        r.u(f"{b} sn'den itibaren 3+ sn donuk görüntü")
    print(f"Video: {os.path.basename(yol)}  {sure:.2f} sn  "
          f"{(v.group(2) + 'x' + v.group(3)) if v else '?'}  LUFS={mi[-1] if mi else '?'}  tepe={mp[-1] if mp else '?'} dBFS")
    return r.bitir("Video")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("proje", nargs="?")
    ap.add_argument("--senaryo", action="store_true")
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--video")
    a = ap.parse_args()
    if a.video:
        return video_kontrol(a.video)
    if not a.proje:
        ap.error("proje ya da --video gerekli")
    from proje import bul
    d = bul(a.proje)
    kod = 0
    if a.senaryo:
        kod |= senaryo_kontrol(d)
    if a.post:
        kod |= post_kontrol(d)
    if a.senaryo or a.post:
        return kod
    return video_kontrol(os.path.join(d, "cikti", os.path.basename(d) + ".mp4"))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
