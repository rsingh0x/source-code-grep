import os
import sys
import urllib.parse
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = "site_sources"
WAIT_MS = 8000  # how long to wait after initial load for lazy assets

TEXT_MIME_HINTS = [
    "javascript", "ecmascript", "css", "html", "json", "xml", "text", "svg"
]

def save_asset(url, body):
    parsed = urllib.parse.urlparse(url)
    host_dir = Path(OUTPUT_DIR) / parsed.netloc
    file_path = host_dir / parsed.path.lstrip("/")
    if parsed.path.endswith("/") or parsed.path == "":
        file_path = file_path / "index.html"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(body)

def should_save(content_type):
    if not content_type:
        return False
    return any(hint in content_type.lower() for hint in TEXT_MIME_HINTS)

def crawl_site(target_url, wait_ms=WAIT_MS, headed=False):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context()
        page = context.new_page()

        def handle_response(response):
            try:
                if not response.ok:
                    return
                ctype = response.headers.get("content-type", "")
                if should_save(ctype):
                    # Retry .body() a few times if needed
                    for attempt in range(3):
                        try:
                            body = response.body()
                            save_asset(response.url, body)
                            break
                        except Exception as e:
                            if attempt == 2:
                                print(f"[!] Failed {response.url}: {e}")
                            else:
                                time.sleep(0.5)
                                continue
            except Exception as e:
                print(f"[!] Skipped {response.url}: {e}")

        page.on("response", handle_response)

        print(f"[+] Navigating to {target_url}")
        page.goto(target_url, wait_until="domcontentloaded")
        page.wait_for_timeout(wait_ms)  # SPA async chunk wait
        print("[+] Capture complete, closing browser...")

        browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <url> [wait_ms] [headed:true|false]")
        sys.exit(1)
    url = sys.argv[1]
    wait_time = int(sys.argv[2]) if len(sys.argv) > 2 else WAIT_MS
    headed = sys.argv[3].lower() == "true" if len(sys.argv) > 3 else False
    crawl_site(url, wait_time, headed)

