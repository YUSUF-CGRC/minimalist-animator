"""Ses yardımcıları: yükleme/kaydetme, konuşma zarfı, sessizlik tespiti, satırlara bölme, seviye eşitleme.

Tüm diziler 44.1 kHz mono float64.
"""
import subprocess
import wave

import imageio_ffmpeg
import numpy as np

import ayar

SR = 44100
FF = imageio_ffmpeg.get_ffmpeg_exe()


def yukle(yol):
    raw = subprocess.run([FF, "-v", "error", "-i", str(yol), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def kaydet(yol, x):
    """Mono ya da (n, 2) stereo diziyi 16-bit WAV olarak yazar."""
    x = np.asarray(x, np.float64)
    ch = 1 if x.ndim == 1 else x.shape[1]
    with wave.open(str(yol), "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def sure(x):
    return len(x) / SR


def _rms_db(x, pencere=0.02):
    hop = max(1, int(pencere * SR))
    n = len(x) // hop
    if n == 0:
        return np.array([-120.0]), hop
    r = np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1))
    return 20 * np.log10(np.maximum(r, 1e-7)), hop


def sessizlikler(x, esik_db=None, min_sure=0.10):
    """Sessiz aralıklar [(bas, bit), ...] saniye cinsinden. Eşik verilmezse sesin kendisine göre seçilir."""
    db, hop = _rms_db(x)
    if esik_db is None:
        konusma = np.percentile(db, 90)
        esik_db = max(konusma - 32, -60)
    sessiz = db < esik_db
    out, i = [], 0
    while i < len(sessiz):
        if sessiz[i]:
            j = i
            while j < len(sessiz) and sessiz[j]:
                j += 1
            if (j - i) * hop / SR >= min_sure:
                out.append((i * hop / SR, j * hop / SR))
            i = j
        else:
            i += 1
    return out


def konusma_araligi(x, esik_db=None):
    """İlk ve son sesli an (saniye)."""
    db, hop = _rms_db(x, 0.01)
    if esik_db is None:
        esik_db = max(np.percentile(db, 90) - 35, -62)
    idx = np.nonzero(db >= esik_db)[0]
    if len(idx) == 0:
        return 0.0, sure(x)
    return idx[0] * hop / SR, min(sure(x), (idx[-1] + 1) * hop / SR)


def bol(x, n, min_parca=0.35, elle=None):
    """Sesi n parçaya böler. Kesimler en uzun iç sessizliklerin ortasına konur.

    Dönüş: [(bas, bit), ...] — her parçanın baş/son sessizliği kırpılmış sınırları (saniye).
    elle: kesim noktaları listesi (saniye) verilirse otomatik seçim yapılmaz.
    """
    a, b = konusma_araligi(x)
    if n <= 1:
        return [(max(0, a - 0.04), min(sure(x), b + 0.06))]
    if elle:
        kesimler = sorted(elle)
    else:
        adaylar = [(e - s, (s + e) / 2) for s, e in sessizlikler(x) if s > a + 0.05 and e < b - 0.05]
        adaylar.sort(reverse=True)
        kesimler = []
        for uzunluk, orta in adaylar:
            if all(abs(orta - k) >= min_parca for k in kesimler):
                kesimler.append(orta)
            if len(kesimler) == n - 1:
                break
        kesimler.sort()
        if len(kesimler) < n - 1:
            raise ValueError(f"{n} parça için yeterli duraklama bulunamadı ({len(kesimler) + 1} parça çıktı). "
                             "--elle ile kesim noktası verin ya da satırı ayrı üretin.")
    sinirlar = [a] + kesimler + [b]
    out = []
    for s, e in zip(sinirlar[:-1], sinirlar[1:]):
        parca = x[int(s * SR):int(e * SR)]
        pa, pb = konusma_araligi(parca)
        out.append((max(0.0, s + pa - 0.04), min(sure(x), s + pb + 0.06)))
    return out


def kes(x, bas, bit, yumusak=0.008):
    y = x[int(bas * SR):int(bit * SR)].copy()
    k = min(len(y) // 2, int(yumusak * SR))
    if k > 0:
        r = np.linspace(0, 1, k)
        y[:k] *= r
        y[-k:] *= r[::-1]
    return y


def seviye_esitle(x, hedef_db=-19.0, tepe=0.95):
    """Konuşulan kısmın RMS'ini hedefe çeker, tepeyi sınırlar."""
    db, hop = _rms_db(x)
    sesli = db > np.percentile(db, 90) - 25
    if not sesli.any():
        return x
    rms = 10 ** (np.mean(db[sesli]) / 20)
    y = x * (10 ** (hedef_db / 20) / max(rms, 1e-6))
    m = np.abs(y).max()
    return y * (tepe / m) if m > tepe else y


def zarf(x, fps=30, uzunluk=None):
    """Kare başına 0..1 konuşma zarfı (hızlı yükselen, yavaş düşen)."""
    hop = SR // fps
    nfr = uzunluk or int(np.ceil(len(x) / hop))
    xx = np.zeros(nfr * hop)
    xx[:min(len(x), len(xx))] = x[:len(xx)]
    rms = np.sqrt(np.mean(xx.reshape(nfr, hop) ** 2, axis=1))
    ref = np.percentile(rms[rms > 1e-4], 95) if (rms > 1e-4).any() else 1.0
    rms = rms / max(ref, 1e-6)
    env = np.zeros(nfr)
    for i in range(nfr):
        prev = env[i - 1] if i else 0.0
        env[i] = prev + (rms[i] - prev) * (0.6 if rms[i] > prev else 0.25)
    return np.clip(env, 0, 1.2)


SESLILER = "aeiouyàáâãäåæèéêëìíîïòóôõöøùúûüýÿœąęįųāēīōūăőűаеёиоуыэюяіїєαεηιουω"


def hece_sayisi(metin):
    """Yaklaşık hece sayısı. Türkçe/Azericede her ünlü bir hecedir; diğer dillerde ardışık ünlü grupları sayılır."""
    if ayar.dil() in ayar.TR_DILLER:
        metin = metin.replace("İ", "i").lower()
        return max(1, sum(ch in "aeıioöuü" for ch in metin))
    metin = metin.lower()
    grup, onceki = 0, False
    for ch in metin:
        sesli = ch in SESLILER
        if sesli and not onceki:
            grup += 1
        onceki = sesli
    if grup == 0:
        harf = sum(ch.isalpha() for ch in metin)
        grup = round(harf / 3)
    return max(1, grup)
