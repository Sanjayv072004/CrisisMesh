import os
import time
import json
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\SANJAY V\.gemini\antigravity\brain\372f31a5-7e29-4c89-a791-126146165247"

def run_render_test():
    console_messages = []
    page_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        print("[*] Navigating to http://localhost:3000 ...")
        page.goto("http://localhost:3000", wait_until="networkidle")
        time.sleep(3)

        # 1. Reset state
        reset_btn = page.get_by_role("button", name="Reset", exact=True)
        if reset_btn.is_visible():
            reset_btn.click()
            time.sleep(2)

        # Verify CSS is loaded
        body_bg = page.evaluate("() => window.getComputedStyle(document.body).backgroundColor")
        print(f"[*] Computed Body Background: {body_bg}")

        # Check WebSocket badge
        ws_text = page.locator("header").text_content()
        print(f"[*] Header text snapshot: {ws_text}")

        # Check Map SVG elements
        line_count = page.locator("svg line").count()
        circle_count = page.locator("svg circle").count()
        print(f"[*] Map features rendered: {line_count} road lines, {circle_count} nodes/markers")

        # Save (a) Initial state screenshot
        p1 = os.path.join(ARTIFACT_DIR, "step0_initial_clean_graph.png")
        page.screenshot(path=p1)
        print(f"[OK] Saved Initial screenshot: {p1}")

        # 2. Trigger Start T0
        start_btn = page.get_by_role("button", name="Start T0", exact=True)
        if start_btn.is_visible():
            start_btn.click()
            print("[*] Clicked Start T0, waiting for solver and WebSocket sync...")
            time.sleep(5)

        # Check incidents count and plan
        inc_count = page.locator("text=Incidents (").text_content()
        print(f"[*] Incident Header: {inc_count}")

        # Save (b) Mid-Demo T0 screenshot
        p2 = os.path.join(ARTIFACT_DIR, "step0_mid_demo_t0.png")
        page.screenshot(path=p2)
        print(f"[OK] Saved Mid-Demo T0 screenshot: {p2}")

        # 3. Trigger Step T+10
        step_btn = page.get_by_role("button", name="Step T+10", exact=True)
        if step_btn.is_visible():
            step_btn.click()
            print("[*] Clicked Step T+10, waiting for blockage and re-plan...")
            time.sleep(5)

        # Save (c) After Step T+10 screenshot
        p3 = os.path.join(ARTIFACT_DIR, "step0_after_step_t10.png")
        page.screenshot(path=p3)
        print(f"[OK] Saved Step T+10 screenshot: {p3}")

        browser.close()

    print("\n--- BROWSER CONSOLE LOGS ---")
    for msg in console_messages[-20:]:
        print(msg)

    print("\n--- BROWSER PAGE ERRORS ---")
    if not page_errors:
        print("None (0 errors)")
    else:
        for err in page_errors:
            print("ERROR:", err)

if __name__ == "__main__":
    run_render_test()
