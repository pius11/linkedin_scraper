# 📖 LinkedIn Company Scraper — User & Usage Guide

This documentation provides comprehensive guidance on how to run and customize the **LinkedIn Company About Scraper**.

---

## 🎯 Target Output Schema

Every scraping run automatically extracts and exports clean, structured company data matching the exact 10 required headers:

| Header | Description | Example Value |
| :--- | :--- | :--- |
| `companyname` | Official legal / trade company name | `Shangri-La Group` |
| `companywebsite` | Direct corporate homepage URL | `https://www.shangri-la.com/group/` |
| `companyemaildomain` | Extracted root corporate email domain | `shangri-la.com` |
| `linkedincompanypageurl` | Canonical LinkedIn company page URL | `https://www.linkedin.com/company/shangri-la-hotels-and-resorts` |
| `stocksymbol` | Stock ticker symbol (if public) | `HKG: 0069` |
| `industry` | Standard English industry sector | `Hospitality` / `Hospitals and Health Care` |
| `city` | Headquarters city / suburb name | `Hong Kong` / `Denver` / `Sydney` |
| `state` | State / Province / Region name | `Colorado` / `New South Wales` |
| `companycountry` | Country name (Standard English) | `Hong Kong` / `United States` / `Australia` |
| `zipcode` | Postal / ZIP code | `80202` / `2036` / `SE1 9QU` |

---

## 🔑 Authentication & Session Management

The scraper uses a **persistent Chromium user profile** located at `./linkedin_session/`.

### First-Time Login:
1. When you run the scraper for the first time, a Chromium browser window will open.
2. If your session is not logged in, the scraper will pause and notify you in the terminal:
   ```
   [AUTH] NOTICE: LinkedIn session is not logged in!
   Please log in to your LinkedIn account in the browser window...
   ```
3. Log in to your LinkedIn account manually in the open browser window (including 2FA if enabled).
4. Once logged in, the scraper automatically detects authentication, saves the cookies/session into `./linkedin_session/`, and continues.
5. **On subsequent runs, you stay logged in automatically.**

---

## 🚀 How to Run the Scraper

### Mode 1: Interactive Wizard with In-Browser Filtering (Recommended)

This is the easiest and most flexible method. You select any official LinkedIn filter tags directly in the browser window.

```powershell
python main_company.py
```

#### Workflow Steps:
1. Run the command above.
2. Choose option `[1]` (*Configure Filters Manually in Browser*).
3. The browser window opens to LinkedIn Search.
4. Click **All filters** in LinkedIn and select your target Locations, Industry verticals, Company size, etc.
5. Click **Show results** on LinkedIn.
6. Switch back to your terminal, type `ok` (or `yes`), and press `ENTER`.
7. Enter how many pages you want to scrape (e.g. `2` pages $\approx$ 20 companies).
8. The scraper will automatically collect all target company links and visit their `/about/` pages to extract detailed information.

---

### Mode 2: Quick CLI Flags (Non-Interactive / Automated)

You can bypass the interactive menu by providing command-line arguments:

#### A. Manual Mode with Custom Page Limit:
```powershell
python main_company.py --manual --pages 3
```

#### B. Direct Search URL Mode:
Paste a pre-filtered LinkedIn search URL:
```powershell
python main_company.py --url "https://www.linkedin.com/search/results/companies/?companyHqGeo=%5B%22103313686%22%5D&industryCompanyVertical=%5B%2214%22%5D" --pages 2
```

#### C. Using Location ID (Geo ID) and Industry ID (Vertical ID):
```powershell
python main_company.py --geo 103313686 --industry 14 --pages 2
```

#### D. Scrape a Single Company Directly:
```powershell
python main_company.py --company "https://www.linkedin.com/company/shangri-la-hotels-and-resorts/about/"
```

#### E. Scrape from a File of Company URLs:
Create a text file `urls.txt` with one URL per line:
```powershell
python main_company.py --company-file urls.txt
```

---

## ⚙️ Available Command-Line Arguments

| Argument | Description | Default |
| :--- | :--- | :--- |
| `--manual` | Opens browser for manual in-browser filter selection | `False` |
| `--url <URL>` | Target LinkedIn company search results URL | `None` |
| `--pages <N>` | Maximum number of search pagination pages to scrape | `2` |
| `--geo <ID>` | LinkedIn Geo ID (`companyHqGeo`), comma-separated | `None` |
| `--industry <ID>` | LinkedIn Industry ID (`industryCompanyVertical`), comma-separated | `None` |
| `--company <URL>` | Single company URL to scrape directly | `None` |
| `--company-file <PATH>`| Text file containing list of company URLs (one per line) | `None` |
| `--headless` | Runs browser in background without graphical window | `False` |
| `--session <PATH>` | Custom directory for session cookies and storage | `./linkedin_session` |

---

## 🛡️ Key Architectural Features

1. **Anti-Filter-Reset Pagination:**
   The scraper clicks LinkedIn's native pagination `Next` button (`artdeco-pagination__button--next`) instead of modifying URLs directly. This ensures that custom complex search filters remain active throughout all pages.

2. **Modern SDUI & Classic Layout Parsing:**
   Supports both LinkedIn's Server-Driven UI (`<p>/<div>`) cards and classic `<dl>/<dt>/<dd>` layouts.

3. **Smart Address & Postal Code Parsing:**
   - Differentiates building numbers (e.g. `1500 Broadway`) from postal codes (e.g. `10036`).
   - Resolves UK formats (`SE1 9QU`), US/AU numeric formats (`80202`, `2036`), and street addresses.
   - Extracts primary headquarters marked with `Primary` / `Headquarters` badges.

4. **Multi-Language Normalization:**
   Automatically translates and standardizes Indonesian/foreign industry names into official English classifications (e.g. `Pelayanan Kesehatan Jiwa` $\rightarrow$ `Mental Health Care`, `Pariwisata dan Perhotelan` $\rightarrow$ `Hospitality`).

---

## 📁 Output Files

All extracted data is saved to the `./output/` directory:
- **CSV:** `./output/companies_about_YYYYMMDD_HHMMSS.csv` (encoded in `utf-8-sig` for perfect Excel compatibility).
- **Excel:** `./output/companies_about_YYYYMMDD_HHMMSS.xlsx`.

---

## 💡 Best Practices & Rate Limiting

- **Safe Delays:** The scraper incorporates built-in randomized delays (3.0s to 5.0s) between company page visits to emulate natural human browsing behavior.
- **Recommended Page Limits:** For daily operational runs, 5 to 10 pages (~50 to 100 companies per session) is optimal to maintain account health.
- **Session Reusability:** Do not delete the `./linkedin_session/` folder unless you wish to switch LinkedIn accounts.
