"""Final checks on a rendered story video.

  python3 story/check.py VIDEO.mp4 [REPORT.png]

Prints pass/fail for: format (1080x1920, 30 fps, length, audio), loudness and peak, picture jumps
(frame-to-frame change that spikes far above its neighbours), camera smoothness (sudden changes of
speed along the phone's path) and sync (the big audio hits land on their picture events).
REPORT.png, if given, plots the frame-change curve with the cuts marked.
"""
import json
import subprocess
import sys

import numpy as np

sys.path.insert(0, __import__("os").path.dirname(__file__))
import render  # noqa: E402

VIDEO = sys.argv[1]
results = []


def check(name, ok, detail):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")


# ---------- format ----------
info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", VIDEO],
                                 capture_output=True, text=True).stdout)
v = next(s for s in info["streams"] if s["codec_type"] == "video")
a = [s for s in info["streams"] if s["codec_type"] == "audio"]
dur = float(info["format"]["duration"])
check("format", (v["width"], v["height"]) == (1080, 1920) and v["r_frame_rate"] == "30/1" and a,
      f"{v['width']}x{v['height']} {v['r_frame_rate']} fps, {dur:.2f} s, audio: {'yes' if a else 'no'}")

# ---------- loudness ----------
out = subprocess.run(["ffmpeg", "-hide_banner", "-i", VIDEO, "-af", "ebur128=peak=true", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
lufs = float(out.split("I:")[-1].split("LUFS")[0])
peak = float(out.split("Peak:")[-1].split("dBFS")[0])
check("loudness", -15.5 <= lufs <= -12.5 and peak <= -1.0, f"{lufs:.1f} LUFS integrated, true peak {peak:.1f} dBFS")

# ---------- picture: frame-to-frame change ----------
W, H = 270, 480
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", VIDEO, "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                     capture_output=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)
diff = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
local = np.array([np.median(diff[max(0, i - 4):i + 5]) for i in range(len(diff))])
spikes = [(i + 1) / 30 for i in range(len(diff)) if diff[i] > 4 * max(local[i], 1.0) and diff[i] > 6]
check("no picture jumps", not spikes, f"{len(spikes)} spike(s) {['%.2fs' % s for s in spikes]}; "
      f"median change {np.median(diff):.2f}, max {diff.max():.2f}")

# ---------- camera path: speed must not jump between frames ----------
from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as p:
    browser, page, _ = render.open_page(p)
    paths = page.evaluate("""() => {
      const o = []; for (let i = Math.round(PHONE[0][0] * 30); i <= Math.round(PHONE[PHONE.length - 1][0] * 30); i++) o.push(track(PHONE, i / 30));
      return [o]; }""")
    browser.close()
bad = []
for k, poses in enumerate(paths):  # the two camera paths are separate shots, so check each on its own
    P = np.array([[q["s"] * 600, q["x"], q["y"], q["rx"] * 10, q["ry"] * 10, q["rz"] * 10] for q in poses])
    vel = np.diff(P, axis=0)                         # px (or deg*10) per frame
    jerk = np.abs(np.diff(vel, axis=0)).max(axis=1)  # change of speed between frames
    spd = np.abs(vel).max(axis=1)[1:]
    skip = 0
    bad += [i for i in range(skip, len(jerk)) if jerk[i] > 0.35 * max(spd[i], 20)]
check("camera speed changes smoothly", not bad, f"{len(bad)} frame(s) with a sudden speed change")

# ---------- sync: loud hits where the picture hits ----------
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", VIDEO, "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True).stdout
x = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
env = np.sqrt(np.convolve(x ** 2, np.ones(240) / 240, mode="same"))
hits = {"first frame": 0.0, "ring complete": 4.45, "wordmark": 22.8}
offs = {}
for name, t in hits.items():
    a0 = max(0, int((t - 0.15) * 8000))
    w = env[a0:int((t + 0.15) * 8000)]
    offs[name] = (np.argmax(np.diff(w)) + a0) / 8000 - t
check("sync", all(abs(o) < 0.06 for o in offs.values()), ", ".join(f"{k} {o * 1000:+.0f} ms" for k, o in offs.items()))

if len(sys.argv) > 2:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1600, 360), "white")
    d = ImageDraw.Draw(img)
    scale = 300 / max(diff.max(), 1)
    for i, val in enumerate(diff):
        X = int(i / len(diff) * 1600)
        d.line([(X, 340), (X, 340 - val * scale)], fill=(40, 40, 40))
    for s in spikes:
        X = int(s * 30 / len(diff) * 1600)
        d.line([(X, 0), (X, 340)], fill=(220, 0, 0), width=2)
    for sec in range(int(dur) + 1):
        X = int(sec * 30 / len(diff) * 1600)
        d.text((X + 2, 344), f"{sec}s", fill=(0, 0, 0))
    img.save(sys.argv[2])

print("ALL PASS" if all(results) else "SOME CHECKS FAILED")
