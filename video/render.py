"""Render video/index.html to a vertical video.

  python3 video/render.py sheet OUT.png 0.5 1.2 3.4 ...   contact sheet of stills, labelled with t
  python3 video/render.py video OUT.mp4 [--audio WAV]      full film at 30 fps, fast moves motion-blurred
  python3 video/render.py events OUT.json                  times of the held-request bursts, for audio.py

Drives the page's render(t) frame by frame in headless Chromium, so every take is identical.
"""
import functools
import http.server
import os
import subprocess
import sys
import threading

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
W, H = 1080, 1920


def serve():
    """The page loads three.js as ES modules, which Chromium refuses over file://."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=HERE)
    handler.log_message = lambda *a: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}/index.html"


def open_page(p):
    browser = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": W, "height": H})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(serve(), wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    page.wait_for_function("window.GL_READY === true", timeout=60000)
    page.wait_for_timeout(400)
    return browser, page, errors


def sheet(out, times):
    from PIL import Image, ImageDraw
    thumbs = []
    with sync_playwright() as p:
        browser, page, errors = open_page(p)
        for t in times:
            page.evaluate(f"render({t})")
            path = f"{out}.{t}.png"
            page.screenshot(path=path)
            im = Image.open(path).convert("RGB").resize((270, 480))
            ImageDraw.Draw(im).text((6, 4), f"{t:.2f}s", fill=(255, 0, 0))
            thumbs.append(im)
            os.remove(path)
        browser.close()
    cols = min(6, len(thumbs))
    rows = (len(thumbs) + cols - 1) // cols
    grid = Image.new("RGB", (cols * 276, rows * 486), "white")
    for i, im in enumerate(thumbs):
        grid.paste(im, ((i % cols) * 276, (i // cols) * 486))
    grid.save(out)
    print("errors:", errors or "none")


def video(out, audio=None, fps=30, sub=6, shutter=0.5):
    """Inside the page's MOTION_BLUR spans each frame is the average of `sub` renders spread over
    `shutter` of a frame (180 degrees), which is how a film camera blurs fast moves."""
    import io

    import numpy as np
    from PIL import Image

    with sync_playwright() as p:
        browser, page, errors = open_page(p)
        duration = page.evaluate("window.DURATION")
        spans = page.evaluate("window.MOTION_BLUR || []")
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
               "-framerate", str(fps), "-i", "-"]
        if audio:
            cmd += ["-i", audio]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
        if audio:
            cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
        cmd += [out]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)

        def grab(t):
            page.evaluate(f"render({max(0.0, t):.5f})")
            jpg = page.screenshot(type="jpeg", quality=95)
            return np.asarray(Image.open(io.BytesIO(jpg)).convert("RGB"), dtype=np.float32)

        n = int(round(duration * fps))
        for i in range(n):
            t = i / fps
            if any(a <= t <= b for a, b in spans):
                acc = sum(grab(t + (k / (sub - 1) - 0.5) * shutter / fps) for k in range(sub))
                frame = acc / sub
            else:
                frame = grab(t)
            ff.stdin.write(np.clip(frame + 0.5, 0, 255).astype(np.uint8).tobytes())
            if i % 60 == 0:
                print(f"frame {i}/{n}", flush=True)
        browser.close()
    ff.stdin.close()
    ff.wait()
    print("errors:", errors or "none")


def events(out):
    """Times of the held requests that burst at the ring, for the soundtrack."""
    import json
    with sync_playwright() as p:
        browser, page, _ = open_page(p)
        times = page.evaluate("window.collectEvents()")
        browser.close()
    with open(out, "w") as f:
        json.dump(times, f)
    print(len(times), "events")


if __name__ == "__main__":
    mode, out = sys.argv[1], sys.argv[2]
    if mode == "events":
        events(out)
    elif mode == "sheet":
        sheet(out, [float(x) for x in sys.argv[3:]])
    else:
        audio = sys.argv[sys.argv.index("--audio") + 1] if "--audio" in sys.argv else None
        video(out, audio)
