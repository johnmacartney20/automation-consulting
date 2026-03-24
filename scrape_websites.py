"""
scrape_websites.py

Reads website URLs from a Google Sheet, scrapes each site using Firecrawl,
and stores the results locally for later import into Claude.

Setup:
    1. Copy .env.example to .env and fill in your values.
    2. Place your Google service account credentials JSON at the path set
       in GOOGLE_SERVICE_ACCOUNT_FILE (default: credentials.json).
    3. Share the Google Sheet with the service account email address.
    4. pip install -r requirements.txt
    5. python scrape_websites.py
"""

import json
import os
import re
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration (read from .env)
# ---------------------------------------------------------------------------
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")
SPREADSHEET_ID = os.environ.get("GOOGLE_SPREADSHEET_ID", "")
SHEET_RANGE = os.environ.get("GOOGLE_SHEET_RANGE", "Sheet1!A2:A100")
SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output")

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def _validate_config() -> None:
    """Raise a descriptive error when required configuration is missing."""
    missing = []
    if not FIRECRAWL_API_KEY:
        missing.append("FIRECRAWL_API_KEY")
    if not SPREADSHEET_ID:
        missing.append("GOOGLE_SPREADSHEET_ID")
    if not os.path.isfile(SERVICE_ACCOUNT_FILE):
        missing.append(f"GOOGLE_SERVICE_ACCOUNT_FILE (file not found: {SERVICE_ACCOUNT_FILE})")
    if missing:
        print("ERROR: Missing required configuration:\n  " + "\n  ".join(missing))
        print("Copy .env.example to .env and fill in the required values.")
        sys.exit(1)


def _get_sheet_urls() -> list[str]:
    """Return the list of URLs from the configured Google Sheet range."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=GOOGLE_SCOPES
    )
    service = build("sheets", "v4", credentials=creds)
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=SHEET_RANGE)
        .execute()
    )
    rows = result.get("values", [])
    # Each row is a list; take only the first cell and strip whitespace.
    urls = [row[0].strip() for row in rows if row and row[0].strip()]
    return urls


def _safe_dirname(url: str) -> str:
    """
    Convert a URL into a filesystem-safe directory name.

    Examples:
        https://www.example.com  ->  example.com
        https://shop.acme.co.uk/path  ->  shop.acme.co.uk
    """
    parsed = urlparse(url)
    host = parsed.netloc or parsed.path
    # Remove any characters that are not alphanumeric, hyphens, or dots.
    safe = re.sub(r"[^\w.\-]", "_", host)
    return safe or "unknown"


def _scrape_url(app: FirecrawlApp, url: str) -> dict:
    """
    Scrape a single URL with Firecrawl and return a dict with:
        - url         original URL
        - markdown    full page content as markdown
        - metadata    page metadata (title, description, etc.)
    """
    result = app.scrape_url(
        url,
        formats=["markdown", "links"],
    )
    return {
        "url": url,
        "markdown": result.markdown or "",
        "metadata": result.metadata.model_dump() if result.metadata else {},
        "links": result.links or [],
    }


def _save_result(result: dict) -> None:
    """Persist the scrape result to disk."""
    site_dir = os.path.join(OUTPUT_DIR, _safe_dirname(result["url"]))
    os.makedirs(site_dir, exist_ok=True)

    md_path = os.path.join(site_dir, "content.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(f"# {result['url']}\n\n")
        fh.write(result["markdown"])

    meta_path = os.path.join(site_dir, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "url": result["url"],
                "metadata": result["metadata"],
                "links": result["links"],
            },
            fh,
            indent=2,
            ensure_ascii=False,
        )

    print(f"  Saved: {site_dir}/")


def main() -> None:
    _validate_config()

    print("Fetching URLs from Google Sheet...")
    urls = _get_sheet_urls()
    if not urls:
        print("No URLs found in the specified sheet range. Nothing to do.")
        return
    print(f"Found {len(urls)} URL(s).\n")

    app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for i, url in enumerate(urls, start=1):
        print(f"[{i}/{len(urls)}] Scraping: {url}")
        try:
            result = _scrape_url(app, url)
            _save_result(result)
        except Exception as exc:  # noqa: BLE001
            print(
                f"  ERROR scraping {url}: {exc}\n"
                "  Possible causes: invalid URL, network connectivity issue, "
                "invalid or rate-limited Firecrawl API key, or the site blocks scrapers.\n"
                "  Skipping and continuing with remaining URLs."
            )

    print(f"\nDone. Results are stored in '{OUTPUT_DIR}/'.")


if __name__ == "__main__":
    main()
