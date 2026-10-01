import time
import os
from playwright.sync_api import sync_playwright

def capture():
    out_dir = r"C:\Users\SANJAY V\.gemini\antigravity\brain\372f31a5-7e29-4c89-a791-126146165247"
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto("http://localhost:3000", wait_until="networkidle")
        time.sleep(2)

        # 1. Dismiss Hero / Start Guided Demo
        hero_btn = page.locator("button:has-text('Run Guided Demo')").first
        if hero_btn.is_visible():
            print("Clicking Run Guided Demo...")
            hero_btn.click()
            time.sleep(3)

        # Expand "Why this choice?"
        why_btn = page.locator("button:has-text('Why this choice?')").first
        if why_btn.is_visible():
            print("Expanding 'Why this choice?'...")
            why_btn.click()
            time.sleep(1)

        p1 = os.path.join(out_dir, "step4_panels_t0.png")
        page.screenshot(path=p1)
        print("Saved Step 4 T0:", p1, "exists:", os.path.exists(p1), "size:", os.path.getsize(p1))

        # 2. Approve and Step T+10
        approve_btn = page.locator("button:has-text('Approve & Dispatch Plan')").first
        if not approve_btn.is_visible():
            approve_btn = page.locator("button:has-text('Authorize Dispatch')").first
        if approve_btn.is_visible():
            print("Clicking Approve & Dispatch...")
            approve_btn.click()
            time.sleep(2)

        step_btn = page.locator("button:has-text('Step T+10')").first
        if step_btn.is_visible():
            print("Stepping to T+10...")
            step_btn.click()
            time.sleep(3)

        p2 = os.path.join(out_dir, "step4_panels_t10_reroute.png")
        page.screenshot(path=p2)
        print("Saved Step 4 T+10:", p2, "exists:", os.path.exists(p2), "size:", os.path.getsize(p2))

        browser.close()

if __name__ == "__main__":
    capture()
