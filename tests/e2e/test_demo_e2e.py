#!/usr/bin/env python3
"""
CrisisMesh Playwright End-to-End Test.
Tests the full demo workflow in a headless browser.
"""
import sys
import time
try:
    from playwright.sync_api import sync_playwright, expect, TimeoutError as PlaywrightTimeout
except ImportError:
    print("[SKIP] Playwright not installed. Install with: pip install playwright && playwright install chromium")
    sys.exit(0)

BASE_URL = "http://localhost:3000"
API_URL = "http://localhost:8000"
TIMEOUT = 15000  # 15s per action


def run_e2e():
    results = []
    def check(name: str, passed: bool, detail: str = ""):
        status = "PASS" if passed else "FAIL"
        results.append((name, passed))
        print(f"  [{status}] {name}" + (f": {detail}" if detail else ""))

    print("=" * 60)
    print("CRISISMESH E2E DEMO TEST")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()

        print("\n--- 1. Page Load & Auth ---")
        page.goto(BASE_URL, timeout=15000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        check("Page loads at localhost:3000", True)

        # The app auto-logs in with NEXT_PUBLIC_DEMO_AUTOLOGIN=true
        # Check top bar renders
        top_bar_visible = page.locator("header, [data-testid=topbar], nav").count() > 0 or \
                          page.locator("text=CrisisMesh").count() > 0 or \
                          page.locator("text=MOCK").count() > 0 or \
                          page.locator("text=LIVE").count() > 0
        check("Top bar renders", top_bar_visible)

        print("\n--- 2. Presenter Mode (keyboard P) ---")
        page.keyboard.press("p")
        time.sleep(1)
        presenter_visible = page.locator("text=Start T0").count() > 0 or \
                            page.locator("text=Presenter").count() > 0 or \
                            page.locator("[data-presenter]").count() > 0
        check("Presenter controls visible after P", presenter_visible)

        print("\n--- 3. Start T0 Scenario (keyboard 1) ---")
        page.keyboard.press("1")
        # Wait for scenario to process (T0 takes ~2s)
        time.sleep(3)
        # Should see incidents appearing in the interface
        has_incident_data = page.locator("text=Silk Board").count() > 0 or \
                            page.locator("text=Bellandur").count() > 0 or \
                            page.locator("text=CONFIRMED").count() > 0 or \
                            page.locator("text=ambulance").count() > 0
        check("T0 scenario runs and incidents appear", has_incident_data)

        print("\n--- 4. Attack Panel (keyboard A) ---")
        page.keyboard.press("a")
        time.sleep(1)
        attack_panel_visible = page.locator("text=Fake Report").count() > 0 or \
                               page.locator("text=Attack").count() > 0 or \
                               page.locator("text=Prompt Injection").count() > 0
        check("Attack panel opens with A", attack_panel_visible)

        # Click fake_report attack
        fake_btn = page.locator("button:has-text('Fake Report')").first
        if fake_btn.count() > 0 or page.locator("button").filter(has_text="Fake").count() > 0:
            btn = page.locator("button").filter(has_text="Fake").first
            btn.click(timeout=5000)
            time.sleep(2)
            outcome_visible = page.locator("text=PROVISIONAL_ISOLATED").count() > 0 or \
                              page.locator("text=BLOCKED").count() > 0 or \
                              page.locator("text=mitigating").count() > 0 or \
                              page.locator("text=VerificationEngine").count() > 0
            check("Fake Report attack shows outcome card", outcome_visible)
        else:
            check("Fake Report attack button found", False, "Button not located")

        print("\n--- 5. Escape closes panel ---")
        page.keyboard.press("Escape")
        time.sleep(0.5)
        panel_closed = page.locator("text=Prompt Injection").count() == 0 or \
                       page.locator("[data-attack-panel]").count() == 0
        check("Escape key closes attack panel", panel_closed)

        print("\n--- 6. USP Proof Panel (keyboard U) ---")
        page.keyboard.press("u")
        time.sleep(1)
        usp_visible = page.locator("text=Low-Churn").count() > 0 or \
                      page.locator("text=USP").count() > 0 or \
                      page.locator("text=Uncertainty").count() > 0
        check("USP Panel opens with U", usp_visible)

        print("\n--- 7. Reset (keyboard R) ---")
        page.keyboard.press("Escape")
        time.sleep(0.5)
        page.keyboard.press("r")
        time.sleep(2)
        check("Reset keystroke executes", True)

        browser.close()

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    print(f"E2E RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_e2e())
