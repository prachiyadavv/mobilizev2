"""Regenerate the README screenshots.

Usage (with the app running on port 5000 against seeded demo data):
    flask --app mobilize seed
    flask --app mobilize run &
    python scripts/screenshots.py
Requires: pip install playwright && playwright install chromium
"""

import sys

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
OUT = "docs/screenshots"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1100, "height": 760}, device_scale_factor=2)

        page.goto(f"{BASE}/")
        page.screenshot(path=f"{OUT}/landing.png", full_page=True)

        page.goto(f"{BASE}/login")
        page.fill("#email", "demo@example.edu")
        page.fill("#password", "Demo#2021")
        page.click("button[type=submit]")
        page.wait_for_url("**/feed")
        page.screenshot(path=f"{OUT}/feed.png", full_page=True)

        page.goto(f"{BASE}/posts/1")
        page.screenshot(path=f"{OUT}/question.png", full_page=True)

        page.goto(f"{BASE}/posts/new")
        page.screenshot(path=f"{OUT}/ask.png", full_page=True)

        page.goto(f"{BASE}/users/1")
        page.screenshot(path=f"{OUT}/profile.png", full_page=True)

        browser.close()


if __name__ == "__main__":
    main()
