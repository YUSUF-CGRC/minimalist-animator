"""Minimalist Animatör komut satırı — tek giriş noktası (ma).

  ma <arac> [argümanlar]       araclar/ altındaki betik (tire ya da alt çizgi): proje, kontrol, envanter, ...
  ma doktor [proje]            ortam: Python, numpy/Pillow/cv2/imageio_ffmpeg, ffmpeg, fontlar, proje kökü, ayarlar
  ma demo [--kareler]          çevrimdışı demo videosu (sirket/projeler/0000-00-00_demo/)
  ma kurulum [hedef] [--ayar anahtar=değer ...]
  ma render <proje> [--bilgi | --kareler otomatik | --kareler 1.2,7.5 | --kapak 3.2 | --ses]
  ma taslak-ses <proje> [--zorla]
  ma yardim                    bu metin + araç listesi

Proje kökü: MA_KOK -> CLAUDE_PROJECT_DIR -> çalışma klasöründen yukarı "_tur" işaretli ayarlar.json.
Başta yalnızca standart kütüphane kullanılır; numpy/cv2 gereken bir komutta bunlar yoksa sirket/.python ya da
ayarlar.json -> araclar.python yorumlayıcısıyla kendini yeniden çalıştırır.
"""
import importlib.util
import os
import runpy
import shutil
import subprocess
import sys

STUDYO = os.path.dirname(os.path.abspath(__file__))
EKLENTI = os.path.dirname(STUDYO)
ARACLAR = os.path.join(STUDYO, "araclar")
MOTOR = os.path.join(STUDYO, "motor")
sys.path.insert(0, MOTOR)
import ayar  # noqa: E402

PAKETLER = [("numpy", "numpy"), ("PIL", "Pillow"), ("cv2", "opencv-python-headless"), ("imageio_ffmpeg", "imageio-ffmpeg")]
# bağımlılık gerektirmeyen komutlar (yalnızca standart kütüphane)
YALIN = {"yardim", "kurulum", "doktor", "proje", "pano", "kilit", "ofis", "envanter", "indir_bekle", "indirilenler"}
OZEL = {"doktor", "demo", "kurulum", "render", "taslak_ses", "yardim"}


def norm_ad(ad):
    return ad.strip().lower().replace("-", "_")


def araclar():
    return sorted(os.path.splitext(f)[0] for f in os.listdir(ARACLAR) if f.endswith(".py") and not f.startswith("_"))


def bagimliliklar_var():
    return all(importlib.util.find_spec(m) is not None for m, _ in PAKETLER)


def kok_python():
    """sirket/.python ya da araclar.python ayarındaki yorumlayıcı (yoksa None)."""
    adaylar = []
    if ayar.kok_var_mi():
        y = ayar.yol("sirket", ".python")
        if os.path.isfile(y):
            with open(y, encoding="utf-8") as f:
                adaylar.append(f.read().strip())
    adaylar.append(str(ayar.al("araclar.python", "") or "").strip())
    for a in adaylar:
        if a and (os.path.isfile(a) or shutil.which(a)):
            return a
    return None


def ayni_yorumlayici(a, b):
    try:
        return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))
    except OSError:
        return False


def yeniden_calistir():
    """Bağımlılıklar bu yorumlayıcıda yoksa uygun olanla kendini yeniden çalıştırır (dönmez)."""
    py = kok_python()
    if py and not os.environ.get("MA_YENIDEN") and not ayni_yorumlayici(py, sys.executable):
        env = dict(os.environ, MA_YENIDEN="1")
        sys.exit(subprocess.run([py, os.path.abspath(__file__), *sys.argv[1:]], env=env).returncode)
    eksik = [p for m, p in PAKETLER if importlib.util.find_spec(m) is None]
    sys.exit(f"Eksik Python paketleri: {', '.join(eksik)} ({sys.executable}).\n"
             f'  Kurmak için: "{sys.executable}" -m pip install -r "{os.path.join(STUDYO, "requirements.txt")}"\n'
             "  Başka bir Python'da kuruluysa: ma kurulum --python-yenile (sirket/.python'a yazar).")


