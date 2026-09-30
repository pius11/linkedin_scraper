"""
Main Execution Script: main_company.py
Runs the LinkedIn Company scraper to extract structured '/about/' data
with in-browser manual filter mode or URL-based parameters.

Exact Output CSV Headers:
companyname, companywebsite, companyemaildomain, linkedincompanypageurl,
stocksymbol, industry, city, state, companycountry, zipcode
"""

import argparse
import sys
import os
from datetime import datetime
from typing import Tuple, Optional, List
from company_scraper import LinkedInCompanyScraper, save_results, REQUIRED_HEADERS, clear_stdin_buffer

DEFAULT_TARGET_URL = (
    "https://www.linkedin.com/search/results/companies/"
    "?origin=FACETED_SEARCH"
    "&companyHqGeo=%5B%22103313686%22%5D"
    "&industryCompanyVertical=%5B%2231%22%5D"
)
DEFAULT_MAX_PAGES = 2
SESSION_DIR = "./linkedin_session"


def prompt_interactive_config() -> Tuple[Optional[str], int, bool]:
    """
    Interactive configuration wizard for user input:
    Provides manual in-browser filter selection, URL input, or preset defaults.
    """
    print("\n" + "=" * 70)
    print("      LINKEDIN COMPANY SCRAPER - CONFIGURATION & PAGE LIMIT")
    print("=" * 70)
    print("Choose search filter method:")
    print("  [1] Configure Filters Manually in Browser (Recommended)")
    print("      -> Browser opens, you freely select official tags on LinkedIn,")
    print("         then type 'ok' in terminal to start automated scraping!")
    print("  [2] Paste LinkedIn Search URL with Pre-applied Filters")
    print("  [3] Enter Location ID (Geo ID) and Industry ID (Vertical ID) manually")
    print("  [4] Use Default URL Preset (New South Wales + Hospitality)")
    print("-" * 70)

    clear_stdin_buffer()
    choice = input("Your choice [1/2/3/4] (Default 1): ").strip()
    if not choice:
        choice = "1"

    target_url = None
    manual_filter_mode = False

    if choice == "1":
        print("\n[OK] Manual In-Browser Filter Mode selected.")
        print("     The browser will open and you can apply location, industry,")
        print("     and other filters directly on LinkedIn's UI.")
        manual_filter_mode = True

    elif choice == "2":
        print("\nPlease copy the search URL from your browser's address bar.")
        clear_stdin_buffer()
        url_input = input("Paste LinkedIn Search URL here: ").strip()
        if url_input:
            target_url = url_input
        else:
            print("[INFO] Input was empty, switching to Manual In-Browser Mode.")
            manual_filter_mode = True

    elif choice == "3":
        print("\nExample IDs: 103313686 (NSW/Australia), 31 (Hospitality), 14 (Hospitals & Health Care), etc.")
        clear_stdin_buffer()
        geo_input = input("Enter Location ID / companyHqGeo (comma-separated): ").strip()
        ind_input = input("Enter Industry ID / industryCompanyVertical (comma-separated): ").strip()

        geo_list = [g.strip() for g in geo_input.split(",") if g.strip()] if geo_input else []
        ind_list = [i.strip() for i in ind_input.split(",") if i.strip()] if ind_input else []

        scraper_helper = LinkedInCompanyScraper()
        target_url = scraper_helper.build_search_url(
            location_geo_ids=geo_list,
            industry_vertical_ids=ind_list,
            page_number=1,
        )
        print(f"\n[OK] Search URL constructed: {target_url}")

    else:
        print("\nUsing Default Preset URL:")
        target_url = DEFAULT_TARGET_URL
        print(f"-> {target_url}")

    # Page Limit Input
    print("\n" + "-" * 70)
    print("How many search result pages do you want to scrape?")
    print("(Note: 1 LinkedIn page contains ~10 companies)")
    clear_stdin_buffer()
    page_input = input("Number of pages [e.g.: 1, 2, 5, 10] (Default 2): ").strip()

    try:
        max_pages = int(page_input) if page_input else DEFAULT_MAX_PAGES
        if max_pages < 1:
            max_pages = 1
    except ValueError:
        print("[!] Invalid input, defaulting to 2 pages.")
        max_pages = DEFAULT_MAX_PAGES

    return target_url, max_pages, manual_filter_mode


