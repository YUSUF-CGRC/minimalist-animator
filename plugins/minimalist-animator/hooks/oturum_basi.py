"""SessionStart kancası: Minimalist Animatör projesinde oturuma Yönetici rolünü ve ayar özetini ekler.

py.sh üzerinden çağrılır (proje kökünde `_tur: minimalist-animator` işaretli ayarlar.json yoksa hiç çalışmaz).
Ayrıca eklenti yolunu sirket/.eklenti dosyasına yazar: Bash aracı CLAUDE_PLUGIN_ROOT'u görmediği için
araçlar ve kullanıcı bu dosyadan `python "<yol>/studyo/ma.py"` komutunu kurabilir.
"""
import json
import os
import sys

SINIR = 9000      # oturum bağlamına eklenecek en fazla karakter; aşılırsa yalnızca özet + skill yönlendirmesi


def oku(yol):
    try:
        with open(yol, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def govde(skill):
    """SKILL.md'nin frontmatter'ını atıp gövdesini döndürür."""
    if skill.startswith("---"):
        son = skill.find("\n---", 3)
        if son != -1:
            return skill[son + 4:].lstrip()
    return skill


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        veri = json.load(sys.stdin)
    except Exception:
        veri = {}
    kok = os.environ.get("CLAUDE_PROJECT_DIR") or veri.get("cwd") or os.getcwd()
    eklenti = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    eklenti = eklenti.replace("\\", "/")
    try:
        ayar = json.loads(oku(os.path.join(kok, "ayarlar.json")) or "{}")
    except ValueError:
        ayar = {}
    try:
        os.makedirs(os.path.join(kok, "sirket"), exist_ok=True)
        with open(os.path.join(kok, "sirket", ".eklenti"), "w", encoding="utf-8") as f:
            f.write(eklenti + "\n")
    except OSError:
        pass

    marka = (ayar.get("marka") or {}).get("ad", "")
    kullanici = (ayar.get("kullanici") or {}).get("ad", "kullanıcı")
    icerik = ayar.get("icerik") or {}
    akis = ayar.get("akis") or {}
    ozet = (
        f"Bu klasör bir Minimalist Animatör stüdyosu. Marka: {marka or '(ayarlanmadı)'} · kullanıcı: {kullanici} · "
        f"içerik dili: {icerik.get('dil', 'tr')} · konu alanı: {icerik.get('konu_alani', '')} · "
        f"varsayılan senaryo modu: {akis.get('varsayilan_senaryo_modu', 'ajan')}.\n"
        f"Ana oturumda sen Yönetici'sin. Araç komutu: `ma <arac>`; PATH'te yoksa "
        f"`python \"{eklenti}/studyo/ma.py\" <arac>`. Eklenti protokolleri: `{eklenti}/protokoller/`.\n"
    )
    rol = govde(oku(os.path.join(eklenti, "skills", "yonetici", "SKILL.md")))
    if rol and len(ozet) + len(rol) <= SINIR:
        baglam = ozet + "\n" + rol
    else:
        baglam = ozet + "Yönetici rolünün ayrıntısı için `minimalist-animator:yonetici` skill'ini yükle."
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": baglam}},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
