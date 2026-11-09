"""Kodla üretilen ses efektleri ve müzik parçaları (44.1 kHz mono numpy dizileri)."""
import subprocess
import numpy as np
import imageio_ffmpeg

SR = 44100
PI2 = 2 * np.pi
rng = np.random.default_rng(7)


def T(d):
    return np.arange(int(d * SR)) / SR


def osc(freq, t=None):
    if np.isscalar(freq):
        return np.sin(PI2 * freq * t)
    return np.sin(PI2 * np.cumsum(freq) / SR)


def att(n, a=0.003):
    e = np.ones(n)
    k = min(n, max(1, int(a * SR)))
    e[:k] = np.linspace(0, 1, k)
    return e


def fft_band(x, lo, hi, soft=0.3):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = 1 / (1 + (lo / np.maximum(f, 1)) ** (2 / soft)) / (1 + (f / hi) ** (2 / soft))
    return np.fft.irfft(X * m, len(x))


def svf_bp(x, fc, q=1.0):
    y = np.zeros_like(x)
    low = band = 0.0
    fcs = np.broadcast_to(fc, x.shape)
    damp = 1 / q
    for i in range(len(x)):
        f = 2 * np.sin(np.pi * min(fcs[i], SR / 6) / SR)
        high = x[i] - low - damp * band
        band += f * high
        low += f * band
        y[i] = band
    return y


def biquad_bp(x, fc, q):
    w = PI2 * fc / SR
    al = np.sin(w) / (2 * q)
    b0, b2, a0, a1, a2 = al, -al, 1 + al, -2 * np.cos(w), 1 - al
    b0, b2, a1, a2 = b0 / a0, b2 / a0, a1 / a0, a2 / a0
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(len(x)):
        v = b0 * x[i] + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, x[i], y1, v
        y[i] = v
    return y


def norm(x, peak=1.0):
    m = np.abs(x).max()
    return x * (peak / m) if m > 0 else x


def place_into(buf, snd, t0):
    i = int(round(t0 * SR))
    if i >= len(buf):
        return buf
    if i < 0:
        snd, i = snd[-i:], 0
    n = min(len(snd), len(buf) - i)
    buf[i:i + n] += snd[:n]
    return buf


def load_audio(path):
    raw = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar",
                          str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


# ------------------------------------------------------------------ efektler
def pop(pitch=1.0):
    t = T(0.12)
    f = (320 + 1100 * np.clip(t / 0.035, 0, 1)) * pitch
    return norm(osc(f) * np.exp(-t / 0.028) * att(len(t), 0.002))


def boing(pitch=1.0, d=0.55):
    t = T(d)
    f = 170 * pitch * (1 + 0.55 * t) * (1 + 0.28 * np.sin(PI2 * 13 * t) * np.exp(-4.5 * t))
    return norm((osc(f) + 0.35 * osc(2 * f)) * np.exp(-t / 0.17) * att(len(t), 0.004))


def thump(f0=110, d=0.3, noise=0.35):
    t = T(d)
    f = f0 * (0.55 + 0.45 * np.exp(-t / 0.035))
    n = fft_band(rng.standard_normal(len(t)), 30, 600) * np.exp(-t / 0.02)
    return norm(osc(f) * np.exp(-t / 0.075) * att(len(t), 0.002) + noise * norm(n))


def whoosh(d=0.45, f0=450, f1=2600, down=False):
    t = T(d)
    p = t / d
    sweep = np.sin(np.pi * p)
    fc = f0 + (f1 - f0) * (1 - p if down else p) * 0.6 + (f1 - f0) * 0.4 * sweep
    y = svf_bp(rng.standard_normal(len(t)), fc, 1.4)
    return norm(y * np.sin(np.pi * p) ** 2)


def tick(f=3200, d=0.05, click=0.6):
    t = T(d)
    n = np.diff(rng.standard_normal(len(t) + 1)) * np.exp(-t / 0.0035)
    return norm(click * norm(n) + osc(f, t) * np.exp(-t / 0.011) + 0.4 * osc(f * 1.52, t) * np.exp(-t / 0.007))


def bell(f0, d=1.4, bright=1.0):
    t = T(d)
    y = np.zeros(len(t))
    for r, a, k in [(1, 1, 1), (2.0, .55, .6), (3.0, .3 * bright, .4), (4.16, .22 * bright, .28), (5.43, .12 * bright, .18)]:
        y += a * osc(f0 * r, t) * np.exp(-t / (d * 0.33 * k))
    return norm(y * att(len(t), 0.002))


def trumpet(d=0.8):
    t = T(d)
    f = 230 + 250 * (1 - np.exp(-t / 0.05))
    f *= 1 + 0.028 * np.sin(PI2 * 6.5 * t) * np.clip((t - 0.12) / 0.1, 0, 1)
    f *= 1 - 0.22 * np.clip((t - (d - 0.2)) / 0.2, 0, 1)
    ph = PI2 * np.cumsum(f) / SR
    saw = sum(np.sin(k * ph) / k for k in range(1, 14))
    raw = saw * att(len(t), 0.03) * np.clip((d - t) / 0.14, 0, 1)
    return norm(0.35 * raw + biquad_bp(raw, 1100, 2.2) + 0.7 * biquad_bp(raw, 2500, 3.0))


