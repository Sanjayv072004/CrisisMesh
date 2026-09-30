import time
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = Path("C:/Users/SANJAY V/.gemini/antigravity/brain/372f31a5-7e29-4c89-a791-126146165247")

def capture():
    print("Starting screenshot capture with Playwright (Edge)...")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # 1. Baseline view
        print("Navigating to http://localhost:3000...")
        page.goto("http://localhost:3000", wait_until="networkidle")
        time.sleep(2)
        
        # Click Start T0 to populate map and agents
        page.keyboard.press("Digit1")
        time.sleep(2)
        
        # Capture Full Dashboard (Redesign)
        shot6 = str(ARTIFACT_DIR / "redesign_full_1080p.png")
        page.screenshot(path=shot6)
        print(f"Captured: {shot6}")

        # Capture Tactical Map close-up
        map_el = page.locator("section[aria-label='Bengaluru Tactical Map']")
        if map_el.count() > 0:
            shot1 = str(ARTIFACT_DIR / "tactical_map.png")
            map_el.screenshot(path=shot1)
            print(f"Captured: {shot1}")

        # Capture Safe Mode banner & TopBar
        header_el = page.locator("header")
        if header_el.count() > 0:
            shot2 = str(ARTIFACT_DIR / "safe_mode_banner.png")
            header_el.screenshot(path=shot2)
            print(f"Captured: {shot2}")

        # Capture Agent Flow View
        flow_el = page.locator("text=Multi-Agent State Flow").locator("xpath=../..")
        if flow_el.count() > 0:
            shot5 = str(ARTIFACT_DIR / "agent_flow.png")
            flow_el.screenshot(path=shot5)
            print(f"Captured: {shot5}")

        # Trigger Attack demonstration and capture Security Feed
        page.keyboard.press("KeyA")
        time.sleep(1)
        # Click first attack button (Prompt Injection)
        prompt_btn = page.locator("button:has-text('Test Prompt Injection')")
        if prompt_btn.count() > 0:
            prompt_btn.click()
            time.sleep(1)
        # Close attack panel
        page.keyboard.press("KeyA")
        time.sleep(0.5)

        # Switch Left Tab to Security Feed
        sec_tab = page.locator("button:has-text('Security Feed')")
        if sec_tab.count() > 0:
            sec_tab.click()
            time.sleep(1)
        
        sidebar_el = page.locator("section[aria-label='Operations Sidebar']")
        if sidebar_el.count() > 0:
            shot3 = str(ARTIFACT_DIR / "security_feed.png")
            sidebar_el.screenshot(path=shot3)
            print(f"Captured: {shot3}")

        # Open USP Proof Panel
        page.keyboard.press("KeyU")
        time.sleep(1.5)
        usp_el = page.locator("div[role='dialog'], div.fixed.inset-0")
        if usp_el.count() > 0:
            shot4 = str(ARTIFACT_DIR / "usp_panel.png")
            page.screenshot(path=shot4)
            print(f"Captured: {shot4}")

        browser.close()
        print("Screenshot capture complete!")

if __name__ == "__main__":
    capture()
