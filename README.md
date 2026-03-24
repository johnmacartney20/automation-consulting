# automation-consulting
B2B business automations

---

## Scrape websites from Google Sheet with Firecrawl

`scrape_websites.py` reads a list of website URLs from a Google Sheet, scrapes
each site using [Firecrawl](https://firecrawl.dev), and stores the results
locally as Markdown and JSON files — ready to import into Claude for site
redesign analysis.

### How it works

1. Authenticates with Google Sheets via a **service account**.
2. Reads every URL from the configured sheet range.
3. Calls the Firecrawl API to scrape the full page content.
4. Writes results to `output/<domain>/`:
   - `content.md` — full page content in Markdown.
   - `metadata.json` — page metadata, title, description, and discovered links.

### Prerequisites

- Python 3.10+
- A [Firecrawl](https://firecrawl.dev) account and API key.
- A Google Cloud project with the **Google Sheets API** enabled and a
  **service account** with a downloaded credentials JSON file.

### Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment variables
cp .env.example .env
#    → Edit .env and fill in FIRECRAWL_API_KEY, GOOGLE_SPREADSHEET_ID, etc.

# 3. Place your Google service account credentials file
#    at the path set in GOOGLE_SERVICE_ACCOUNT_FILE (default: credentials.json)

# 4. Share the Google Sheet with the service account email address
#    (found inside credentials.json under "client_email")
```

#### Google Sheet format

The sheet should have one URL per row in the column(s) covered by
`GOOGLE_SHEET_RANGE` (default `Sheet1!A2:A100`).  The script reads the
**first cell of each row**, so a layout like this works:

| A (URL)                    | B (Notes)        |
|----------------------------|------------------|
| https://www.example.com    | Main site        |
| https://shop.acme.co.uk    | E-commerce store |

Row 1 is assumed to be a header and is skipped by the default range
(`A2:A100`).

### Usage

```bash
python scrape_websites.py
```

Output is written to the `output/` directory (configurable via `OUTPUT_DIR`):

```
output/
  example.com/
    content.md
    metadata.json
  shop.acme.co.uk/
    content.md
    metadata.json
```

### Environment variables

| Variable | Description | Default |
|---|---|---|
| `FIRECRAWL_API_KEY` | Your Firecrawl API key | *(required)* |
| `GOOGLE_SPREADSHEET_ID` | ID from the Google Sheet URL | *(required)* |
| `GOOGLE_SHEET_RANGE` | Sheet name and cell range to read | `Sheet1!A2:A100` |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Path to service account credentials JSON | `credentials.json` |
| `OUTPUT_DIR` | Directory where results are saved | `output` |
