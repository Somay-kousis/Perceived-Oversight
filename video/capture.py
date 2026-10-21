"""Capture the explorer's mobile pages for the phone screen in the video.

  cd explorer/web && npm run dev      # in another shell
  python3 video/capture.py

Writes video/shots/*.png at the phone screen's proportions (568 x 1268), 2x.
"""
import os
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5173/"

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 430, "height": 960}, device_scale_factor=2)
    for name, route, full in [("hero", "", False), ("journey", "#/journey", True), ("models", "#/models", False)]:
        page.goto(BASE + route, wait_until="networkidle")
        page.wait_for_timeout(2500)  # let the landing's stream fill the screen
        page.screenshot(path=os.path.join(HERE, "shots", f"{name}.png"), full_page=full)
        print(name, page.evaluate("document.body.scrollHeight"))
    browser.close()
