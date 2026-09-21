"""
save_session.py

Opens a real, visible browser window so you can log into Educative
manually. Once logged in, come back to this terminal and press Enter
to save your session (cookies, storage) to auth_state.json for reuse.

Run this ONCE (and again later if your session expires):
    python3 save_session.py
"""

from playwright.sync_api import sync_playwright

STATE_FILE = "auth_state.json"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://www.educative.io")

        print("=" * 60)
        print("A browser window has opened.")
        print("Please log into Educative manually in that window.")
        print("Complete any 2FA / verification steps if prompted.")
        print("=" * 60)
        input("Once you're fully logged in and see your dashboard, "
              "press Enter here to save the session...")

        context.storage_state(path=STATE_FILE)
        print(f"\nSession saved to {STATE_FILE}")

        browser.close()


if __name__ == "__main__":
    main()