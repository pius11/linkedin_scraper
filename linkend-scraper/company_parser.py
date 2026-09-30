"""
Module: company_parser.py
Parses company card details from LinkedIn Search Results HTML.
"""

from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any


def clean_text(text: str) -> str:
    """Cleans multiple whitespaces, \xa0, and &nbsp;."""
    if not text:
        return ""
    text = text.replace('\xa0', ' ').replace('&nbsp;', ' ')
    return re.sub(r'\s+', ' ', text).strip()


def parse_company_cards_from_html(html_content: str) -> List[Dict[str, Any]]:
    """
    Extracts company cards from LinkedIn search results HTML page.
    Supports modern desktop LinkedIn search results DOM structure.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    results = []
    seen_urls = set()

    # Find main list container
    list_container = soup.find(attrs={"role": "list"}) or soup

    # Find company result containers
    cards = list_container.find_all(attrs={"data-display-contents": "true"})
    
    # Fallback to finding company anchor links if data-display-contents is not found
    if not cards:
        cards = list_container.find_all("a", href=re.compile(r"linkedin\.com/company/[^/]+/?"))

    for card in cards:
        try:
            # 1. Company URL & Inner Links
            all_comp_links = card.find_all("a", href=re.compile(r"linkedin\.com/company/"))
            if not all_comp_links:
                continue

            raw_href = all_comp_links[0].get("href", "")
            company_url = raw_href.split("?")[0].rstrip("/")
            if not company_url.startswith("http"):
                company_url = f"https://www.linkedin.com{company_url}"

            if company_url in seen_urls:
                continue

            # 2. Company Name
            candidate_names = []
            for l in all_comp_links:
                txt = clean_text(l.text)
                if txt and not txt.lower().startswith("ikuti") and not txt.lower().startswith("follow"):
                    candidate_names.append(txt)

            if not candidate_names:
                continue

            company_name = min(candidate_names, key=len)

            # 3. Verified Badge Status
            verified_elem = card.find("svg", id="verified-small") or card.find(
                attrs={"aria-label": re.compile(r"terverifikasi|verified", re.I)}
            )
            is_verified = bool(verified_elem)

            # 4. Logo URL
            img_elem = card.find("img")
            logo_url = ""
            if img_elem:
                logo_url = img_elem.get("src") or img_elem.get("data-delayed-url", "")

            # 5. Listitem metadata (Industry & Location)
            listitem = card.find(attrs={"role": "listitem"}) or card
            industry = ""
            location = ""

            sub_info_ps = listitem.find_all("p")
            meta_texts = []
            for p in sub_info_ps:
                t = clean_text(p.text)
                if t and t != company_name and len(t) < 80:
                    meta_texts.append(t)

            if len(meta_texts) >= 1:
                industry = meta_texts[0]
            if len(meta_texts) >= 2:
                location = meta_texts[1]

            # 6. Description & Followers count
            description = ""
            followers_raw = ""
            followers_count = None

            follower_pattern = re.compile(r"([\d.,]+)\s*(?:pengikut|followers|follower)", re.I)

            for p in card.find_all("p"):
                t = clean_text(p.text)
                if not t:
                    continue
                f_match = follower_pattern.search(t)
                if f_match and not followers_raw:
                    followers_raw = t
                    digits = f_match.group(1).replace(".", "").replace(",", "")
                    try:
                        followers_count = int(digits)
                    except ValueError:
                        pass
                elif len(t) > 60 and not description and t != company_name:
                    description = t

            seen_urls.add(company_url)
            results.append({
                "company_name": company_name,
                "company_url": company_url,
                "industry": industry,
                "location": location,
                "followers": followers_raw,
                "followers_count": followers_count,
                "is_verified": is_verified,
                "description": description,
                "logo_url": logo_url
            })

        except Exception:
            continue

    return results