def bubble(f0):
    t = T(0.06)
    return osc(f0 * (1 + 1.3 * t / 0.06)) * np.exp(-t / 0.018) * att(len(t), 0.002)


def water(d):
    t = T(d)
    hiss = fft_band(rng.standard_normal(len(t)), 500, 3500, 0.5)
    mod = fft_band(rng.standard_normal(len(t)), 2, 18, 0.6)
    y = norm(hiss) * (0.55 + 0.45 * norm(mod)) * 0.45
    for _ in range(int(d * 13)):
        place_into(y, bubble(rng.uniform(450, 1300)) * rng.uniform(0.2, 0.55), rng.uniform(0, max(0.01, d - 0.06)))
    return y * np.clip(t / 0.15, 0, 1) * np.clip((d - t) / 0.25, 0, 1)


def drip(f0=850):
    t = T(0.12)
    return norm(osc(f0 * (1 + 1.4 * np.clip(t / 0.04, 0, 1))) * np.exp(-t / 0.03) * att(len(t), 0.001))


def gears(d, rate0, rate1):
    t = T(d)
    y = np.zeros(len(t))
    ph = np.cumsum(np.linspace(rate0, rate1, len(t))) / SR
    for j, i in enumerate(np.nonzero(np.diff(np.floor(ph)) > 0)[0]):
        c = tick(rng.uniform(1700, 2600), 0.04, 0.9) * rng.uniform(0.5, 1.0)
        place_into(y, c, i / SR)
    return y * np.clip(t / 0.2, 0, 1) * np.clip((d - t) / 0.2, 0, 1)


def rewind(d=1.0):
    t = T(d)
    p = t / d
    ph = np.cumsum(6 + 46 * np.sin(np.pi * p) ** 1.5) / SR
    y = np.zeros(len(t))
    for i in np.nonzero(np.diff(np.floor(ph)) > 0)[0]:
        place_into(y, tick(rng.uniform(2600, 3400), 0.03, 0.6) * 0.7, i / SR)
    ph2 = PI2 * np.cumsum(180 + 700 * np.sin(np.pi * p)) / SR
    whirr = sum(np.sin(k * ph2) / k for k in range(1, 6)) * np.sin(np.pi * p) * 0.25
    return norm(y + whirr)


def beeps(freqs=(988, 1319, 784)):
    y = np.zeros(int((0.12 * len(freqs) + 0.1) * SR))
    for k, f in enumerate(freqs):
        t = T(0.085)
        sq = sum(np.sin(PI2 * f * m * t) / m for m in (1, 3, 5))
        place_into(y, sq * att(len(t), 0.004) * np.clip((0.085 - t) / 0.02, 0, 1), k * 0.12)
    return norm(y)


def sparkle(d=0.8, n=14, lo=3000, hi=7500):
    y = np.zeros(int(d * SR))
    for _ in range(n):
        f, tau = rng.uniform(lo, hi), rng.uniform(0.06, 0.16)
        t = T(min(d, tau * 5))
        place_into(y, osc(f, t) * np.exp(-t / tau) * att(len(t), 0.002) * rng.uniform(0.3, 1), rng.uniform(0, d * 0.65))
    return norm(y)


def arpeggio(freqs, step=0.075, d=1.2):
    y = np.zeros(int((d + step * len(freqs)) * SR))
    for k, f in enumerate(freqs):
        place_into(y, bell(f, d, 0.7) * (0.75 + 0.25 * k / len(freqs)), k * step)
    return norm(y)


def chirp(base=2500):
    y = np.zeros(int(0.42 * SR))
    for k in range(3):
        t = T(0.075)
        f = base + 1900 * np.sin(np.pi * t / 0.075) + 300 * k
        place_into(y, osc(f) * np.sin(np.pi * t / 0.075) ** 2, k * 0.11)
    return norm(y)


def pad_chord(freqs=(146.83, 220, 293.66, 369.99, 440), d=2.6):
    t = T(d)
    y = np.zeros(len(t))
    for f in freqs:
        for det in (-0.6, 0.6):
            y += osc(f + det, t)
    return norm(y * np.clip(t / 0.35, 0, 1) * np.clip((d - t) / 1.2, 0, 1))


# ---- zaman yolculuğu efektleri
def zupp(d=1.0):
    """Zaman yolculuğu: yükselen girdap + faz kayan gürültü + parıltı."""
    t = T(d)
    p = t / d
    f = 120 * 2 ** (5 * p ** 1.6)
    ph = PI2 * np.cumsum(f) / SR
    tone = sum(np.sin(k * ph + 0.5 * np.sin(PI2 * 7 * t)) / k for k in range(1, 6))
    noise = svf_bp(rng.standard_normal(len(t)), 300 + 5000 * p ** 1.3, 2.0)
    env = np.sin(np.pi * np.clip(p * 1.05, 0, 1)) ** 0.8
    return norm((0.6 * norm(tone) + 0.8 * norm(noise)) * env + 0.4 * place_into(np.zeros(len(t)), sparkle(d * 0.6, 12), d * 0.4))


