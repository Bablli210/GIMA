#!/usr/bin/env python3
"""
Original score for the GIMA website direction film (motion.html, 72 s).

Everything is synthesised here from oscillators and noise: no samples, loops or third-party
music, so there is nothing to license. 120 BPM in F major / D minor. The midpoint of every
scene wipe in the film falls on a beat, and the sound design is cued to the same times as
motion.html (pen strokes on the line drawing, cursor ticks, keynote tags, scope slabs,
3D layers landing).

    python3 score.py [out.wav]          48 kHz stereo WAV, default score.wav
    Needs numpy and scipy.

render.js muxes it into the MP4 with --audio score.wav (normalised to -16 LUFS there).
"""
import re
import sys
import wave
import numpy as np
from scipy import signal

SR = 48000
DUR = 72.0
N = int(DUR * SR)
BEAT = 0.5                                   # 120 BPM
rng = np.random.default_rng(1980)

BUS = {k: np.zeros((2, N)) for k in ('pad', 'bass', 'kick', 'hats', 'drums', 'keys', 'fx', 'send')}


# ---------------------------------------------------------------- helpers
def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def pan2(x, pan):
    """Constant-power pan. pan is -1 (left) … 1 (right), scalar or per-sample array."""
    a = (np.asarray(pan) + 1) * np.pi / 4
    return np.vstack([x * np.cos(a), x * np.sin(a)])


def put(bus, t0, x, pan=0.0, gain=1.0, send=0.0):
    if x.ndim == 1:
        x = pan2(x, pan)
    i0 = int(round(t0 * SR))
    s, e = max(0, i0), min(N, i0 + x.shape[1])
    if e <= s:
        return
    seg = gain * x[:, s - i0:e - i0]
    BUS[bus][:, s:e] += seg
    if send:
        BUS['send'][:, s:e] += send * seg


def sos_lp(fc, order=2):
    return signal.butter(order, fc, 'low', fs=SR, output='sos')


def sos_hp(fc, order=2):
    return signal.butter(order, fc, 'high', fs=SR, output='sos')


def sos_bp(lo, hi, order=2):
    return signal.butter(order, [lo, hi], 'band', fs=SR, output='sos')


def filt(sos, x):
    return signal.sosfilt(sos, x, axis=-1)


def tvec(dur):
    return np.arange(int(dur * SR)) / SR


def cosramp(x):
    x = np.clip(x, 0, 1)
    return 0.5 - 0.5 * np.cos(np.pi * x)


def declick(x, ms=3):
    n = min(len(x) // 2, int(ms * SR / 1000))
    if n > 0:
        r = np.linspace(0, 1, n)
        x[:n] *= r
        x[-n:] *= r[::-1]
    return x


def saw(freq, n, phase0=0.0):
    """Band-limited saw (polyBLEP)."""
    dt = freq / SR
    ph = (phase0 + dt * np.arange(n)) % 1.0
    y = 2 * ph - 1
    m = ph < dt
    u = ph[m] / dt
    y[m] -= u + u - u * u - 1
    m = ph > 1 - dt
    u = (ph[m] - 1) / dt
    y[m] -= u * u + u + u + 1
    return y


def eIO(x):
    x = np.clip(x, 0, 1)
    return np.where(x < .5, 4 * x ** 3, 1 - (-2 * x + 2) ** 3 / 2)


def swept_noise(dur, fc_of_u, bw_oct=1.0, seed=None):
    """Noise through a band-pass whose centre follows fc_of_u(u), u = 0 … 1 over the sound."""
    g = np.random.default_rng(seed) if seed is not None else rng
    n = int(dur * SR)
    x = g.standard_normal(n + 2048)
    f, tt, Z = signal.stft(x, SR, nperseg=1024, noverlap=768)
    fc = np.maximum(40, fc_of_u(np.clip(tt / dur, 0, 1)))
    lf = np.log2(np.maximum(f, 20))[:, None]
    G = np.exp(-0.5 * ((lf - np.log2(fc)[None, :]) / (bw_oct / 2)) ** 2)
    _, y = signal.istft(Z * G, SR, nperseg=1024, noverlap=768)
    y = y[:n]
    return y / (np.sqrt(np.mean(y ** 2)) + 1e-9)


# ---------------------------------------------------------------- instruments
def mallet(f, dur=0.8, decay=0.35, bright=1.0):
    """Soft FM mallet: warm body, a glassy 4th partial on the attack."""
    t = tvec(dur)
    idx = 1.6 * bright * np.exp(-t / 0.05)
    body = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
    bell = 0.22 * bright * np.sin(2 * np.pi * 4.0 * f * t) * np.exp(-t / 0.07)
    y = (body + bell) * (1 - np.exp(-t / 0.0015)) * np.exp(-t / decay)
    return declick(y, 2)


def kick():
    t = tvec(0.55)
    f = 44 + 86 * np.exp(-t / 0.032)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.2)
    y = np.tanh(1.6 * y) / np.tanh(1.6)
    click = filt(sos_hp(2500), rng.standard_normal(len(t))) * np.exp(-t / 0.0018) * 0.18
    return declick((y + click) * (1 - np.exp(-t / 0.0008)), 2)


