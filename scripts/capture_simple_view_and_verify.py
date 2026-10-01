import os
import time
import requests
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\SANJAY V\.gemini\antigravity\brain\372f31a5-7e29-4c89-a791-126146165247"

def run():
    print("Resetting scenario via API...")
    try:
        requests.post("http://127.0.0.1:8000/api/scenario/reset")
    except Exception as e:
        print("Reset error:", e)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        print("Navigating to http://localhost:3000 ...")
        page.goto("http://localhost:3000", wait_until="networkidle", timeout=30000)
        time.sleep(2)

        # Check if Hero modal is open, click "Run Guided Demo"
        hero_btn = page.locator("button:has-text('Run Guided Demo')")
        if hero_btn.is_visible():
            print("Clicking Run Guided Demo...")
            hero_btn.click()
            time.sleep(3)

        # Wait for emergencies and plan to be rendered
        page.wait_for_selector("text=Silk Board", timeout=15000)
        time.sleep(2)

        # Take T0 Screenshot
        t0_path = os.path.join(ARTIFACT_DIR, "simple_view_t0.png")
        page.screenshot(path=t0_path)
        print(f"Captured T0 screenshot: {t0_path}")

        # Now approve plan
        approve_btn = page.locator("button:has-text('Approve & Dispatch Plan')")
        if approve_btn.is_visible():
            print("Approving plan...")
            approve_btn.click()
            time.sleep(2)

        # Click Step T+10 button in the narrator bar
        step_narrator_btn = page.locator("button:has-text('Step T+10')")
        if step_narrator_btn.is_visible():
            print("Clicking Step T+10 in narrator bar...")
            step_narrator_btn.click()
            time.sleep(3)

        # Wait for T+10 incident or blocked road
        time.sleep(2)

        # Take T+10 Screenshot
        t10_path = os.path.join(ARTIFACT_DIR, "simple_view_t10.png")
        page.screenshot(path=t10_path)
        print(f"Captured T+10 screenshot: {t10_path}")

        browser.close()

if __name__ == "__main__":
    run()
