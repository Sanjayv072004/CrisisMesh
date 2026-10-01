import os
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\SANJAY V\.gemini\antigravity\brain\372f31a5-7e29-4c89-a791-126146165247"
PUBLIC_FRONTEND_URL = "https://affects-wind-anytime-sequence.trycloudflare.com"

def verify_public_url():
    print(f"Connecting to PUBLIC frontend URL: {PUBLIC_FRONTEND_URL}")
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        page.on("console", lambda msg: print(f"  [BROWSER CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"  [BROWSER ERROR] {err}"))

        # 1. Load Public Frontend URL
        print("Navigating to public URL...")
        page.goto(PUBLIC_FRONTEND_URL, wait_until="networkidle", timeout=60000)
        time.sleep(3)

        # 2. Check CSS styling loaded
        body_bg = page.evaluate("() => window.getComputedStyle(document.body).backgroundColor")
        results["styled_page"] = "PASS" if body_bg in ["rgb(11, 12, 31)", "rgb(10, 13, 20)", "rgb(7, 10, 18)", "#0b0c1f", "#0a0d14", "#070a12"] else "FAIL"
        print(f"Styled page check: {results['styled_page']} (body_bg: {body_bg})")

        # 3. Dismiss Hero Modal by clicking "Run Guided Demo"
        hero_btn = page.get_by_role("button", name="Run Guided Demo")
        if hero_btn.is_visible():
            print("Clicking Run Guided Demo on public page...")
            hero_btn.click()
            time.sleep(3)

        # 4. Ingest T0 scenario by clicking "Start Scenario" or "Next step"
        start_btn = page.locator("button:has-text('Start Scenario')")
        if not start_btn.is_visible():
            start_btn = page.locator("button:has-text('Next step')")
        if start_btn.is_visible():
            print("Clicking Start Scenario / Next step...")
            start_btn.click()
            time.sleep(4)

        # 5. Check WebSocket is CONNECTED
        header_text = page.locator("header").text_content() or ""
        results["websocket_connected"] = "PASS" if "CONNECTED" in header_text else "FAIL"
        print(f"WebSocket CONNECTED check: {results['websocket_connected']}")

        # 6. Check Map has drawn features
        line_count = page.locator("svg line").count()
        circle_count = page.locator("svg circle").count()
        results["map_rendering"] = "PASS" if (line_count > 0 and circle_count > 0) else "FAIL"
        print(f"Map rendering check: {results['map_rendering']} ({line_count} lines, {circle_count} circles)")

        # 7. Check T0 Incidents appear
        sidebar_text = page.locator("section[aria-label='Operations Sidebar']").text_content() or ""
        has_incidents = "Silk Board" in sidebar_text and ("Confirmed" in sidebar_text or "CONFIRMED" in sidebar_text)
        results["t0_incidents_intake"] = "PASS" if has_incidents else "FAIL"
        print(f"T0 Incidents intake check: {results['t0_incidents_intake']}")

        # 8. Check Plan recommendations appear
        plan_section = page.locator("section[aria-label='Plan and Trace Panels']")
        plan_text = plan_section.text_content() or ""
        has_plan = "Ambulance 1" in plan_text or "What We Recommend" in plan_text or "Total Harm Cost" in plan_text
        results["plan_recommendations"] = "PASS" if has_plan else "FAIL"
        print(f"Plan recommendations check: {results['plan_recommendations']}")

        # 9. Save Screenshot of Public Page at T0
        screenshot_path = os.path.join(ARTIFACT_DIR, "public_share_t0.png")
        page.screenshot(path=screenshot_path)
        print(f"Saved public screenshot: {screenshot_path}")

        # 10. Test Plan Approval
        approve_btn = page.locator("button:has-text('Approve & Dispatch Plan')")
        if approve_btn.is_visible():
            print("Clicking Approve & Dispatch Plan on public page...")
            approve_btn.click()
            time.sleep(3)

        updated_plan_text = page.locator("section[aria-label='Plan and Trace Panels']").text_content() or ""
        results["plan_approval"] = "PASS" if ("Dispatched" in updated_plan_text or "Audit Valid" in updated_plan_text or "DISPATCHED" in (page.locator("header").text_content() or "")) else "FAIL"
        print(f"Plan approval check: {results['plan_approval']}")

        browser.close()

    print("\n--- Final Verification Results ---")
    for k, v in results.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    verify_public_url()