def hat(open_=False):
    t = tvec(0.35 if open_ else 0.09)
    x = filt(sos_hp(7200, 4), rng.standard_normal(len(t)))
    x = x / np.sqrt(np.mean(x ** 2))
    return declick(x * np.exp(-t / (0.09 if open_ else 0.018)), 1)


def snap():
    t = tvec(0.25)
    x = filt(sos_bp(1300, 4200), rng.standard_normal(len(t)))
    x = x / np.sqrt(np.mean(x ** 2)) * np.exp(-t / 0.045)
    body = 0.5 * np.sin(2 * np.pi * 240 * t) * np.exp(-t / 0.03)
    return declick((x + body) * (1 - np.exp(-t / 0.0007)), 1)


def tick(f=4200, dec=0.004):
    t = tvec(0.04)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t / dec)
    y += 0.35 * filt(sos_hp(3000), rng.standard_normal(len(t))) * np.exp(-t / 0.0012)
    return declick(y, 0.5)


def thud(f0=78):
    t = tvec(0.6)
    f = f0 * 0.62 + f0 * 0.6 * np.exp(-t / 0.04)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    n = filt(sos_lp(900), rng.standard_normal(len(t))) * np.exp(-t / 0.03) * 0.25
    return declick(y + n, 2)


def impact(dur=3.0):
    t = tvec(dur)
    f = 41 + 58 * np.exp(-t / 0.07)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.7) * (1 - np.exp(-t / 0.002))
    nz = filt(sos_lp(1400), rng.standard_normal(len(t)))
    nz = nz / np.sqrt(np.mean(nz[:SR // 10] ** 2)) * np.exp(-t / 0.16) * 0.35
    return declick(np.tanh(1.3 * (boom + nz)), 3)


def whoosh(dur, lo=380, hi=2600, peak=.55):
    u = np.linspace(0, 1, int(dur * SR))
    fc = lambda v: lo * (hi / lo) ** np.where(v < peak, v / peak, 1 - (v - peak) / (1 - peak) * .7)
    x = swept_noise(dur, fc, 1.1)
    env = np.where(u < peak, (u / peak) ** 2.2, np.exp(-(u - peak) / (1 - peak) * 3.2))
    return declick(x * env, 3)


def riser(dur, lo=250, hi=7000):
    u = np.linspace(0, 1, int(dur * SR))
    x = swept_noise(dur, lambda v: lo * (hi / lo) ** v, 0.9)
    return declick(x * u ** 2.4, 8)


# ---------------------------------------------------------------- harmony
CH = {  # pad voicing, sub-bass root
    'Dm9':    ([50, 57, 60, 64, 65], 38),
    'Bbmaj9': ([46, 53, 57, 60, 62], 34),
    'Fadd9':  ([53, 57, 60, 67, 69], 41),
    'C6':     ([52, 55, 60, 64, 69], 36),
    'Bbmaj7': ([50, 53, 57, 58, 62], 34),
    'F/A':    ([53, 57, 60, 65, 69], 33),
    'C/E':    ([52, 55, 60, 64, 67], 40),
    'Gm9':    ([55, 58, 62, 65, 69], 31),
    'Csus':   ([53, 55, 60, 65, 67], 36),
    'Fbig':   ([41, 48, 53, 57, 60, 67, 69, 72], 29),
}
# (start, chord, pad cutoff Hz, pad level, attack s)
CHORDS = [
    (0.0, 'Dm9', 650, .95, 2.2),      # opening: grid and logo
    (8.5, 'Bbmaj9', 1000, 1.0, .35),   # "then built"
    (11.5, 'Fadd9', 1500, .9, .5),     # home page
    (15.5, 'C6', 1600, .9, .6),
    (19.5, 'Dm9', 1700, .9, .5),       # photography
    (23.5, 'Bbmaj7', 1700, .9, .6),
    (26.5, 'F/A', 1800, .85, .5),      # the work
    (31.0, 'C/E', 1800, .85, .6),
    (36.0, 'Dm9', 1600, .85, .5),      # project page
    (40.0, 'Bbmaj7', 1700, .85, .6),
    (44.0, 'Gm9', 1900, .9, .5),       # scope
    (48.5, 'Csus', 2100, .9, .5),
    (51.0, 'Dm9', 800, .95, .8),       # 3D: breakdown
    (55.0, 'Bbmaj7', 950, .95, .8),
    (58.0, 'Fadd9', 2300, 1.0, .25),   # built
    (61.0, 'Bbmaj9', 1300, .85, .6),   # phone
    (63.5, 'C6', 1400, .85, .6),
    (67.2, 'Fbig', 2400, 1.15, .12),   # end card
]
SEG = [(c[0], (CHORDS[i + 1][0] if i + 1 < len(CHORDS) else DUR), *c[1:]) for i, c in enumerate(CHORDS)]


def chord_at(t):
    for a, b, name, *_ in SEG:
        if a <= t < b:
            return name
    return SEG[-1][2]


def in_ranges(t, ranges):
    return any(a <= t < b for a, b in ranges)


# ---------------------------------------------------------------- pad and bass
for a, b, name, cut, lvl, att in SEG:
    notes, root = CH[name]
    rel = 1.3 if b < DUR else 0.01
    n = int((b - a + rel) * SR)
    t = np.arange(n) / SR
    env = cosramp(t / att) * (1 - cosramp((t - (b - a)) / rel))
    out = np.zeros((2, n))
    for m in notes:
        for d, pn in zip((-9, -3, 3, 9), (-.6, -.2, .2, .6)):
            out += pan2(saw(midi(m) * 2 ** (d / 1200), n, rng.random()), pn)
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * t / 5.3 + rng.random() * 6)
    dark, bright = filt(sos_lp(cut * .6), out), filt(sos_lp(cut * 1.5), out)
    out = dark * (1 - .45 * lfo) + bright * .45 * lfo
    put('pad', a, out * env * lvl * 0.098 / np.sqrt(len(notes)), send=.55)

    if a >= 8.5:                                            # sub enters on "then built"
        subs = [root] if name != 'Fbig' else [29, 41]
        for r in subs:
            y = np.sin(2 * np.pi * midi(r) * t)
            y = np.tanh(1.8 * y) / np.tanh(1.8)
            put('bass', a, y * cosramp(t / .06) * (1 - cosramp((t - (b - a)) / max(rel, .3))) * (0.14 if name != 'Fbig' else .10))

# offbeat pluck bass
PLUCK_BASS = [(15.5, 51.0), (58.0, 61.0)]
for k in range(int(DUR / (BEAT / 2))):
    tb = k * BEAT / 2
    if k % 2 == 1 and in_ranges(tb, PLUCK_BASS):
        root = CH[chord_at(tb)][1]
        tt = tvec(.26)
        y = filt(sos_lp(750), saw(midi(root + 12), len(tt), rng.random()))
        y = declick(y * np.exp(-tt / .1) * (1 - np.exp(-tt / .003)), 3)
        put('bass', tb, y, gain=.09)

# ---------------------------------------------------------------- drums
KICKS = [k * BEAT for k in range(int(DUR / BEAT)) if in_ranges(k * BEAT, [(11.5, 51.0), (58.0, 61.0)])]
KICKS += [61.0 + i for i in range(6)]                      # phone: half time
K = kick()
for tk in KICKS:
    put('kick', tk, K, gain=.27 if tk < 61 else .18)

for k in range(int(DUR / 0.125)):
    th = k * 0.125
    eighth, off = k % 2 == 0, k % 4 == 2
    v = 0.0
    if in_ranges(th, [(15.5, 51.0), (58.0, 66.5)]) and off:
        v = .144
    elif in_ranges(th, [(26.5, 36.0), (44.0, 51.0), (58.0, 61.0)]):
        v = .067 if eighth else .038
    if v:
        put('hats', th, hat(), pan=.25 if k % 2 else -.1, gain=v * (1 + .15 * (rng.random() - .5)))
    if off and in_ranges(th, [(19.5, 51.0), (58.0, 61.0)]):
        put('hats', th, hat(True), pan=-.3, gain=.043)

SN = snap()
for i in range(int(DUR)):
    ts = float(i)
    if in_ranges(ts, [(20.0, 51.0), (58.5, 61.0)]):
        put('drums', ts, SN, pan=.05, gain=.16, send=.35)
for ts in np.arange(61.5, 66.0, 1.0):
    put('drums', ts, SN, pan=.05, gain=.13, send=.4)

# sidechain: pad and bass duck under each kick
duck = np.zeros(N)
for tk in KICKS:
    i = int(tk * SR)
    duck[i:i + 1] = 1
duck = signal.lfilter([1], [1, -np.exp(-1 / (0.16 * SR))], duck)
duck = signal.lfilter([1 - np.exp(-1 / (0.004 * SR))], [1, -np.exp(-1 / (0.004 * SR))], np.minimum(duck, 1)) * 1.0
BUS['pad'] *= 1 - .35 * np.clip(duck, 0, 1)
BUS['bass'] *= 1 - .55 * np.clip(duck, 0, 1)

# ---------------------------------------------------------------- keys: arpeggio and cues
PAT = [0, 2, 4, 2, 1, 3, 4, 3, 0, 2, 4, 2, 1, 3, 2, 4]
for k in range(int(DUR / 0.125)):
    ta = k * 0.125
    six = in_ranges(ta, [(26.5, 36.0), (44.0, 51.0), (58.0, 61.0)])
    eig = in_ranges(ta, [(36.0, 44.0), (61.0, 66.5)]) and k % 2 == 0
    if not (six or eig):
        continue
    tones = sorted(m + 12 for m in CH[chord_at(ta)][0] if m >= 52)[:5]
    m = tones[PAT[k % 16] % len(tones)]
    vel = 1.0 if k % 4 == 0 else (.72 if k % 2 == 0 else .5)
    vel *= 1 + .12 * (rng.random() - .5)
    lvl = .125 if ta < 61 else .09
    put('keys', ta, mallet(midi(m), .5, .16, .65), pan=(PAT[k % 16] - 2) * .18, gain=lvl * vel, send=.3)

# opening: logo, wordmark, lockup, label
put('keys', 2.08, mallet(midi(62), 2.2, .9, .8), pan=-.1, gain=.14, send=.6)
put('keys', 2.14, mallet(midi(69), 2.2, .9, .8), pan=.1, gain=.11, send=.6)
put('keys', 2.20, mallet(midi(76), 2.2, .9, .8), pan=.2, gain=.08, send=.6)
put('keys', 3.6, mallet(midi(81), 1.6, .7, .5), pan=.35, gain=.06, send=.7)
put('keys', 4.35, mallet(midi(88), 1.6, .7, .5), pan=0, gain=.045, send=.8)

# the idea: one note per group of pen strokes (walls, columns, shelves, floor, lights)
for g, m in enumerate([69, 74, 76, 81, 88]):
    put('keys', 6.3 + g * .34, mallet(midi(m), 1.6, .6, .7), pan=-.5 + g * .25, gain=.075 - g * .006, send=.6)

# hero switches flagship
put('keys', 16.3, mallet(midi(76), 1.2, .5, .6), pan=.4, gain=.06, send=.5)

# keynote tags pop, then the pairing highlight
for i, m in enumerate([81, 84, 86, 88]):
    put('keys', 37.3 + i * .9 + .42, mallet(midi(m), 1.0, .4, .9), pan=[.35, -.45, .5, -.1][i], gain=.085, send=.45)
for i in range(4):
    put('fx', 41.2 + i * .7, tick(3600, .005), pan=[.35, -.45, .5, -.1][i], gain=.05)

# scope slabs fill, left to right, rising; concept goes back to the brand
for i, m in enumerate([67, 70, 74, 77, 81]):
    s = 45.3 + i * .42
    put('keys', s + .05, mallet(midi(m), 1.2, .45, .8), pan=-.2 + i * .1, gain=.09, send=.4)
    w = swept_noise(.55, lambda v: 900 * 3 ** v, 1.0) * np.sin(np.pi * np.linspace(0, 1, int(.55 * SR))) ** 2
    put('fx', s, declick(w), pan=np.linspace(-.6, .6, len(w)), gain=.018)
put('keys', 48.55, mallet(midi(62), 1.6, .6, .5), pan=-.5, gain=.08, send=.5)

# 3D: each layer lands on the beat, a floor higher
for i, m in enumerate([50, 57, 62, 65, 69, 74]):
    tl = 52.5 + i
    put('drums', tl - .02, thud(70 + i * 6), gain=.30, send=.25)
    put('keys', tl, mallet(midi(m), 1.4, .55, .7), pan=-.3 + i * .12, gain=.14, send=.45)

# end card: the chord is struck as the red block cuts in, headline and labels answer
for i, m in enumerate([65, 69, 72, 79, 81]):
    put('keys', 67.2 + i * .045, mallet(midi(m), 4.5, 1.6, .9), pan=-.3 + i * .15, gain=.10, send=.7)
put('keys', 67.75, mallet(midi(84), 3.0, 1.2, .5), pan=.2, gain=.05, send=.8)
put('fx', 68.42, tick(3000, .006), pan=-.1, gain=.03)
put('fx', 68.62, tick(3300, .006), pan=.1, gain=.03)

# ping-pong delay on the keys (dotted eighth)
D = int(.375 * SR)
cur, wet = BUS['keys'].copy(), np.zeros((2, N))
lp = sos_lp(3800)
for _ in range(5):
    cur = filt(lp, cur)[::-1] * .36
    sh = np.zeros_like(cur)
    sh[:, D:] = cur[:, :-D]
    cur = sh
    wet += cur
BUS['keys'] += .55 * wet
BUS['send'] += .25 * wet

# ---------------------------------------------------------------- sound design
# grid lines drawing in (0.1 s + i × 35 ms): a light pen tick for each, panned to its position
for i in range(23):
    x = (i + 1) * 120 / 1920 if i < 15 else .5
    put('fx', .1 + i * .035, tick(3000 + 3000 * rng.random(), .003), pan=(x * 2 - 1) * .8, gain=.03)

# the red block and the lockup wipe in left to right
w = whoosh(1.0, 300, 2400, .5)
put('fx', 1.4, w, pan=np.linspace(-.7, .7, len(w)), gain=.05, send=.3)
put('fx', 1.9, impact(2.5), gain=.22, send=.5)
w = whoosh(1.0, 400, 1800, .5)
put('fx', 3.0, w, pan=np.linspace(-.2, .6, len(w)), gain=.025, send=.3)

# pen on paper for each stroke of the trace (same timing as drawTrace in motion.html)
TRACE = [
    ['M0 100 L415 112', 'M578 150 L856 168', 'M862 165 L864 570', 'M1395 40 L1395 700', 'M840 128 L1395 38', 'M850 146 L1395 68', 'M0 845 L380 792'],
    ['M415 112 L415 648', 'M578 125 L578 622', 'M415 112 Q497 98 578 125'],
    ['M0 245 L398 257', 'M0 383 L400 380', 'M0 520 L402 503', 'M405 105 L408 640', 'M583 258 L848 268', 'M586 372 L848 374', 'M588 482 L850 470', 'M910 272 L1392 212', 'M912 373 L1390 358', 'M915 470 L1388 484'],
    ['M0 655 L430 620', 'M596 590 L876 566', 'M880 566 L1382 628', 'M1380 628 L1378 802', 'M1050 760 L1378 802', 'M62 858 L380 800', 'M62 858 L215 1063', 'M1190 818 L1478 884', 'M1478 884 L1228 1063'],
    [[293, 86], [353, 90], [540, 110], [697, 128], [740, 134]],
]


def pen(t0, dur, x0, x1, gain, phone=False):
    u = np.linspace(0, 1, int(dur * SR))
    speed = np.where(u < .5, 12 * u ** 2, 12 * (1 - u) ** 2) / 3          # derivative of eIO
    x = swept_noise(dur, lambda v: 2600 + 1600 * v, 1.3)
    put('fx', t0, declick(x * speed ** 1.3), pan=np.linspace(x0, x1, len(u)) * .8, gain=gain * (.5 if phone else 1), send=.15)


for g, grp in enumerate(TRACE):
    for k, d in enumerate(grp):
        xs = [float(v) for v in re.findall(r'-?\d+', d)[0::2]] if isinstance(d, str) else [d[0], d[0]]
        x0, x1 = xs[0] / 800 - 1, xs[-1] / 800 - 1
        pen(6.3 + g * .34 + k * .07, .9, x0, x1, .011)
        pen(61.6 + g * .16 + k * .03, .5, (x0 * .2 + .45), (x1 * .2 + .45), .008, phone=True)

# "then built": a rising breath, then the hit as the photo fills
put('fx', 7.25, riser(1.25, 300, 5000), pan=-.2, gain=.03, send=.3)
put('fx', 8.5, impact(3.0), gain=.30, send=.55)

# hero settles into the home page
w = whoosh(1.3, 250, 1500, .6)
put('fx', 10.25, w, pan=np.linspace(-.3, .5, len(w)), gain=.035, send=.3)

# every scene wipe cuts right to left
for a in (19.1, 26.1, 35.6, 43.6, 50.6, 60.6, 66.1):
    w = whoosh(1.1, 420, 3000, .45)
    put('fx', a - .05, w, pan=np.linspace(.8, -.8, len(w)), gain=.055, send=.3)

# photography: the divider slides left, right, left
for a, b, p0, p1 in ((20.1, 21.9, .8, -.3), (22.6, 23.7, -.3, .4), (24.1, 25.2, .4, -.1)):
    w = swept_noise(b - a, lambda v: 600 + 900 * np.sin(np.pi * v), 1.4) * np.sin(np.pi * np.linspace(0, 1, int((b - a) * SR))) ** 2
    put('fx', a, declick(w), pan=np.linspace(p0, p1, len(w)), gain=.02, send=.2)


# register: a tick each time the preview swaps, and the click (same cursor path as motion.html)
def path(keys, t):
    if t <= keys[0][0]:
        return keys[0][1:]
    for i in range(1, len(keys)):
        if t <= keys[i][0]:
            a, b = keys[i - 1], keys[i]
            k = float(eIO((t - a[0]) / (b[0] - a[0])))
            return (a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k)
    return keys[-1][1:]


CUR5 = [[27.5, 1500, 920], [28.3, 640, 466], [29.3, 640, 466], [29.8, 660, 538], [30.7, 660, 538], [31.2, 630, 610], [32.1, 630, 610], [32.6, 670, 682], [33.5, 670, 682], [34.1, 610, 466], [35.6, 610, 466]]


def row_at(y):
    for i in range(8):
        if 428 + i * 72 <= y < 500 + i * 72:
            return i
    return -1


swaps, last, t = [], -1, 27.5
while t < 36:
    r = row_at(path(CUR5, t)[1])
    if r != last and 0 <= r < 4:
        swaps.append((t, r))
    last = r
    t += 1 / 120
swaps = [q for i, q in enumerate(swaps) if i == len(swaps) - 1 or swaps[i + 1][0] - q[0] > .3]
for ts, r in swaps:
    put('fx', ts, tick(3800 + r * 250, .0045), pan=.35, gain=.06)
put('fx', 34.95, tick(2400, .006), pan=-.1, gain=.09)
put('fx', 35.05, tick(2900, .004), pan=-.1, gain=.06)

# scope: build into the 3D wipe
put('fx', 49.5, riser(1.1, 400, 6000), pan=.2, gain=.025, send=.3)

# 3D: swell into "built", then the layers pull apart
put('fx', 57.1, riser(.9, 200, 3000), gain=.03, send=.4)
put('fx', 58.0, impact(3.0), gain=.26, send=.5)
put('fx', 59.1, riser(1.45, 250, 7500), pan=-.1, gain=.035, send=.35)

# end card
put('fx', 66.55, riser(.65, 300, 4000), gain=.025, send=.3)
put('fx', 67.2, impact(4.0), gain=.32, send=.6)


# ---------------------------------------------------------------- space
def make_ir(dur=3.6, rt_lo=2.8, rt_hi=1.2):
    t = tvec(dur)
    ir = np.zeros((2, len(t)))
    for c in range(2):
        nz = rng.standard_normal(len(t))
        lo = filt(sos_lp(1600), nz)
        hi = nz - lo
        ir[c] = lo * np.exp(-6.91 * t / rt_lo) + .55 * hi * np.exp(-6.91 * t / rt_hi)
    ir *= cosramp(t / .004)
    ir = np.pad(ir, ((0, 0), (int(.024 * SR), 0)))
    return ir / np.sqrt(np.sum(ir ** 2) / 2)


IR = make_ir()
send = filt(sos_hp(180), filt(sos_lp(7000), BUS['send']))
wet = np.vstack([signal.fftconvolve(send[c], IR[c])[:N] for c in range(2)])

mix = BUS['pad'] + BUS['bass'] + BUS['kick'] + BUS['hats'] + BUS['drums'] + BUS['keys'] + BUS['fx'] + .4 * wet
mix = filt(sos_hp(26), mix)

# reference level: a groove section sits at -18 dBFS RMS, then gentle glue (2:1 above -15 dBFS)
ref = np.sqrt(np.mean(mix[:, int(27 * SR):int(35 * SR)] ** 2))
mix *= 10 ** (-18 / 20) / ref
lvl = np.sqrt(signal.lfilter([1 - np.exp(-1 / (.08 * SR))], [1, -np.exp(-1 / (.08 * SR))], np.mean(mix ** 2, axis=0)) + 1e-12)
db = 20 * np.log10(lvl)
gain_db = np.minimum(0, (-15 - db) * .5)
mix *= 10 ** (gain_db / 20)

# fade in, fade out with the picture
tt = np.arange(N) / SR
mix *= cosramp(tt / .02) * (1 - cosramp((tt - 70.3) / 1.65))



def lufs(x):
    """Integrated loudness, ITU-R BS.1770-4 (K-weighting, 400 ms blocks, absolute and relative gates)."""
    k = signal.lfilter([1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585], x, axis=-1)
    k = signal.lfilter([1.0, -2.0, 1.0], [1, -1.99004745483398, 0.99007225036621], k, axis=-1)
    blk, hop = int(.4 * SR), int(.1 * SR)
    z = np.array([np.mean(k[:, i:i + blk] ** 2, axis=1).sum() for i in range(0, k.shape[1] - blk, hop)])
    l = -0.691 + 10 * np.log10(z + 1e-12)
    z = z[l > -70]
    rel = -0.691 + 10 * np.log10(np.mean(z)) - 10
    z = z[-0.691 + 10 * np.log10(z) > rel]
    return -0.691 + 10 * np.log10(np.mean(z))


# -16 LUFS integrated, peaks held under -2 dBFS by a soft knee that only touches the impacts
TARGET, CEIL, KNEE = -16.0, 10 ** (-2 / 20), 10 ** (-5 / 20)
mix *= 10 ** ((TARGET - lufs(mix)) / 20)
a = np.abs(mix)
over = a > KNEE
mix[over] = np.sign(mix[over]) * (KNEE + (CEIL - KNEE) * np.tanh((a[over] - KNEE) / (CEIL - KNEE)))
print(f'loudness {lufs(mix):.1f} LUFS, peak {20 * np.log10(np.max(np.abs(mix))):.1f} dBFS, samples in knee {int(over.sum())}')

out = sys.argv[1] if len(sys.argv) > 1 else 'score.wav'
pcm = (np.clip(mix, -1, 1).T * 32767).astype('<i2')
with wave.open(out, 'wb') as f:
    f.setnchannels(2)
    f.setsampwidth(2)
    f.setframerate(SR)
    f.writeframes(pcm.tobytes())

# mix report: bus levels (dB, relative) in a few sections
def db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


BUS['reverb'] = .4 * wet
for lo, hi in ((0, 6), (6, 11.5), (27, 35), (51, 57.5), (61, 66), (67.2, 70)):
    sl = slice(int(lo * SR), int(hi * SR))
    print(f'{lo:5.1f}-{hi:5.1f} s  ' + '  '.join(f'{k} {db(BUS[k][:, sl]):6.1f}' for k in ('pad', 'bass', 'kick', 'hats', 'drums', 'keys', 'fx', 'reverb')))
print('wrote', out)