def ortami_hazirla():
    os.environ["MA_EKLENTI"] = EKLENTI
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if ayar.kok_var_mi():
        kok = ayar.kok()
        os.environ["MA_KOK"] = kok
        y = os.path.join(kok, "sirket", ".eklenti")
        if os.path.isdir(os.path.dirname(y)):
            try:
                with open(y, encoding="utf-8") as f:
                    mevcut = f.read().strip()
            except OSError:
                mevcut = ""
            if mevcut != EKLENTI.replace("\\", "/"):
                try:
                    with open(y, "w", encoding="utf-8") as f:
                        f.write(EKLENTI.replace("\\", "/") + "\n")
                except OSError:
                    pass


def betik_calistir(yol, args):
    sys.argv = [yol, *args]
    for d in (os.path.dirname(yol), MOTOR):
        if d not in sys.path:
            sys.path.insert(0, d)
    runpy.run_path(yol, run_name="__main__")
    return 0


# ------------------------------------------------------------------ özel komutlar
def cmd_yardim(_):
    print(__doc__)
    print("Araçlar: " + ", ".join(a.replace("_", "-") for a in araclar()))
    return 0


def cmd_render(args):
    if not args or args[0].startswith("-"):
        sys.exit("kullanım: ma render <proje> [--bilgi | --kareler otomatik | --kapak 3.2 | --ses]")
    sys.path.insert(0, ARACLAR)
    from proje import bul
    d = bul(args[0])
    r = os.path.join(d, "animasyon", "render.py")
    if not os.path.exists(r):
        os.makedirs(os.path.dirname(r), exist_ok=True)
        shutil.copy2(os.path.join(STUDYO, "sablon", "render.py"), r)
        print(f"animasyon/render.py yoktu: şablon kopyalandı ({r})")
    return subprocess.run([sys.executable, r, *args[1:]], cwd=d, env=dict(os.environ)).returncode


def cmd_taslak_ses(args):
    return betik_calistir(os.path.join(MOTOR, "taslak_ses.py"), args)


def cmd_kurulum(args):
    return betik_calistir(os.path.join(ARACLAR, "kurulum.py"), args)


def cmd_demo(args):
    if not ayar.kok_var_mi():
        sys.exit("Demo bir proje kökü ister: önce 'ma kurulum <klasör>' (ya da MA_KOK=<klasör>).")
    return betik_calistir(os.path.join(ARACLAR, "demo.py"), args)


def _surum(modul):
    try:
        m = __import__(modul)
        return getattr(m, "__version__", "?")
    except Exception as e:  # noqa: BLE001 — doktor her hatayı rapor eder
        return None if isinstance(e, ImportError) else f"HATA: {e}"


