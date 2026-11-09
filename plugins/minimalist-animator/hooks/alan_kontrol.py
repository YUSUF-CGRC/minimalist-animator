"""Tarayıcı ajanlarının yalnızca izinli sitelere gitmesini sağlayan PreToolUse kancası.

hooks.json'dan py.sh üzerinden çağrılır; yalnızca Minimalist Animatör projelerinde çalışır.
stdin: Claude Code kanca JSON'u. Ajan, girdideki `agent_type` alanından tanınır:
  - alan yoksa çağrı ana oturumdan (Yönetici) gelir → izin verilir;
  - başka bir eklentinin ajanıysa → karışılmaz;
  - `minimalist-animator:<ad>` ise → proje kökündeki sirket/izinli-alanlar.json[<ad>] listesine bakılır.
Çıkış kodu 2 = çağrıyı engelle (stderr ajana iletilir).
Hata ayıklama: MA_KANCA_GUNLUK=1 ise girdi sirket/.kanca-girdi.log'a eklenir.
"""
import json
import os
import sys
from urllib.parse import urlparse

ONEK = "minimalist-animator:"
SERBEST = ("back", "forward", "about:blank", "chrome://newtab/", "chrome://newtab")


def alan(url):
    u = url.strip()
    if "://" not in u:
        u = "https://" + u
    return (urlparse(u).hostname or "").lower().rstrip(".")


def main():
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        veri = json.load(sys.stdin)
    except Exception:
        return 0
    kok = os.environ.get("CLAUDE_PROJECT_DIR") or veri.get("cwd") or os.getcwd()
    if os.environ.get("MA_KANCA_GUNLUK"):
        with open(os.path.join(kok, "sirket", ".kanca-girdi.log"), "a", encoding="utf-8") as f:
            f.write(json.dumps(veri, ensure_ascii=False) + "\n")

    url = str((veri.get("tool_input") or {}).get("url", "")).strip()
    if not url or url in SERBEST:
        return 0
    tur = str(veri.get("agent_type") or "")
    if not tur and not veri.get("agent_id"):
        return 0                                  # ana oturum: Yönetici
    if tur and not tur.startswith(ONEK):
        return 0                                  # başka bir eklentinin ajanı
    ajan = tur[len(ONEK):] if tur else ""

    try:
        with open(os.path.join(kok, "sirket", "izinli-alanlar.json"), encoding="utf-8") as f:
            tablo = json.load(f)
    except Exception as e:
        print(f"İzinli alan listesi okunamadı ({e}); güvenlik için gezinme engellendi.", file=sys.stderr)
        return 2
    if ajan:
        liste = tablo.get(ajan, [])
    else:                                         # ajan kimliği gelmediyse: tarayıcı ajanlarının birleşik listesi
        liste = sorted({d for k, v in tablo.items() if not k.startswith("_") and isinstance(v, list) for d in v})
    h = alan(url)
    if any(h == d or h.endswith("." + d) for d in liste):
        return 0
    print(
        f"ENGELLENDİ: '{h}' alanı {ajan or 'bu ajan'} için izinli değil (izinliler: {', '.join(liste) or 'yok'}). "
        "Bu siteye gitmeye çalışma. Gerçekten gerekiyorsa raporundaki 'talepler' bölümüne "
        "kime: yonetici, hangi site, neden ve ne okuyacağını yaz; Yönetici gerekirse kullanıcıya sorar.",
        file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