def power_up(d=1.1):
    t = T(d)
    f = 90 + 900 * (t / d) ** 2
    ph = PI2 * np.cumsum(f) / SR
    y = sum(np.sin(k * ph) / k for k in range(1, 7)) * np.clip(t / 0.1, 0, 1) * (0.4 + 0.6 * t / d)
    return norm(y * np.clip((d - t) / 0.08, 0, 1))


def hum(d, f0=60):
    t = T(d)
    y = osc(f0, t) + 0.5 * osc(2 * f0, t) + 0.25 * osc(3 * f0 + 0.7, t)
    y *= 0.8 + 0.2 * np.sin(PI2 * 0.9 * t)
    return norm(y * np.clip(t / 0.3, 0, 1) * np.clip((d - t) / 0.3, 0, 1))


def zap(d=0.18):
    t = T(d)
    n = rng.standard_normal(len(t)) * (rng.random(len(t)) < 0.15)
    buzz = sum(np.sin(PI2 * 180 * m * t) / m for m in range(1, 12, 2))
    return norm((fft_band(n, 1500, 9000) * 2 + 0.4 * buzz) * np.exp(-t / (d * 0.4)) * att(len(t), 0.001))


def clank():
    t = T(0.5)
    y = sum(a * osc(f, t) * np.exp(-t / tau) for f, a, tau in ((420, 1, .12), (1130, .6, .08), (2370, .4, .05), (3510, .25, .03)))
    return norm(y + 0.6 * thump(140, 0.5, 0.6))


def buzzer(d=0.22):
    """Hata 'dıt' sesi (yasak/X damgası)."""
    t = T(d)
    sq = sum(np.sin(PI2 * 155 * m * t) / m for m in range(1, 16, 2))
    return norm(sq * att(len(t), 0.004) * np.clip((d - t) / 0.03, 0, 1))


def slide_whistle(f0=500, f1=1300, d=0.45):
    t = T(d)
    f = f0 * (f1 / f0) ** (t / d)
    f *= 1 + 0.015 * np.sin(PI2 * 7 * t)
    y = osc(f) + 0.12 * osc(2 * f)
    return norm(y * np.sin(np.pi * t / d) ** 0.6 + 0.05 * fft_band(rng.standard_normal(len(t)), 1000, 4000))


def cricket(d=0.5):
    y = np.zeros(int(d * SR))
    for k in range(int(d / 0.16)):
        t = T(0.07)
        y_ = osc(4400, t) * (0.5 + 0.5 * np.sin(PI2 * 75 * t)) * np.sin(np.pi * t / 0.07)
        place_into(y, y_, k * 0.16)
    return norm(y)


def tweets(d=0.9):
    """Sersemleme: başın etrafında dönen kuşlar."""
    y = np.zeros(int(d * SR))
    for k in range(int(d / 0.22)):
        t = T(0.12)
        f = 2600 + 900 * np.sin(PI2 * 9 * t) + 400 * (k % 2)
        place_into(y, osc(f) * np.sin(np.pi * t / 0.12) ** 2, k * 0.22)
    return norm(y)


def fanfare():
    y = np.zeros(int(1.4 * SR))
    for k, (f, d) in enumerate(((392, .16), (523.25, .16), (659.25, .16), (783.99, .8))):
        t = T(d + 0.2)
        ph = PI2 * f * t
        saw = sum(np.sin(m * ph) / m for m in range(1, 10))
        env = att(len(t), 0.02) * np.clip((d + 0.2 - t) / 0.2, 0, 1)
        place_into(y, saw * env * (1 + 0.02 * np.sin(PI2 * 6 * t)), k * 0.15)
    return norm(0.5 * y + biquad_bp(y, 1400, 1.5))


# ------------------------------------------------------------------ müzik araçları
def ks(f, d, bright=0.55, decay=0.996):
    n = int(d * SR)
    N = max(2, int(round(SR / f)))
    y = np.zeros(n + N + 1)
    init = rng.uniform(-1, 1, N + 1)
    for _ in range(int((1 - bright) * 4)):
        init = 0.5 * (init + np.roll(init, 1))
    y[:N + 1] = init
    i = N + 1
    while i < len(y):
        j = min(i + N, len(y))
        y[i:j] = decay * 0.5 * (y[i - N:j - N] + y[i - N - 1:j - N - 1])
        i = j
    return y[:n] * np.clip((d - T(d)) / 0.08, 0, 1)


def synth_pluck(f, d=0.22, harm=8, cutoff_tau=0.06):
    t = T(d)
    ph = PI2 * f * t
    y = sum(np.sin(m * ph) / m * np.exp(-t * m / (cutoff_tau * 40)) for m in range(1, harm + 1))
    return y * att(len(t), 0.003) * np.exp(-t / (d * 0.5))
