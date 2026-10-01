import time
import os
from playwright.sync_api import sync_playwright

def capture():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto("http://localhost:3000", wait_until="networkidle")
        time.sleep(2)

        # 1. Start T0
        hero_btn = page.locator("button:has-text('Run Guided Demo')").first
        if hero_btn.is_visible():
            hero_btn.click()
            time.sleep(3)

        out_dir = r"C:\Users\SANJAY V\.gemini\antigravity\brain\372f31a5-7e29-4c89-a791-126146165247"
        p1 = os.path.join(out_dir, "step3_osm_map_t0.png")
        page.screenshot(path=p1)
        print("Saved:", p1, "exists:", os.path.exists(p1), "size:", os.path.getsize(p1))

        # 2. Authorize and Step T+10
        auth_btn = page.locator("button:has-text('Authorize Dispatch')").first
        if auth_btn.is_visible():
            auth_btn.click()
            time.sleep(2)

        step_btn = page.locator("button:has-text('Step T+10')").first
        if step_btn.is_visible():
            step_btn.click()
            time.sleep(3)

        p2 = os.path.join(out_dir, "step3_osm_map_t10_blocked.png")
        page.screenshot(path=p2)
        print("Saved:", p2, "exists:", os.path.exists(p2), "size:", os.path.getsize(p2))

        browser.close()

if __name__ == "__main__":
    capture()
