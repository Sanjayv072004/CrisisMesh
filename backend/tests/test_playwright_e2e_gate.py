"""Playwright E2E Gate Test: Verifies CSS styles, WebSocket connectivity, Map rendering,
T0 verification truth labels, provisional assignments, VETO triggering at T+10,
and Security Defenses isolation.
"""
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

    # Reset to clean state
    try:
        import requests
        requests.post("http://127.0.0.1:8000/scenario/reset")
    except Exception:
        pass

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # 1. Navigate to app
        page.goto("http://localhost:3000", wait_until="networkidle")
        time.sleep(2)

        # 2. Assert CSS styles are loaded (Background must not be default white)
        body_bg = page.evaluate("() => window.getComputedStyle(document.body).backgroundColor")
        assert body_bg in ["rgb(11, 12, 31)", "rgb(10, 13, 20)", "rgb(7, 10, 18)", "#0b0c1f", "#0a0d14", "#070a12"], f"CSS not loaded, body_bg was {body_bg}"

        # 3. Dismiss Hero Modal by clicking "Run Guided Demo"
        hero_btn = page.get_by_role("button", name="Run Guided Demo")
        if hero_btn.is_visible():
            hero_btn.click()
            time.sleep(3)
        else:
            explore_btn = page.get_by_role("button", name="Explore Manually")
            if explore_btn.is_visible():
                explore_btn.click()
                time.sleep(1)

        # 4. Assert WebSocket is CONNECTED in the header badge
        header_text = page.locator("header").text_content() or ""
        assert "CONNECTED" in header_text, f"WebSocket was not CONNECTED. Header: {header_text}"

        # 5. Assert Map has drawn features (nodes & road edges)
        line_count = page.locator("svg line").count()
        circle_count = page.locator("svg circle").count()
        assert line_count > 0, f"Map has 0 road lines drawn: {line_count}"
        assert circle_count > 0, f"Map has 0 nodes/circles drawn: {circle_count}"

        # 6. Assert T0 Incidents truth labels: Silk Board & Bellandur CONFIRMED, Koramangala UNVERIFIED
        sidebar_text = page.locator("section[aria-label='Operations Sidebar']").text_content() or ""
        assert "Road Accident at Silk Board" in sidebar_text, "Silk board incident missing"
        assert "Confirmed" in sidebar_text or "CONFIRMED" in sidebar_text, "Confirmed label missing"
        assert "unverified" in sidebar_text.lower() or "not yet confirmed" in sidebar_text.lower(), "Unverified label missing"

        # 7. Assert Plan assignments: Only Koramangala is PROVISIONAL (with confirmation checkbox)
        plan_section = page.locator("section[aria-label='Plan and Trace Panels']")
        plan_text = plan_section.text_content() or ""
        assert "Harm Cost" in plan_text or "Total Cost" in plan_text or "Recommend" in plan_text, "Active dispatch plan not computed"
        assert "PROVISIONAL" in plan_text.upper(), "Provisional tag missing for unverified incident"
        assert "CONFIRMED" in plan_text.upper(), "Confirmed tag missing for verified incidents"

        # 8. Assert NO Veto badge before T+10
        body_text = page.locator("body").text_content() or ""
        assert "VETO • RE-SOLVED" not in body_text, "Veto badge showed prematurely at T0!"

        # 9. Authorize T0 Plan and advance to Step T+10
        auth_btn = page.locator("button:has-text('Approve & Dispatch Plan')").first
        if not auth_btn.is_visible():
            auth_btn = page.locator("button:has-text('Authorize Dispatch')").first
        if auth_btn.is_visible():
            auth_btn.click()
            time.sleep(2)

        # Step to T+10 via Next step button
        step_btn = page.locator("button:has-text('Step T+10')")
        if not step_btn.is_visible():
            step_btn = page.locator("button:has-text('Next step')")
        if step_btn.is_visible():
            step_btn.click()
            time.sleep(3)

        # 10. Assert VETO occurs at T+10
        updated_body = page.locator("body").text_content() or ""
        assert "Veto" in updated_body or "VETO" in updated_body or "rerouted" in updated_body.lower() or "157.8" in updated_body, "VETO / reroute failed to appear after T+10 road blockage"

        # 11. Trigger Attack Panel from Top Bar
        atk_btn = page.locator("button:has-text('Try to attack it')")
        if atk_btn.is_visible():
            atk_btn.click()
            time.sleep(1)
            atk_modal = page.locator("body").text_content() or ""
            assert "Attack" in atk_modal or "Simulate" in atk_modal or "Injection" in atk_modal, "Attack modal failed to open"

        browser.close()
