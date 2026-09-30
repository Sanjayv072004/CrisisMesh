"""Playwright E2E Gate Test: Verifies CSS styles, WebSocket connectivity, Map rendering, and Scenario execution."""
import os
import time
import pytest
import urllib.request

def is_service_ready(url: str) -> bool:
    try:
        res = urllib.request.urlopen(url, timeout=2)
        return res.status == 200
    except Exception:
        return False

@pytest.mark.skipif(
    not is_service_ready("http://localhost:3000") or not is_service_ready("http://127.0.0.1:8000/health"),
    reason="Frontend (port 3000) or Backend (port 8000) not running in current environment",
)
def test_playwright_full_ui_gate():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # 1. Navigate to app
        page.goto("http://localhost:3000", wait_until="networkidle")
        time.sleep(2)

        # 2. Assert CSS styles are loaded (Background must not be default white)
        body_bg = page.evaluate("() => window.getComputedStyle(document.body).backgroundColor")
        assert body_bg in ["rgb(10, 13, 20)", "rgb(7, 10, 18)", "#0a0d14", "#070a12"], f"CSS not loaded, body_bg was {body_bg}"

        # 3. Assert WebSocket is CONNECTED in the header badge
        header_text = page.locator("header").text_content() or ""
        assert "CONNECTED" in header_text, f"WebSocket was not CONNECTED. Header: {header_text}"

        # 4. Assert Map has drawn features (nodes & road edges)
        line_count = page.locator("svg line").count()
        circle_count = page.locator("svg circle").count()
        assert line_count > 0, f"Map has 0 road lines drawn: {line_count}"
        assert circle_count > 0, f"Map has 0 nodes/circles drawn: {circle_count}"

        # 5. Reset and trigger Start T0
        reset_btn = page.get_by_role("button", name="Reset", exact=True)
        if reset_btn.is_visible():
            reset_btn.click()
            time.sleep(2)

        start_btn = page.get_by_role("button", name="Start T0", exact=True)
        assert start_btn.is_visible(), "Start T0 button not found"
        start_btn.click()
        time.sleep(4)

        # 6. Assert Incidents are populated (> 0)
        incident_cards = page.locator("section[aria-label='Operations Sidebar']").locator("div[class*='cursor-pointer']").count()
        assert incident_cards > 0, "Incidents stayed 0 after Start T0"

        # 7. Assert Plan assignments are rendered
        plan_section = page.locator("section[aria-label='Plan and Trace Panels']")
        assert "Total Cost" in (plan_section.text_content() or ""), "Active dispatch plan not computed"

        browser.close()