def main():
    parser = argparse.ArgumentParser(
        description="LinkedIn Company '/about/' Scraper with Custom Filters & Page Limit"
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Open browser and allow manual selection of location and industry filters",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="LinkedIn Search Results URL containing location and industry filters",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=None,
        help="Maximum number of search result pages to scrape",
    )
    parser.add_argument(
        "--geo",
        type=str,
        default=None,
        help="Location ID (companyHqGeo), comma-separated if multiple",
    )
    parser.add_argument(
        "--industry",
        type=str,
        default=None,
        help="Industry ID (industryCompanyVertical), comma-separated if multiple",
    )
    parser.add_argument(
        "--company",
        type=str,
        default=None,
        help="Scrape a single company URL directly (e.g. https://www.linkedin.com/company/nsw-justice-health/about/)",
    )
    parser.add_argument(
        "--company-file",
        type=str,
        default=None,
        help="Text file containing list of company URLs (one per line)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in background without GUI window",
    )
    parser.add_argument(
        "--session",
        type=str,
        default=SESSION_DIR,
        help="Directory storing persistent browser session data (default: ./linkedin_session)",
    )

    args = parser.parse_args()

    direct_urls = None
    target_url = args.url
    max_pages = args.pages
    manual_filter_mode = args.manual

    if args.company:
        direct_urls = [args.company]
    elif args.company_file:
        if os.path.exists(args.company_file):
            with open(args.company_file, "r", encoding="utf-8") as f:
                direct_urls = [line.strip() for line in f if line.strip()]
        else:
            print(f"[!] File not found: {args.company_file}")
            sys.exit(1)
    elif args.geo or args.industry:
        geo_list = [g.strip() for g in args.geo.split(",")] if args.geo else None
        ind_list = [i.strip() for i in args.industry.split(",")] if args.industry else None
        scraper_helper = LinkedInCompanyScraper()
        target_url = scraper_helper.build_search_url(
            location_geo_ids=geo_list,
            industry_vertical_ids=ind_list,
        )
        if not max_pages:
            max_pages = DEFAULT_MAX_PAGES
    elif not target_url and not direct_urls and not manual_filter_mode:
        target_url, max_pages, manual_filter_mode = prompt_interactive_config()
    else:
        if not max_pages:
            max_pages = DEFAULT_MAX_PAGES

    print("\n" + "=" * 70)
    print("               STARTING LINKEDIN COMPANY SCRAPER")
    print("=" * 70)
    if direct_urls:
        print(f"Target Mode   : Direct Company List ({len(direct_urls)} URLs)")
    elif manual_filter_mode:
        print(f"Target Mode   : Manual In-Browser Filter Mode")
        print(f"Page Limit    : {max_pages} pages (~{max_pages * 10} companies)")
    else:
        print(f"Target Search : {target_url}")
        print(f"Page Limit    : {max_pages} pages (~{max_pages * 10} companies)")

    print(f"Session Dir   : {args.session}")
    print(f"Headless Mode : {args.headless}")
    print("-" * 70)
    print("Output CSV Headers:")
    print("  " + ", ".join(REQUIRED_HEADERS))
    print("=" * 70)

    scraper = LinkedInCompanyScraper(
        user_data_dir=args.session,
        headless=args.headless,
        slow_mo=100,
        page_delay_min=3.0,
        page_delay_max=5.0,
    )

    start_time = datetime.now()

    try:
        results = scraper.scrape_companies(
            target_url=target_url,
            max_pages=max_pages,
            direct_company_urls=direct_urls,
            manual_filter_mode=manual_filter_mode,
        )

        print("\n" + "=" * 70)
        print(f"COMPLETE! Successfully processed {len(results)} companies.")
        print(f"Elapsed time: {datetime.now() - start_time}")
        print("=" * 70)

        if results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"companies_about_{timestamp}"
            saved_csv = save_results(results, base_filename=filename)
            print(f"\n[SUCCESS] Your data is ready in the ./output/ folder")
        else:
            print("\n[INFO] No company data was extracted.")

    except KeyboardInterrupt:
        print("\n[STOP] Process aborted by user.")
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
