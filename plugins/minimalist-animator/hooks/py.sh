#!/bin/sh
# Minimalist Animatör kanca başlatıcısı: hooks/<ad>.py betiğini uygun Python ile çalıştırır.
# Yalnızca proje kökünde `"_tur": "minimalist-animator"` işaretli ayarlar.json varsa çalışır;
# başka projelerde hiçbir şey yapmadan çıkar (Python bile başlatılmaz).
kok="${CLAUDE_PROJECT_DIR:-$PWD}"
grep -q '"_tur"[[:space:]]*:[[:space:]]*"minimalist-animator"' "$kok/ayarlar.json" 2>/dev/null || exit 0
betik="$(dirname "$0")/$1.py"
secili="$(head -n 1 "$kok/sirket/.python" 2>/dev/null)"
for py in "$secili" python3 python "py -3"; do
  [ -n "$py" ] || continue
  # Windows'taki Store yer tutucusunu elemek için yorumlayıcıyı gerçekten çalıştırarak sına
  if $py -c "import sys" >/dev/null 2>&1; then
    exec $py "$betik"
  fi
done
echo "Minimalist Animatör: Python bulunamadı; kanca atlandı ($1)." >&2
exit 0
