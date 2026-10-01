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

        # 2. Open Technical Drawer Tab 1 (Trace)
        tab1_btn = page.locator("button:has-text('How AI Team Decided')").first
        if tab1_btn.is_visible():
            print("Opening Tab 1: How AI Team Decided...")
            tab1_btn.click()
            time.sleep(1)

        p1 = os.path.join(out_dir, "step5_drawer_tab1_trace.png")
        page.screenshot(path=p1)
        print("Saved Step 5 Tab 1:", p1, "exists:", os.path.exists(p1))

        # 3. Switch to Tab 2 (Security) and simulate Prompt Injection Attack
        tab2_btn = page.locator("button:has-text('Security: Try to Break It')").first
        if tab2_btn.is_visible():
            print("Opening Tab 2: Security...")
            tab2_btn.click()
            time.sleep(1)

            # Click simulate on prompt injection
            sim_btn = page.locator("button:has-text('Simulate')").first
            if sim_btn.is_visible():
                print("Simulating attack...")
                sim_btn.click()
                time.sleep(2)

        p2 = os.path.join(out_dir, "step5_drawer_tab2_security.png")
        page.screenshot(path=p2)
        print("Saved Step 5 Tab 2:", p2, "exists:", os.path.exists(p2))

        # 4. Switch to Tab 3 (Proofs)
        tab3_btn = page.locator("button:has-text('Why It\\'s Smarter')").first
        if not tab3_btn.is_visible():
            tab3_btn = page.locator("button:has-text('Why It')").first
        if tab3_btn.is_visible():
            print("Opening Tab 3: Proofs...")
            tab3_btn.click()
            time.sleep(2)

        p3 = os.path.join(out_dir, "step5_drawer_tab3_proofs.png")
        page.screenshot(path=p3)
        print("Saved Step 5 Tab 3:", p3, "exists:", os.path.exists(p3))

        browser.close()

if __name__ == "__main__":
    capture()
