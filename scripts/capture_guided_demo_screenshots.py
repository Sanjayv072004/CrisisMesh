import os
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\SANJAY V\.gemini\antigravity\brain\372f31a5-7e29-4c89-a791-126146165247"

def capture_guided_demo():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        print("[*] Navigating to http://localhost:3000 ...")
        page.goto("http://localhost:3000", wait_until="networkidle")
        time.sleep(2)

        # 1. Capture Hero Screen
        p1 = os.path.join(ARTIFACT_DIR, "hero_screen_initial.png")
        page.screenshot(path=p1)
        print(f"[OK] Saved Hero Screen screenshot: {p1}")

        # 2. Click "Run Guided Demo"
        hero_btn = page.get_by_role("button", name="Run Guided Demo")
        if hero_btn.is_visible():
            hero_btn.click()
            time.sleep(4)

        # Capture T0 Ingested & Plan with Guided Narrator
        p2 = os.path.join(ARTIFACT_DIR, "guided_demo_t0_ingested.png")
        page.screenshot(path=p2)
        print(f"[OK] Saved Guided Demo T0 screenshot: {p2}")

        # 3. Trigger Step T+10 via TopBar or Narrator
        step_btn = page.get_by_role("button", name="Step T+10", exact=True)
        if step_btn.is_visible():
            step_btn.click()
            time.sleep(4)

        # Capture T+10 Road Blockage & VETO
        p3 = os.path.join(ARTIFACT_DIR, "guided_demo_t10_veto.png")
        page.screenshot(path=p3)
        print(f"[OK] Saved Guided Demo T+10 VETO screenshot: {p3}")

        # 4. Switch to Security Feed Tab
        sec_tab = page.get_by_role("button", name="Security Feed")
        if sec_tab.is_visible():
            sec_tab.click()
            time.sleep(2)

        p4 = os.path.join(ARTIFACT_DIR, "guided_demo_security_attacks.png")
        page.screenshot(path=p4)
        print(f"[OK] Saved Security Attack Feed screenshot: {p4}")

        browser.close()

if __name__ == "__main__":
    capture_guided_demo()
