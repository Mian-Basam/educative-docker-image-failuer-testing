"""
check_build_bulk.py

READ-ONLY script: loads each Educative editor page in a headless
browser using a saved login session, waits for the JavaScript-
rendered content to load, then checks whether the Docker image
has been built. Never clicks anything or submits any forms.

Requires auth_state.json (created by running save_session.py once).

Usage:
    python3 check_build_bulk.py
"""

import os
import sys
import time
import pandas as pd
from playwright.sync_api import sync_playwright

INPUT_FILE = "urls_template.xlsx"
OUTPUT_FILE = "build_status_results.xlsx"
SHEET_NAME = 0
REQUEST_DELAY_SECONDS = 2
PAGE_LOAD_TIMEOUT_MS = 20000
STATE_FILE = "auth_state.json"


def load_rows(path: str, sheet=0) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet)
    df.columns = [str(c).strip().lower() for c in df.columns]

    if "author_id" in df.columns and "collection_id" in df.columns:
        df["author_id"] = df["author_id"].astype(str).str.strip()
        df["collection_id"] = df["collection_id"].astype(str).str.strip()
        df["url"] = df.apply(
            lambda r: f"https://www.educative.io/editor/collectioneditor/{r['author_id']}/{r['collection_id']}",
            axis=1
        )
        return df[["url"]]

    if "url" in df.columns:
        df["url"] = df["url"].astype(str).str.strip()
        return df[["url"]]

    raise ValueError(f"Could not find required columns. Found: {list(df.columns)}")


def check_docker_build_status(page, url: str, debug: bool = False) -> dict:
    """
    Loads the page using the authenticated browser context, waits
    for JS-rendered content, and reads the build status text.
    Read-only: no clicks, no form submissions.
    """
    try:
        page.goto(url, timeout=PAGE_LOAD_TIMEOUT_MS, wait_until="networkidle")
    except Exception as e:
        return {"built": None, "status_text": None, "error": f"page load error: {e}"}

    if debug:
        try:
            page.screenshot(path="debug_screenshot.png", full_page=True)
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("    [DEBUG] Saved debug_screenshot.png and debug_page.html")

            if page.locator("text=Log In").count() > 0:
                print("    [DEBUG] WARNING: 'Log In' button detected — likely NOT authenticated.")
            else:
                print("    [DEBUG] No 'Log In' button detected — likely authenticated OK.")
        except Exception as e:
            print(f"    [DEBUG] Could not save debug files: {e}")

    try:
        success_locator = page.locator("text=Image has been built")
        if success_locator.count() > 0:
            return {"built": True, "status_text": success_locator.first.inner_text(), "error": None}

        error_locator = page.locator(".text-red-500")
        if error_locator.count() > 0:
            return {"built": False, "status_text": error_locator.first.inner_text(), "error": None}

        return {"built": None, "status_text": None, "error": None}
    except Exception as e:
        return {"built": None, "status_text": None, "error": f"parse error: {e}"}


def main():
    if not os.path.exists(STATE_FILE):
        print(f"ERROR: {STATE_FILE} not found.")
        print("Run 'python3 save_session.py' first to log in and save your session.")
        sys.exit(1)

    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)

    rows = load_rows(INPUT_FILE, sheet=SHEET_NAME)
    print(f"Loaded {len(rows)} URLs from {INPUT_FILE}")

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=STATE_FILE)
        page = context.new_page()

        for i, row in rows.iterrows():
            url = row["url"]

            if not url or url.lower() == "nan":
                print(f"[{i+1}/{len(rows)}] Skipping empty row")
                results.append({"url": url, "built": None, "status_text": None, "error": "empty url"})
                continue

            print(f"[{i+1}/{len(rows)}] Checking {url} ...")
            result = check_docker_build_status(page, url, debug=(i == 0))

            results.append({
                "url": url,
                "built": result["built"],
                "status_text": result["status_text"],
                "error": result["error"],
            })

            print(f"    -> built={result['built']} text={result['status_text']!r}")
            time.sleep(REQUEST_DELAY_SECONDS)

        browser.close()

    out_df = pd.DataFrame(results)
    out_df.to_excel(OUTPUT_FILE, index=False)
    print(f"\nDone. Results written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()