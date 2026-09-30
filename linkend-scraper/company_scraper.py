"""
Module: company_scraper.py
LinkedIn Company Search & '/about/' page detail scraper using Playwright & BeautifulSoup.
Features persistent session profile and filter-preserving native pagination.
"""

import os
import re
import sys
import time
import random
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional

import pandas as pd
from playwright.sync_api import sync_playwright, Page, BrowserContext

from company_parser import parse_company_cards_from_html
from about_parser import (
    parse_about_page,
    extract_email_domain,
    parse_address_components,
    translate_country,
)


REQUIRED_HEADERS = [
    "companyname",
    "companywebsite",
    "companyemaildomain",
    "linkedincompanypageurl",
    "stocksymbol",
    "industry",
    "city",
    "state",
    "companycountry",
    "zipcode",
]


def clear_stdin_buffer():
    """Flushes trailing newline characters from stdin buffer so input() is not skipped."""
    try:
        if sys.platform == "win32":
            import msvcrt
            while msvcrt.kbhit():
                msvcrt.getch()
        else:
            import select
            while select.select([sys.stdin], [], [], 0)[0]:
                sys.stdin.read(1)
    except Exception:
        pass


class LinkedInCompanyScraper:
    def __init__(
        self,
        user_data_dir: str = "./linkedin_session",
        headless: bool = False,
        slow_mo: int = 100,
        page_delay_min: float = 2.5,
        page_delay_max: float = 4.5,
    ):
        self.user_data_dir = os.path.abspath(user_data_dir)
        self.headless = headless
        self.slow_mo = slow_mo
        self.page_delay_min = page_delay_min
        self.page_delay_max = page_delay_max

        os.makedirs(self.user_data_dir, exist_ok=True)

    def _sleep_random(self, min_sec: Optional[float] = None, max_sec: Optional[float] = None):
        """Sleeps for a random duration to simulate natural browsing delay."""
        min_s = min_sec or self.page_delay_min
        max_s = max_sec or self.page_delay_max
        time.sleep(random.uniform(min_s, max_s))

    def _scroll_page_smoothly(self, page: Page, steps: int = 5):
        """
        Scrolls down the page smoothly and safely in steps.
        Equipped with exception handling to prevent navigation context errors.
        """
        try:
            page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:
            pass

        viewport_height = 800
        try:
            if page.viewport_size:
                viewport_height = page.viewport_size.get("height", 800)
        except Exception:
            pass

        for i in range(1, steps + 1):
            scroll_to = (viewport_height * i) // 2
            try:
                page.evaluate(f"window.scrollTo({{ top: {scroll_to}, behavior: 'smooth' }});")
            except Exception:
                time.sleep(1.0)
            time.sleep(random.uniform(0.5, 0.9))

        try:
            page.evaluate("window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });")
        except Exception:
            pass
        time.sleep(random.uniform(0.8, 1.4))

    def ensure_logged_in(self, page: Page):
        """
        Checks LinkedIn authentication status. If not logged in, pauses for user to log in via browser window.
        """
        print("\n[AUTH] Verifying LinkedIn login status...")
        try:
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=45000)
        except Exception:
            pass
        self._sleep_random(2, 3)

        current_url = page.url.lower()
        is_logged_in = True
        if any(keyword in current_url for keyword in ["login", "uas/login", "authwall", "signup"]):
            is_logged_in = False
        else:
            try:
                nav_logged_in = page.locator("nav.global-nav, button.global-nav__primary-link, #global-nav").count() > 0
                if not nav_logged_in:
                    if page.locator("input#username, input#session_key").count() > 0:
                        is_logged_in = False
            except Exception:
                pass

        if not is_logged_in:
            print("\n" + "=" * 65)
            print("(!) NOTICE: LinkedIn session is not logged in!")
            print("    Please log in to your LinkedIn account in the browser window.")
            print("    The scraper will automatically resume once login is detected...")
            print("=" * 65 + "\n")

            start_wait = time.time()
            max_wait = 300
            while time.time() - start_wait < max_wait:
                time.sleep(3)
                try:
                    curr = page.url.lower()
                    if "feed" in curr or "search" in curr or page.locator("nav.global-nav, #global-nav").count() > 0:
                        print("[AUTH] Login detected successfully! Continuing process...\n")
                        self._sleep_random(2, 4)
                        return True
                except Exception:
                    pass

            raise TimeoutError("Login wait timeout exceeded. Please try again.")
        else:
            print("[AUTH] LinkedIn account is authenticated & ready.")
            return True

    def capture_manual_filters_in_browser(self) -> str:
        """
        Opens a visible browser window so the user can interactively select
        filters on LinkedIn's UI. Once confirmed with 'ok', captures the URL,
        closes the visible window, and returns the target URL for headless scraping.
        """
        print("\n[BROWSER] Opening visible browser window to configure filters...")
        chosen_url = ""
        with sync_playwright() as p:
            context: BrowserContext = p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False,
                slow_mo=100,
                locale="en-US",
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                    "--no-sandbox",
                ],
            )

            try:
                context.add_cookies([
                    {"name": "lang", "value": "v=2&lang=en-us", "domain": ".linkedin.com", "path": "/"},
                    {"name": "lang", "value": "v=2&lang=en-us", "domain": ".www.linkedin.com", "path": "/"},
                ])
            except Exception:
                pass

            page = context.pages[0] if context.pages else context.new_page()

            # Ensure authenticated
            self.ensure_logged_in(page)

            start_url = "https://www.linkedin.com/search/results/companies/?origin=FACETED_SEARCH"
            try:
                page.goto(start_url, wait_until="domcontentloaded", timeout=45000)
            except Exception:
                pass
            self._sleep_random(1.5, 2.5)

            print("\n" + "=" * 70)
            print("          MANUAL IN-BROWSER FILTER CONFIGURATION GUIDE")
            print("=" * 70)
            print("Your browser is now open on the LinkedIn Company Search page.")
            print("Please follow these steps in the open browser window:")
            print("  1. Click 'All filters' on the LinkedIn page.")
            print("  2. Select your desired 'Locations', 'Industry', and other official tags.")
            print("  3. Click 'Show results' in the browser to apply filters.")
            print("  4. Verify that your target company list is displayed on screen.")
            print("=" * 70)

            clear_stdin_buffer()

            def _get_live_browser_url() -> str:
                # 1. Check all open pages (tabs) in reverse to find any tab with active filters
                for p in reversed(context.pages):
                    try:
                        live_href = p.evaluate("() => window.location.href")
                        if "linkedin.com/search/results/companies" in live_href:
                            # If it has filter parameters, prioritize this tab
                            if any(param in live_href for param in ["companyHqGeo", "industryCompanyVertical", "keywords", "geoUrn", "facet"]):
                                return live_href
                    except Exception:
                        pass

                # 2. Otherwise get live URL of the most recent page
                if context.pages:
                    try:
                        return context.pages[-1].evaluate("() => window.location.href")
                    except Exception:
                        return context.pages[-1].url
                return page.url

            while True:
                prompt_text = (
                    "\n>> [WAITING FOR YOU IN BROWSER]\n"
                    "   Type 'ok' (or paste the URL directly) then press ENTER once filters are applied: "
                )
                user_input = input(prompt_text).strip()

                if not user_input:
                    continue

                # If user pasted a direct LinkedIn search URL
                if user_input.startswith("http://") or user_input.startswith("https://"):
                    if "linkedin.com/search/results/companies" in user_input:
                        chosen_url = user_input
                        break
                    else:
                        print(f"   [!] URL does not seem to be a LinkedIn Company search URL: {user_input}")
                        continue

                user_input_lower = user_input.lower()
                if user_input_lower in ["ok", "siap", "yes", "y", "done", "lanjut", "1"]:
                    curr_url = _get_live_browser_url()
                    is_default = (
                        curr_url.rstrip("/") == start_url.rstrip("/") 
                        or curr_url.endswith("?origin=FACETED_SEARCH")
                        or (curr_url.count("?") == 1 and curr_url.endswith("origin=FACETED_SEARCH") and "companyHqGeo" not in curr_url and "industryCompanyVertical" not in curr_url and "keywords" not in curr_url)
                    )
                    if is_default:
                        print("\n[!] NOTICE: The current browser URL does not have active filter parameters:")
                        print(f"    Current URL: {curr_url}")
                        print("    Did you click 'Show results' in LinkedIn after selecting filters?")
                        print("    (Tip: You can also copy & paste the URL directly from the browser address bar into this prompt)")
                        clear_stdin_buffer()
                        confirm = input("    Proceed with this URL anyway? [y/n] (Default n): ").strip().lower()
                        if confirm in ["y", "yes", "ok", "1"]:
                            chosen_url = curr_url
                            break
                        else:
                            print("    [+] Please click 'Show results' on LinkedIn, then type 'ok' (or paste the URL) again.")
                            continue
                    else:
                        chosen_url = curr_url
                        break
                else:
                    print("   [!] Please type 'ok' or paste the URL, then press ENTER.")

            time.sleep(0.5)
            # Final check to get exact URL
            if not chosen_url:
                chosen_url = _get_live_browser_url()

            print(f"\n[OK] Search filter URL captured from browser:")
            print(f"     {chosen_url}")
            print("[INFO] Closing visible setup window. Switching to HEADLESS background scraping...\n")
            context.close()

        # Cooldown delay to allow Chromium to cleanly release socket and file locks
        time.sleep(2.0)
        return chosen_url

    def build_search_url(
        self,
        keywords: Optional[str] = None,
        location_geo_ids: Optional[List[str]] = None,
        industry_vertical_ids: Optional[List[str]] = None,
        page_number: int = 1,
    ) -> str:
        """
        Builds a valid LinkedIn Company Search URL with filter parameters.
        """
        base_url = "https://www.linkedin.com/search/results/companies/"
        params = {"origin": "FACETED_SEARCH"}

        if keywords:
            params["keywords"] = keywords

        if location_geo_ids:
            geo_json = "[" + ",".join([f'"{g}"' for g in location_geo_ids]) + "]"
            params["companyHqGeo"] = geo_json

        if industry_vertical_ids:
            ind_json = "[" + ",".join([f'"{i}"' for i in industry_vertical_ids]) + "]"
            params["industryCompanyVertical"] = ind_json

        if page_number > 1:
            params["page"] = str(page_number)

        query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        return f"{base_url}?{query_string}"

    def scrape_company_about(self, page: Page, company_base_url: str, fallback_data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Navigates to the company's '/about/' page and extracts full details.
        """
        clean_url = company_base_url.rstrip("/")
        if not clean_url.endswith("/about"):
            about_url = f"{clean_url}/about/"
        else:
            about_url = f"{clean_url}/"

        print(f"  --> Opening About Page: {about_url}")
        data = {h: "" for h in REQUIRED_HEADERS}
        data["linkedincompanypageurl"] = clean_url.replace("/about", "")

        try:
            page.goto(about_url, wait_until="domcontentloaded", timeout=45000)
            self._sleep_random(2.0, 3.2)

            # Scroll down so dynamic SDUI modules (overview, website, primary location) finish mounting
            try:
                page.evaluate("window.scrollBy(0, 500);")
            except Exception:
                pass
            time.sleep(random.uniform(1.0, 1.8))

            html = page.content()
            data = parse_about_page(html, linkedin_company_url=clean_url)

            # Fallback for any missing values from the search result snippet
            if fallback_data:
                if (not data["companyname"] or data["companyname"].lower() in ["0 notifications", "0 notifikasi", "notification", "notifikasi", "linkedin"]) and fallback_data.get("company_name"):
                    data["companyname"] = fallback_data["company_name"]
                if not data["industry"] and fallback_data.get("industry"):
                    data["industry"] = fallback_data["industry"]
                if not data["city"] and fallback_data.get("location"):
                    c, s, co, z = parse_address_components(fallback_data["location"])
                    data["city"] = c or fallback_data["location"]
                    if s: data["state"] = s
                    if co: data["companycountry"] = translate_country(co)
                    if z: data["zipcode"] = z

        except Exception as e:
            print(f"  [!] Notice during about page fetch ({e})")
            if fallback_data:
                data["companyname"] = fallback_data.get("company_name", "")
                data["industry"] = fallback_data.get("industry", "")
                c, s, co, z = parse_address_components(fallback_data.get("location", ""))
                data["city"] = c
                data["state"] = s
                data["companycountry"] = translate_country(co)
                data["zipcode"] = z

        return data

    def scrape_companies(
        self,
        target_url: Optional[str] = None,
        max_pages: int = 2,
        direct_company_urls: Optional[List[str]] = None,
        manual_filter_mode: bool = False,
    ) -> List[Dict[str, str]]:
        """
        Executes end-to-end scraping workflow:
        1. If manual filter mode is on, captures filter URL in visible browser first
        2. Launches scraping context in headless background mode
        3. Collects company URLs across pagination using native Next button (retaining all active filters)
        4. Visits each company's '/about/' page to extract complete structured data
        """
        final_results: List[Dict[str, str]] = []
        seen_companies = set()

        # PHASE 1: Capture manual filters in visible browser if requested
        if manual_filter_mode and not target_url and not direct_company_urls:
            target_url = self.capture_manual_filters_in_browser()
            # Once captured, run headless background scraping for quiet, efficient execution
            active_headless = True
        else:
            active_headless = self.headless

        # PHASE 2: Main Scraping Execution
        with sync_playwright() as p:
            mode_desc = "Headless Background Mode" if active_headless else "Visible Browser Mode"
            print(f"[BROWSER] Launching scraper in {mode_desc} (session: {self.user_data_dir})")
            context: BrowserContext = p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=active_headless,
                slow_mo=self.slow_mo,
                locale="en-US",
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                    "--no-sandbox",
                ],
            )

            try:
                context.add_cookies([
                    {"name": "lang", "value": "v=2&lang=en-us", "domain": ".linkedin.com", "path": "/"},
                    {"name": "lang", "value": "v=2&lang=en-us", "domain": ".www.linkedin.com", "path": "/"},
                ])
            except Exception:
                pass

            page = context.pages[0] if context.pages else context.new_page()

            # Ensure authenticated
            self.ensure_logged_in(page)

            companies_to_visit: List[Dict[str, Any]] = []

            # DIRECT COMPANY URL LIST MODE
            if direct_company_urls:
                for u in direct_company_urls:
                    companies_to_visit.append({"company_url": u, "company_name": "", "industry": "", "location": ""})
            else:
                try:
                    page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                    self._sleep_random(2.0, 3.5)
                except Exception as e:
                    print(f"  [!] Initial navigation notice: {e}")

                # STEP 1: COLLECT COMPANY CARDS FROM SEARCH RESULTS
                print("\n" + "=" * 65)
                print("STEP 1: COLLECTING TARGET COMPANIES FROM FILTERED SEARCH")
                print("=" * 65)

                for page_idx in range(1, max_pages + 1):
                    current_url_active = page.url
                    print(f"\n[*] Processing Search Page {page_idx}/{max_pages}:")
                    print(f"    {current_url_active}")

                    try:
                        page.wait_for_selector('div[role="list"], div[role="listitem"]', timeout=15000)
                    except Exception as e:
                        print(f"  [!] Card render notice: {e}")

                    # Smooth scroll to ensure all cards on active page render
                    self._scroll_page_smoothly(page, steps=6)

                    # Snapshot HTML
                    try:
                        html_content = page.content()
                    except Exception:
                        time.sleep(2)
                        html_content = page.content()

                    found_cards = parse_company_cards_from_html(html_content)

                    new_count = 0
                    for c in found_cards:
                        url = c["company_url"]
                        if url not in seen_companies:
                            seen_companies.add(url)
                            companies_to_visit.append(c)
                            new_count += 1
                            print(f"  [+] Found: {c['company_name']} ({url})")

                    print(f"[*] Page {page_idx} complete: Found {len(found_cards)} cards ({new_count} new). Total collected: {len(companies_to_visit)}")

                    if len(found_cards) == 0:
                        print("[!] No further results found on this page.")
                        break

                    # NAVIGATE TO NEXT PAGE USING LINKEDIN NATIVE NEXT BUTTON
                    if page_idx < max_pages:
                        print(f"[*] Navigating to Page {page_idx + 1}...")
                        next_clicked = False

                        try:
                            # Scroll down so pagination controls are visible
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(1.0)

                            # Locate native Next button
                            next_btn = page.locator(
                                'button.artdeco-pagination__button--next, '
                                'button[aria-label*="next" i], '
                                'button[aria-label*="berikutnya" i], '
                                'button:has-text("Next"), '
                                'button:has-text("Berikutnya")'
                            ).first

                            if next_btn.is_visible(timeout=3000) and not next_btn.is_disabled():
                                next_btn.click()
                                print("  [+] Clicked native 'Next' button (All filters preserved).")
                                next_clicked = True
                                self._sleep_random(3.0, 4.5)
                                try:
                                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                                except Exception:
                                    pass
                            else:
                                # Try clicking page number button directly
                                page_num_btn = page.locator(f'li.artdeco-pagination__indicator--number button:has-text("{page_idx + 1}")').first
                                if page_num_btn.is_visible(timeout=2000):
                                    page_num_btn.click()
                                    print(f"  [+] Clicked page number button {page_idx + 1}.")
                                    next_clicked = True
                                    self._sleep_random(3.0, 4.5)
                                    try:
                                        page.wait_for_load_state("domcontentloaded", timeout=15000)
                                    except Exception:
                                        pass
                        except Exception as e:
                            print(f"  [!] Pagination click notice: {e}")

                        # URL-based fallback retaining active filter query
                        if not next_clicked:
                            curr_url = page.url
                            if "page=" in curr_url:
                                next_url = re.sub(r"page=\d+", f"page={page_idx + 1}", curr_url)
                            else:
                                sep = "&" if "?" in curr_url else "?"
                                next_url = f"{curr_url}{sep}page={page_idx + 1}"

                            print(f"  [Fallback] Opening Page {page_idx + 1} URL: {next_url}")
                            try:
                                page.goto(next_url, wait_until="domcontentloaded", timeout=60000)
                                self._sleep_random(3.0, 4.5)
                            except Exception as e:
                                print(f"  [!] Fallback navigation notice: {e}")
                                break

                # STEP 2: SCRAPE COMPANY ABOUT PAGES
                print("\n" + "=" * 65)
                print(f"STEP 2: EXTRACTING DETAILS FROM /about/ PAGES ({len(companies_to_visit)} COMPANIES)")
                print("=" * 65)

                for idx, comp in enumerate(companies_to_visit, 1):
                    url = comp["company_url"]
                    name_preview = comp.get("company_name") or url.split("/")[-1]
                    print(f"\n[{idx}/{len(companies_to_visit)}] Fetching About Details: {name_preview}")

                    detail = self.scrape_company_about(page, company_base_url=url, fallback_data=comp)
                    final_results.append(detail)

                    print(f"  [OK] Name    : {detail['companyname']}")
                    print(f"       Website : {detail['companywebsite']}")
                    print(f"       Domain  : {detail['companyemaildomain']}")
                    print(f"       Industry: {detail['industry']}")
                    print(f"       City    : {detail['city']} | State: {detail['state']} | Country: {detail['companycountry']} | Zip: {detail['zipcode']}")

                    self._sleep_random(self.page_delay_min, self.page_delay_max)

            context.close()

        return final_results


def save_results(data: List[Dict[str, str]], base_filename: Optional[str] = None) -> str:
    """
    Saves scraping results to CSV and Excel files with standard required headers.
    """
    if not data:
        print("[!] No data to save.")
        return ""

    if not base_filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"companies_about_{timestamp}"

    output_dir = "./output"
    os.makedirs(output_dir, exist_ok=True)

    csv_path = os.path.join(output_dir, f"{base_filename}.csv")
    excel_path = os.path.join(output_dir, f"{base_filename}.xlsx")

    df = pd.DataFrame(data)

    for col in REQUIRED_HEADERS:
        if col not in df.columns:
            df[col] = ""
    df = df[REQUIRED_HEADERS]

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n[OK] CSV file saved to   : {csv_path}")

    try:
        df.to_excel(excel_path, index=False, engine="openpyxl")
        print(f"[OK] Excel file saved to : {excel_path}")
    except Exception as e:
        print(f"[!] Excel export notice: {e}")

    return csv_path