def cmd_doktor(args):
    sorun = 0

    def satir(durum, metin):
        nonlocal sorun
        if durum == "!!":
            sorun += 1
        print(f"  [{durum}] {metin}")

    print("== Python ==")
    v = sys.version_info
    satir("ok" if v >= (3, 10) else "!!", f"Python {v.major}.{v.minor}.{v.micro}  {sys.executable}")
    print("== Paketler ==")
    eksik = []
    for m, p in PAKETLER:
        s = _surum(m)
        if s is None or str(s).startswith("HATA"):
            eksik.append(p)
        not_ = ""
        if m == "PIL" and s and not str(s).startswith("HATA"):
            try:
                if tuple(int(x) for x in s.split(".")[:2]) < (10, 1):
                    not_ = "  (>= 10.1 gerekli: ImageFont.load_default(boyut))"
                    eksik.append(p)
            except ValueError:
                pass
        satir("ok" if s and not str(s).startswith("HATA") and not not_ else "--", f"{p}: {s or 'YOK'}{not_}")
    if eksik:
        py = kok_python()
        calisir = False
        if py and not ayni_yorumlayici(py, sys.executable):
            try:
                p = subprocess.run([py, "-c", "import numpy, cv2, PIL, imageio_ffmpeg"], capture_output=True, timeout=90)
                calisir = p.returncode == 0
            except (OSError, subprocess.SubprocessError):
                calisir = False
        if calisir:
            satir("ok", f"bu yorumlayıcıda eksik, ama {py} tam: ma komutları onunla çalışır")
        else:
            satir("!!", f"eksik paket: {', '.join(eksik)}. Kurmak için: "
                        f'"{sys.executable}" -m pip install -r "{os.path.join(STUDYO, "requirements.txt")}"')
    print("== ffmpeg ==")
    try:
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        ilk = subprocess.run([ff, "-version"], capture_output=True, text=True, timeout=30).stdout.splitlines()[:1]
        satir("ok", f"{ff}  ({ilk[0].split(' Copyright')[0] if ilk else '?'})")
    except Exception as e:  # noqa: BLE001
        satir("!!" if not eksik else "--", f"ffmpeg bulunamadı: {e}")
    print("== Proje kökü ==")
    satir("ok", f"eklenti: {EKLENTI}")
    if ayar.kok_var_mi():
        kok = ayar.kok()
        ay = os.path.join(kok, "ayarlar.json")
        satir("ok" if os.path.isfile(ay) else "!!", f"kök: {kok}" + ("" if os.path.isfile(ay) else "  (ayarlar.json yok: ma kurulum)"))
        for alt in ("sirket/projeler", "sirket/arsiv", "sirket/kullanici"):
            satir("ok" if os.path.isdir(os.path.join(kok, alt)) else "!!", alt + "/")
        py = os.path.join(kok, "sirket", ".python")
        if os.path.isfile(py):
            with open(py, encoding="utf-8") as f:
                satir("ok", f"sirket/.python: {f.read().strip()}")
        else:
            satir("--", "sirket/.python yok (ma kurulum --python-yenile)")
    else:
        satir("!!", "proje kökü bulunamadı: 'ma kurulum <klasör>' ya da MA_KOK=<klasör>")
    print("== Ayarlar ==")
    satir("ok", f"kullanıcı: {ayar.kullanici()} · marka: {ayar.marka_adi() or '(boş)'} · dil: {ayar.dil()} · "
                f"konuşma hızı: {ayar.konusma_hizi():g} kar/sn · senaryo modu: {ayar.al('akis.varsayilan_senaryo_modu')}")
    lg = ayar.logo_yolu()
    satir("ok", f"logo: {lg or 'yok -> kapanışta marka adı yazılır'} · slogan: {ayar.al('marka.slogan') or '(boş)'}")
    ind = os.path.normpath(os.path.expanduser(str(ayar.al("araclar.indirilenler_klasoru") or "~/Downloads")))
    satir("ok" if os.path.isdir(ind) else "--", f"indirilenler: {ind}" + ("" if os.path.isdir(ind) else " (klasör yok)"))
    print("== Yazı tipleri ==")
    if args and ayar.kok_var_mi():
        sys.path.insert(0, ARACLAR)
        from proje import bul
        d = bul(args[0])
        secim = ayar.proje_fontu(d)
        satir("ok", f"proje: {os.path.basename(d)}  font alanı: {secim or 'yok (ayarlar kullanılır)'}")
    for tur in ("kalin_dar", "kalin_yari_dar"):
        y, vary, kaynak = ayar.font_cozumle(tur)
        durum = "ok" if y else "!!"
        glif = ""
        if y and importlib.util.find_spec("PIL"):
            try:
                from PIL import ImageFont
                f = ImageFont.truetype(y, 40)
                if vary:
                    f.set_variation_by_name(vary)
                bos = f.getmask("").getbbox()
                eksik_harf = [ch for ch in "ĞÜŞİÖÇğüşıöç" if f.getmask(ch).getbbox() == bos]
                glif = "  Türkçe harfler tam" if not eksik_harf else f"  EKSİK HARF: {''.join(eksik_harf)}"
                if eksik_harf:
                    durum = "!!"
            except Exception as e:  # noqa: BLE001
                glif, durum = f"  açılamadı: {e}", "!!"
        satir(durum, f"{tur}: {y or 'Pillow yedeği'}{f' [{vary}]' if vary else ''}  ← {kaynak}{glif}")
    print(f"\n{'Sorun yok.' if sorun <= 0 else f'{sorun} sorun var.'}")
    return 0 if sorun <= 0 else 1


KOMUTLAR = {"yardim": cmd_yardim, "doktor": cmd_doktor, "demo": cmd_demo, "kurulum": cmd_kurulum,
            "render": cmd_render, "taslak_ses": cmd_taslak_ses}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        return cmd_yardim(None)
    ad, args = norm_ad(sys.argv[1]), sys.argv[2:]
    if ad not in OZEL and ad not in araclar():
        print(f"Bilinmeyen komut: {sys.argv[1]}\n")
        cmd_yardim(None)
        return 2
    if ad not in YALIN and not bagimliliklar_var():
        yeniden_calistir()
    ortami_hazirla()
    if ad in KOMUTLAR:
        return KOMUTLAR[ad](args)
    return betik_calistir(os.path.join(ARACLAR, ad + ".py"), args)


if __name__ == "__main__":
    sys.exit(main())
