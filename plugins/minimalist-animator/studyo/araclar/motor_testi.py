"""Motor duman testi: demo projeyi (ornek/demo -> sirket/projeler/0000-00-00_demo) kurar, kontrol karelerini üretir ve
senaryo/araçların çalıştığını doğrular. Tam render yapmaz (onun için: ma demo).

  ma motor-testi
Çıkış kodu 0 = motor sağlam.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import demo  # noqa: E402


def calis(*args, cwd):
    p = subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=demo.ortam())
    return p.returncode, (p.stdout + p.stderr).strip()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    d = demo.hazirla(sessiz=True)
    araclar = os.path.dirname(os.path.abspath(__file__))
    render = os.path.join(d, "animasyon", "render.py")
    ok = True
    for ad, args in (("görseller", [os.path.join(d, "hazirla.py"), d]),
                     ("taslak ses", [os.path.join(demo.STUDYO, "motor", "taslak_ses.py"), d, "--zorla"]),
                     ("senaryo kontrolü", [os.path.join(araclar, "kontrol.py"), d, "--senaryo"]),
                     ("zamanlama", [render, "--bilgi"]),
                     ("kontrol kareleri", [render, "--kareler", "otomatik"])):
        kod, cikti = calis(*args, cwd=d)
        print(f"[{'OK' if kod == 0 else 'HATA'}] {ad}")
        if kod != 0:
            ok = False
            print(cikti[-1500:])
            break
    print("Motor sağlam." if ok else "Motor testi BAŞARISIZ — son değişikliği geri al ya da düzelt.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
