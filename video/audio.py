"""Synthesise the story's soundtrack: a dark, minimal pulse plus sound design on every beat of the picture.

  python3 video/render.py events video/events.json     # when the held requests burst
  python3 video/audio.py OUT.wav [video/events.json]

Every sound is generated here, so there is nothing to license. Times match video/index.html (S).
The result is loudness-normalised for Instagram (-14 LUFS, -1.5 dBTP) with ffmpeg's two-pass loudnorm.
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

SR = 48000
DUR = 24.6
N = int(SR * DUR)
rng = np.random.default_rng(7)

drums, bass_bus, keys, sfx, send = (np.zeros((N, 2)) for _ in range(5))
kicks = []  # real times, for the sidechain


def add(buf, t0, sig, gain=1.0, pan=0.0, rev=0.0):
    """Mix a mono or stereo signal in at t0; `rev` also sends it to the reverb."""
    i = int(t0 * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    if sig.ndim == 1:
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        sig = np.stack([sig * l, sig * r], axis=1) * 1.414
    buf[i:i + len(sig)] += sig * gain
    if rev:
        send[i:i + len(sig)] += sig * gain * rev


def tt(d):
    return np.arange(int(d * SR)) / SR


def attack(t, ms=3):
    return np.minimum(1, t / (ms / 1000))


def svf(x, fc, q=0.8, mode="bp"):
    """Chamberlin state-variable filter with a per-sample cutoff."""
    f = 2 * np.sin(np.pi * np.minimum(np.broadcast_to(fc, x.shape), SR / 6) / SR)
    damp = 1 / q
    lp = bp = 0.0
    y = np.empty_like(x)
    for i in range(len(x)):
        hp = x[i] - lp - damp * bp
        bp += f[i] * hp
        lp += f[i] * bp
        y[i] = bp if mode == "bp" else lp
    return y


# ---------- instruments ----------
def kick():
    t = tt(0.5)
    f = 46 + 95 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6.5) * attack(t, 1)


def hat():
    t = tt(0.07)
    return np.diff(rng.standard_normal(len(t)), prepend=0) * np.exp(-t * 60) * 0.11 * attack(t, 1)


def clap():
    t = tt(0.3)
    n = svf(rng.standard_normal(len(t)), 1600, q=1.2)
    env = sum(np.exp(-np.maximum(t - d, 0) * 40) * (t >= d) for d in (0, 0.011, 0.022)) / 3 + 0.5 * np.exp(-t * 14)
    return n * env * 0.5


def pluck(f, d=0.45):
    t = tt(d)
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) * np.exp(-t * 18) + 0.1 * np.sin(6 * np.pi * f * t) * np.exp(-t * 30)
    return s * np.exp(-t * 8) * attack(t, 2)


def bass(f, d=0.26):
    t = tt(d)
    s = np.sin(2 * np.pi * f * t) + 0.22 * np.sin(4 * np.pi * f * t) + 0.06 * np.sin(6 * np.pi * f * t)
    return s * np.exp(-t * 5) * attack(t, 6) * np.minimum(1, (d - t) / 0.03)


def pad(freqs, d, rel=0.5):
    """Warm, slightly detuned saw pad, rolled off so it sits behind everything."""
    t = tt(d)
    s = np.zeros(len(t))
    for f in freqs:
        for det in (-0.005, 0.0, 0.005):
            for k in range(1, 9):
                s += np.sin(2 * np.pi * f * (1 + det) * k * t + k) / k * math.exp(-k / 2.5)
    env = np.minimum(1, t / 0.4) * np.clip((d - t) / rel, 0, 1)
    return s / (len(freqs) * 3 * 1.6) * env


def whoosh(d, shape, f0=180.0, f1=1300.0, sub=0.35):
    """Air that follows a move: low-passed noise (no hiss) with a soft sub sweep for weight.
    'bell' peaks mid-move, 'decay' starts fast and settles, 'rise' accelerates into a cut.
    It pans across as it passes."""
    t = tt(d)
    x = t / d
    if shape == "bell":
        env, fc = np.sin(np.pi * x) ** 2, f0 + (f1 - f0) * np.sin(np.pi * x)
    elif shape == "decay":
        env, fc = attack(t, 25) * np.exp(-x * 4.0), f1 + (f0 - f1) * x
    else:
        env, fc = x ** 2.2, f0 * (f1 / f0) ** x
    air = svf(rng.standard_normal(len(t)), fc, q=0.6, mode="lp")
    air /= np.max(np.abs(air)) + 1e-9
    low = np.sin(2 * np.pi * np.cumsum(95 - 45 * x) / SR)  # 95 -> 50 Hz
    s = (air + sub * low) * env
    pan = np.clip(-0.5 + 1.0 * x, -1, 1)
    return np.stack([s * np.cos((pan + 1) * np.pi / 4), s * np.sin((pan + 1) * np.pi / 4)], axis=1) * 1.414


def riser(d):
    t = tt(d)
    x = t / d
    tone = np.sin(2 * np.pi * np.cumsum(110 * 3 ** x) / SR) * 0.12 * x ** 2  # 110 -> 330 Hz, under the air
    return whoosh(d, "rise", 160, 1800, sub=0.2) + np.stack([tone, tone], axis=1)


def pop(f0, g=1.0):
    t = tt(0.14)
    f = f0 * (1 + 0.5 * np.minimum(1, t / 0.035))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 34) * attack(t, 1.5) * 0.6 * g


def glide(f0, f1, d):
    t = tt(d)
    return np.sin(2 * np.pi * np.cumsum(f0 * (f1 / f0) ** (t / d)) / SR) * np.sin(np.pi * t / d)


def tick(f=2600):
    t = tt(0.05)
    return np.sin(2 * np.pi * f * t) * np.exp(-t * 90) * attack(t, 0.5)


def bell(f, d=1.4):
    t = tt(d)
    s = np.sin(2 * np.pi * f * t) + 0.22 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 7) + 0.1 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 12)
    return s * np.exp(-t * 3.6) * attack(t, 1)


def thump(depth=1.0):
    t = tt(1.0)
    f = 34 + 70 * np.exp(-t * 9)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.4)
    air = svf(rng.standard_normal(len(t)), 900, q=0.7, mode="lp") * np.exp(-t * 14) * 0.5
    return (body * depth + air) * attack(t, 2)


# ---------- timeline (index.html S) ----------
S = dict(helper=3.2, ask=6.4, covers=10.0, chart=13.4, seal=16.8, phone=19.4, end=22.35, done=24.6)
BEAT = 0.6  # 100 bpm; each section with drums starts its own grid on its cut

# ---------- music: A minor, Am F Dm E, dark and sparse ----------
CH = {
    "Am": (55.0, [220.0, 261.63, 329.63, 440.0]), "F": (43.65, [174.61, 220.0, 261.63, 349.23]),
    "Dm": (73.42, [146.83, 220.0, 293.66, 349.23]), "E": (82.41, [164.81, 207.65, 246.94, 329.63]),
    "Am9": (55.0, [220.0, 261.63, 329.63, 493.88]),
}


def section(start, end, chords, kick=True, clap=False, hats=True, arp=True, bassline=True):
    """Bars of four beats from `start`, cut off at `end`."""
    bar = 4 * BEAT
    b = 0
    while start + b * bar < end:
        root, voicing = CH[chords[b % len(chords)]]
        t0 = start + b * bar
        add(keys, t0, pad(voicing, min(bar + 0.4, end - t0 + 0.6)), 0.26, rev=0.3)
        for e in range(8):
            te = t0 + e * BEAT / 2
            if te >= end:
                break
            if bassline and e % 2 == 0:
                add(bass_bus, te, bass(root * 2, 0.32), 0.55)
            if arp:
                note = [voicing[0], voicing[2], voicing[1], voicing[3]][e % 4] * 2
                add(keys, te, pluck(note, 0.5), 0.09, pan=(-0.5 if e % 2 else 0.5), rev=0.45)
            if kick and e % 2 == 0:
                add(drums, te, kick_(), 0.85)
                kicks.append(te)
                if clap and e in (2, 6):
                    add(drums, te, clap_(), 0.7, rev=0.3)
            if hats and e % 2 == 1:
                add(drums, te, hat(), 0.8, pan=0.3)
        b += 1


kick_, clap_ = kick, clap
# hook + helper: a low drone under the stream, a tick like a clock
add(sfx, 0.0, thump(0.9), 0.6, rev=0.3)  # an impact on the first frame
add(keys, 0.0, pad([55.0, 82.41, 110.0], S["ask"] + 0.4, rel=0.8), 0.42, rev=0.2)
for k in range(int(S["ask"] / BEAT)):
    add(drums, k * BEAT, tick(1500), 0.08, pan=0.2)
# the ask and the covers: the pulse comes in
section(S["ask"], S["covers"], ["Am", "F"], clap=False)
section(S["covers"], S["chart"], ["Dm", "E"], clap=True)
# the chart: lighter, the arp alone over a pad
section(S["chart"], S["seal"], ["Am", "F"], kick=True, hats=True, bassline=False)
# the seal: drone and a slow heartbeat
add(keys, S["seal"], pad([55.0, 82.41, 130.81], S["phone"] - S["seal"] + 0.6, rel=0.8), 0.34, rev=0.4)
for k in range(4):
    add(drums, S["seal"] + 0.3 + k * 0.65, thump(0.7), 0.5 if k % 2 == 0 else 0.36)
# the explorer: the groove returns; the end: it resolves on the wordmark
section(S["phone"], S["end"], ["Am", "F", "Dm", "E"], clap=True)
add(keys, S["end"] + 0.45, pad(CH["Am9"][1], S["done"] - S["end"] - 0.45, rel=1.6), 0.36, rev=0.5)
add(bass_bus, S["end"] + 0.45, bass(55.0 * 2, 1.4), 0.6)
for e in range(6):
    add(keys, S["end"] + 0.45 + e * BEAT / 2, pluck([440.0, 523.25, 659.25, 987.77, 659.25, 523.25][e], 0.9), 0.11, pan=(-0.4 if e % 2 else 0.4), rev=0.55)

# ---------- sound design ----------
# the stream: soft air while requests flow (hook, helper, ask), and again under the end card
air = whoosh(S["covers"] + 0.4, "bell", 120, 520, sub=0.0)
add(sfx, 0.0, air, 0.16)
add(sfx, S["end"], whoosh(S["done"] - S["end"], "bell", 120, 480, sub=0.0), 0.12)
# the ring assembles from the stream, then the informant lights in the slit
add(sfx, S["helper"] + 0.1, riser(1.1), 0.35, rev=0.3)
add(sfx, S["helper"] + 1.25, thump(0.8), 0.55, rev=0.3)
add(sfx, S["helper"] + 1.45, bell(880.0, 1.6), 0.12, rev=0.5)


def crackle(n=1):
    """A held request breaking into amber dust: a short burst of grains."""
    t = tt(0.22)
    out = np.zeros(len(t))
    for _ in range(4 + 3 * n):
        g = int(rng.random() * 0.12 * SR)
        d = int((0.008 + rng.random() * 0.02) * SR)
        seg = svf(rng.standard_normal(d), 900 + rng.random() * 900, q=1.0) * np.exp(-np.arange(d) / SR * 120)
        out[g:g + d] += seg[: len(out) - g]
    return out / (np.max(np.abs(out)) + 1e-9)


events = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else []
last = -1.0
for e in sorted(events):
    if e - last < 0.08:   # a cluster sounds as one
        continue
    n = sum(1 for x in events if 0 <= x - e < 0.08)
    add(sfx, e, crackle(n), min(0.45, 0.16 + 0.03 * n), pan=-0.25, rev=0.25)
    last = e
# the covers: a pluck as each lane draws in
for i, f in enumerate([220.0, 261.63, 293.66, 329.63, 392.0, 440.0, 523.25]):
    add(sfx, S["covers"] + 0.25 + i * 0.12, pluck(f, 0.7), 0.16, pan=-0.3 + i * 0.1, rev=0.4)
add(sfx, S["covers"] - 0.05, whoosh(0.5, "bell", 160, 900), 0.3)
# the chart: a tick per request as the lines draw; amber points ring a little brighter
show = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "study.json")))["showcase"]
n = len(show["holistic"])
for j in range(n):
    u = j / (n - 1)
    # the draw is eased in-out over 0.9..2.5 s into the chart; invert the ease to find each point's time
    lo, hi = 0.0, 1.0
    for _ in range(30):
        mid = (lo + hi) / 2
        v = 4 * mid ** 3 if mid < 0.5 else 1 - (-2 * mid + 2) ** 3 / 2
        lo, hi = (mid, hi) if v < u else (lo, mid)
    at = S["chart"] + 0.9 + 1.6 * lo
    hot = max(show["holistic"][j], show["narrow"][j]) > 60
    add(sfx, at, bell(660.0, 0.5) if hot else tick(1300), 0.07 if hot else 0.05, pan=-0.6 + 1.2 * u, rev=0.3)
add(sfx, S["chart"] - 0.05, whoosh(0.5, "bell", 160, 900), 0.3)
# the seal, the phone, the end
add(sfx, S["seal"] - 0.05, whoosh(0.6, "bell", 140, 700), 0.3, rev=0.3)
add(sfx, S["phone"], whoosh(0.95, "decay", 160, 1200), 0.5, rev=0.2)
add(sfx, 22.0, whoosh(0.7, "bell", 150, 1000), 0.35, rev=0.2)
add(sfx, S["end"] + 0.45, thump(1.0), 0.7, rev=0.35)
add(sfx, S["end"] + 0.5, bell(1318.5, 2.0), 0.08, rev=0.6)
add(sfx, S["end"] + 1.15, pop(784), 0.3, rev=0.25)

# ---------- mix ----------
# sidechain: duck bass and keys under each kick, so the groove breathes
sc = np.ones(N)
for k in kicks:
    a = int(k * SR)
    seg = np.arange(min(N - a, int(0.3 * SR))) / SR
    sc[a:a + len(seg)] = np.minimum(sc[a:a + len(seg)], 1 - 0.42 * np.exp(-seg * 11))
music = drums + (bass_bus + keys) * sc[:, None]


def reverb(x, rt=1.7, pre=0.018):
    """Stereo FFT convolution with a decorrelated, darkening noise tail."""
    n = int(rt * SR)
    t = np.arange(n) / SR
    out = np.zeros_like(x)
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    for c in range(2):
        ir = rng.standard_normal(n) * np.exp(-t * 6.9 / rt)
        ir = np.convolve(ir, np.ones(6) / 6, mode="same")  # soften the top end
        ir = np.concatenate([np.zeros(int(pre * SR)), ir])[:n]
        ir /= np.sqrt(np.sum(ir ** 2))
        out[:, c] = np.fft.irfft(np.fft.rfft(x[:, c], size) * np.fft.rfft(ir, size), size)[: len(x)]
    return out


mix = music * 0.55 + sfx * 0.75 + reverb(send) * 0.35
mix = np.tanh(mix * 1.15) / np.tanh(1.15)
env = np.ones(N)
env[: int(0.01 * SR)] = np.linspace(0, 1, int(0.01 * SR))
env[-int(1.0 * SR):] = np.linspace(1, 0, int(1.0 * SR)) ** 1.5
mix *= env[:, None]
mix /= np.max(np.abs(mix)) / 0.9


def write(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


# two-pass loudnorm to Instagram's -14 LUFS without pumping
out = sys.argv[1]
raw = tempfile.mktemp(suffix=".wav")
write(raw, mix)
target = "I=-14:TP=-1.5:LRA=11"
probe = subprocess.run(["ffmpeg", "-hide_banner", "-i", raw, "-af", f"loudnorm={target}:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
m = json.loads(probe[probe.rindex("{"):probe.rindex("}") + 1])
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af",
                f"loudnorm={target}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
                f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true", "-ar", str(SR), out], check=True)
os.remove(raw)
print("wrote", out, "| input", m["input_i"], "LUFS")
