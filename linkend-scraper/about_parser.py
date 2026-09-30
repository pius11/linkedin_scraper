"""
Module: about_parser.py
Extracts company details from LinkedIn Company '/about/' pages:
- companyname
- companywebsite
- companyemaildomain
- linkedincompanypageurl
- stocksymbol
- industry (native LinkedIn industry value)
- city
- state
- companycountry (normalized to standard English)
- zipcode
"""

import re
import urllib.parse
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, Tuple


# Country name mapping & normalization dictionary
COUNTRY_TRANSLATION_MAP = {
    "au": "Australia",
    "australia": "Australia",
    "us": "United States",
    "usa": "United States",
    "united states": "United States",
    "amerika serikat": "United States",
    "uk": "United Kingdom",
    "united kingdom": "United Kingdom",
    "britania raya": "United Kingdom",
    "inggris raya": "United Kingdom",
    "inggris": "United Kingdom",
    "gb": "United Kingdom",
    "great britain": "United Kingdom",
    "cina": "China",
    "tiongkok": "China",
    "china": "China",
    "jerman": "Germany",
    "germany": "Germany",
    "belanda": "Netherlands",
    "netherlands": "Netherlands",
    "prancis": "France",
    "france": "France",
    "spanyol": "Spain",
    "spain": "Spain",
    "italia": "Italy",
    "italy": "Italy",
    "jepang": "Japan",
    "japan": "Japan",
    "korea selatan": "South Korea",
    "south korea": "South Korea",
    "uni emirat arab": "United Arab Emirates",
    "united arab emirates": "United Arab Emirates",
    "arab saudi": "Saudi Arabia",
    "saudi arabia": "Saudi Arabia",
    "selandia baru": "New Zealand",
    "new zealand": "New Zealand",
    "rusia": "Russia",
    "russia": "Russia",
    "swiss": "Switzerland",
    "switzerland": "Switzerland",
    "swedia": "Sweden",
    "norwegia": "Norway",
    "denmark": "Denmark",
    "singapura": "Singapore",
    "singapore": "Singapore",
    "kanada": "Canada",
    "canada": "Canada",
    "hong kong": "Hong Kong",
    "indonesia": "Indonesia",
    "malaysia": "Malaysia",
    "filipina": "Philippines",
    "philippines": "Philippines",
    "thailand": "Thailand",
    "vietnam": "Vietnam",
    "india": "India",
    "brazil": "Brazil",
    "meksiko": "Mexico",
    "mexico": "Mexico",
    "afrika selatan": "South Africa",
    "south africa": "South Africa",
}

# State / Region / Subdivision dictionary
STATE_MAP = {
    # Australia
    "nsw": ("New South Wales", "Australia"),
    "new south wales": ("New South Wales", "Australia"),
    "vic": ("Victoria", "Australia"),
    "victoria": ("Victoria", "Australia"),
    "qld": ("Queensland", "Australia"),
    "queensland": ("Queensland", "Australia"),
    "wa": ("Western Australia", "Australia"),
    "western australia": ("Western Australia", "Australia"),
    "sa": ("South Australia", "Australia"),
    "south australia": ("South Australia", "Australia"),
    "tas": ("Tasmania", "Australia"),
    "tasmania": ("Tasmania", "Australia"),
    "act": ("Australian Capital Territory", "Australia"),
    "australian capital territory": ("Australian Capital Territory", "Australia"),
    "nt": ("Northern Territory", "Australia"),
    "northern territory": ("Northern Territory", "Australia"),
    # United States
    "ca": ("California", "United States"),
    "california": ("California", "United States"),
    "ny": ("New York", "United States"),
    "new york": ("New York", "United States"),
    "tx": ("Texas", "United States"),
    "texas": ("Texas", "United States"),
    "fl": ("Florida", "United States"),
    "florida": ("Florida", "United States"),
    "il": ("Illinois", "United States"),
    "illinois": ("Illinois", "United States"),
    "in": ("Indiana", "United States"),
    "indiana": ("Indiana", "United States"),
    "co": ("Colorado", "United States"),
    "colorado": ("Colorado", "United States"),
    "ma": ("Massachusetts", "United States"),
    "massachusetts": ("Massachusetts", "United States"),
    "nc": ("North Carolina", "United States"),
    "north carolina": ("North Carolina", "United States"),
    "de": ("Delaware", "United States"),
    "delaware": ("Delaware", "United States"),
    "ga": ("Georgia", "United States"),
    "georgia": ("Georgia", "United States"),
    "oh": ("Ohio", "United States"),
    "ohio": ("Ohio", "United States"),
    "pa": ("Pennsylvania", "United States"),
    "pennsylvania": ("Pennsylvania", "United States"),
    "az": ("Arizona", "United States"),
    "arizona": ("Arizona", "United States"),
    "mi": ("Michigan", "United States"),
    "michigan": ("Michigan", "United States"),
    "va": ("Virginia", "United States"),
    "virginia": ("Virginia", "United States"),
    # UK Regions
    "england": ("England", "United Kingdom"),
    "scotland": ("Scotland", "United Kingdom"),
    "wales": ("Wales", "United Kingdom"),
    "northern ireland": ("Northern Ireland", "United Kingdom"),
}

# Major Australian cities lookup for automatic state resolution
AU_CITIES = {
    "sydney": ("New South Wales", "Australia"),
    "melbourne": ("Victoria", "Australia"),
    "brisbane": ("Queensland", "Australia"),
    "perth": ("Western Australia", "Australia"),
    "adelaide": ("South Australia", "Australia"),
    "canberra": ("Australian Capital Territory", "Australia"),
    "hobart": ("Tasmania", "Australia"),
    "darwin": ("Northern Territory", "Australia"),
    "gold coast": ("Queensland", "Australia"),
    "newcastle": ("New South Wales", "Australia"),
    "cairns": ("Queensland", "Australia"),
    "deakin": ("Australian Capital Territory", "Australia"),
    "randwick": ("New South Wales", "Australia"),
    "camberwell": ("Victoria", "Australia"),
    "st leonards": ("New South Wales", "Australia"),
    "st. leonards": ("New South Wales", "Australia"),
    "parkville": ("Victoria", "Australia"),
    "clayton": ("Victoria", "Australia"),
    "collingwood": ("Victoria", "Australia"),
    "richmond": ("Victoria", "Australia"),
    "bondi junction": ("New South Wales", "Australia"),
    "ultimo": ("New South Wales", "Australia"),
    "cotton tree": ("Queensland", "Australia"),
    "south yarra": ("Victoria", "Australia"),
    "mcmahons point": ("New South Wales", "Australia"),
    "north sydney": ("New South Wales", "Australia"),
}


def clean_text(text: str) -> str:
    """Cleans multiple whitespaces, newlines, and non-breaking space characters."""
    if not text:
        return ""
    text = text.replace('\xa0', ' ').replace('&nbsp;', ' ')
    return re.sub(r'\s+', ' ', text).strip()


def translate_country(country_str: str) -> str:
    """Translates and normalizes country name/code to standard English."""
    if not country_str:
        return ""
    cleaned = clean_text(country_str)
    lookup_key = cleaned.lower()
    return COUNTRY_TRANSLATION_MAP.get(lookup_key, cleaned)


def extract_email_domain(website_url: str) -> str:
    """
    Extracts the root email domain from a website URL.
    Example: 'https://www.shangri-la.com/group/' -> 'shangri-la.com'
    """
    if not website_url:
        return ""
    try:
        url = website_url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        parsed = urlparse(url)
        netloc = parsed.netloc or parsed.path
        netloc = netloc.split(":")[0]
        domain = re.sub(r"^www\.", "", netloc, flags=re.I)
        domain = domain.split("/")[0].strip().lower()
        return domain
    except Exception:
        return ""


def clean_redirect_url(url: str) -> str:
    """Extracts target external URL if LinkedIn uses an outbound redirect URL."""
    if not url:
        return ""
    if "linkedin.com/safety/go/" in url or "linkedin.com/redir" in url:
        match = re.search(r"url=([^&]+)", url)
        if match:
            return urllib.parse.unquote(match.group(1))
    return url


def get_label_value(elem) -> Tuple[str, str]:
    """Retrieves (val_text, val_link) from the nearest sibling of a label element."""
    sib = elem.find_next_sibling()
    if not sib and elem.parent:
        sib = elem.parent.find_next_sibling()

    val_text = ""
    val_link = ""
    if sib:
        val_text = clean_text(sib.text)
        a_tag = sib.find("a") if hasattr(sib, "find") else None
        if a_tag and a_tag.get("href"):
            val_link = clean_redirect_url(a_tag["href"])

    return val_text, val_link


def parse_address_components(address_str: str, country_hint: str = "") -> Tuple[str, str, str, str]:
    """
    Splits a headquarters address string into (city, state, companycountry, zipcode)
    with smart handling of various international and US/AU address formats:
    - Format 1: 'Sydney' with country_hint='Australia'
    - Format 2: 'Brisbane, Queensland' with country_hint='Australia'
    - Format 3: '1500 Broadway, New York, NY 10036, United States'
    - Format 4: 'Denver, Colorado 80202, United States'
    - Format 5: '31 St Thomas Street, London, England SE1 9QU'
    - Format 6: 'South Bend, IN'
    """
    city = ""
    state = ""
    country = ""
    zipcode = ""

    if not address_str and not country_hint:
        return city, state, country, zipcode

    text = clean_text(address_str)

    # 1. Zipcode / Postal Code Extraction
    # UK Format (e.g. SE1 9QU, EC1A 1BB)
    uk_zip = re.search(r'\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b', text)
    if uk_zip:
        zipcode = uk_zip.group(1)
        text = text.replace(zipcode, "").strip()
    else:
        # US / AU / International postal codes appear near the end (after State), NOT street numbers at the front!
        # Pattern 1: State + Zip (e.g. 'NY 10036', 'VA 22033', 'NSW 2060', 'Colorado 80202')
        state_zip_m = re.search(r'(?:[A-Z]{2}|[A-Za-z]+)\s+(\d{4,5}(?:-\d{4})?)\b(?:\s*,\s*(?:US|USA|AU|United States|Australia))?$', text.strip(), re.I)
        if state_zip_m:
            zipcode = state_zip_m.group(1)
            text = text[:state_zip_m.start(1)] + text[state_zip_m.end(1):]
        else:
            # Pattern 2: Search for postal code ONLY in tail parts to avoid street numbers
            parts_temp = text.split(",")
            if len(parts_temp) > 1:
                search_area = ", ".join(parts_temp[1:])
                matches = list(re.finditer(r'\b(\d{4,6}(?:-\d{4})?)\b', search_area))
                if matches:
                    zipcode = matches[-1].group(1)
                    idx_in_tail = matches[-1].start(1)
                    tail_replaced = search_area[:idx_in_tail] + search_area[idx_in_tail + len(zipcode):]
                    text = parts_temp[0] + ", " + tail_replaced
            else:
                num_end = re.search(r'\b(\d{4,6}(?:-\d{4})?)$', text)
                if num_end:
                    zipcode = num_end.group(1)
                    text = text[:num_end.start(1)].strip()

    text = re.sub(r',\s*,', ',', text).strip(' ,')

    if country_hint:
        country = translate_country(country_hint)

    parts = [clean_text(p) for p in text.split(',') if clean_text(p)]

    # Check if last part is Country
    if parts:
        last_p = parts[-1].lower()
        if last_p in COUNTRY_TRANSLATION_MAP:
            country = COUNTRY_TRANSLATION_MAP[last_p]
            parts.pop()

    # Check if any remaining part is State / Province
    for i in range(len(parts) - 1, -1, -1):
        p_low = parts[i].lower()
        if p_low in STATE_MAP:
            st_name, st_country = STATE_MAP[p_low]
            state = st_name
            if not country:
                country = st_country
            parts.pop(i)
            break

    # City resolution from remaining parts (stripping leading street numbers if present)
    if parts:
        if len(parts) == 1:
            city = parts[0]
        elif len(parts) == 2:
            # If parts[0] starts with street digits (e.g. '1500 Broadway'), city is parts[1] ('New York')
            if re.match(r'^\d+\s+', parts[0]):
                city = parts[1]
            else:
                city = parts[0]
                if not state:
                    p1_low = parts[1].lower()
                    if p1_low in STATE_MAP:
                        state = STATE_MAP[p1_low][0]
                    else:
                        state = parts[1]
        else:
            city = parts[-1]

    # Scoped State resolution for Australian major cities
    city_low = city.lower()
    if country in ["Australia", ""] and city_low in AU_CITIES:
        au_st, au_co = AU_CITIES[city_low]
        if not state:
            state = au_st
        if not country:
            country = au_co

    return clean_text(city), clean_text(state), clean_text(country), clean_text(zipcode)


def parse_about_page(html_content: str, linkedin_company_url: str = "") -> Dict[str, str]:
    """
    Parses details from a LinkedIn Company '/about/' page.
    Supports both Modern LinkedIn SDUI (<p>/<div>) and Classic (<dl>/<dt>/<dd>) layouts.
    Returns a dictionary with the exact 10 required headers:
    companyname, companywebsite, companyemaildomain, linkedincompanypageurl,
    stocksymbol, industry, city, state, companycountry, zipcode
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Company Name
    companyname = ""

    # Method 1: Extract from <title> tag
    title_elem = soup.find("title")
    if title_elem and clean_text(title_elem.text):
        raw_title = clean_text(title_elem.text)
        clean_title = raw_title.split("|")[0].strip()
        for suffix in [": about", ": overview", ": tentang", ": home", ": posts", ": posting", ": jobs", ": pekerjaan", ": life", ": people"]:
            if suffix in clean_title.lower():
                idx = clean_title.lower().find(suffix)
                clean_title = clean_title[:idx].strip()
        if clean_title and clean_title.lower() not in ["linkedin", "overview", "tentang", "about", "0 notifications", "0 notifikasi"]:
            companyname = clean_title

    # Method 2: Fallback to og:title
    if not companyname:
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            raw_og = clean_text(og_title["content"]).split("|")[0].split(":")[0].strip()
            if raw_og and raw_og.lower() not in ["linkedin", "0 notifications", "0 notifikasi"]:
                companyname = raw_og

    # Method 3: Fallback to heading h1 / h2 inside profile card
    if not companyname:
        for tag_name in ["h1", "h2"]:
            for h in soup.find_all(tag_name):
                txt = clean_text(h.text)
                if not txt:
                    continue
                if any(ign in txt.lower() for ign in [
                    "notification", "notifikasi", "toast", "gambaran umum", "lokasi",
                    "opsi iklan", "tentang", "overview", "affiliate", "afiliasi", "dialog",
                    "sign in", "login", "halaman utama", "feed", "search", "cari"
                ]):
                    continue
                companyname = txt
                break
            if companyname:
                break

    # 2. LinkedIn Company Page URL
    clean_linkedin_url = linkedin_company_url.rstrip("/")
    if clean_linkedin_url.endswith("/about"):
        clean_linkedin_url = clean_linkedin_url[:-6].rstrip("/")

    companywebsite = ""
    stocksymbol = ""
    industry = ""
    headquarters = ""
    country_hint = ""
    city = ""
    state = ""
    companycountry = ""
    zipcode = ""

    # 3. Website Extraction from safety/go redirect or 'Visit website' button
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "safety/go/?url=" in href or "linkedin.com/redir" in href:
            target_url = clean_redirect_url(href)
            if target_url and not any(ign in target_url for ign in ["linkedin.com", "licdn.com", "help/"]):
                companywebsite = target_url
                break

    # 4. Parsing Key-Value from Classic Layout (<dt>, <dd>)
    dt_elements = soup.find_all("dt")
    for dt in dt_elements:
        dt_title = clean_text(dt.text).lower()
        dd = dt.find_next_sibling("dd")
        if not dd:
            continue
        dd_text = clean_text(dd.text)

        if "website" in dt_title or "situs web" in dt_title:
            link = dd.find("a")
            web_val = link.get("href", "").strip() if link else dd_text
            if not companywebsite:
                companywebsite = clean_redirect_url(web_val)
        elif "stock" in dt_title or "saham" in dt_title:
            if not stocksymbol:
                stocksymbol = dd_text
        elif "industry" in dt_title or "industri" in dt_title:
            if not industry:
                industry = dd_text
        elif "headquarters" in dt_title or "kantor pusat" in dt_title or "lokasi utama" in dt_title:
            if not headquarters:
                headquarters = dd_text

    # 5. Parsing Key-Value from Modern SDUI Layout (<p>, <span>, <div>, <h3>, <h4>)
    for p in soup.find_all(["p", "span", "h3", "h4"]):
        label = clean_text(p.text).lower()
        if label in ["website", "situs web"] and not companywebsite:
            vt, vl = get_label_value(p)
            companywebsite = vl or vt
        elif label in ["industry", "industri"] and not industry:
            vt, _ = get_label_value(p)
            industry = vt
        elif label in ["headquarters", "kantor pusat"] and not headquarters:
            vt, _ = get_label_value(p)
            headquarters = vt
        elif label in ["stock symbol", "simbol saham", "saham"] and not stocksymbol:
            vt, _ = get_label_value(p)
            stocksymbol = vt

    # 6. Primary Location Extraction from Locations Section
    for badge in soup.find_all(["p", "span"]):
        badge_text = clean_text(badge.text).lower()
        if badge_text in ["primary", "headquarters", "utama"]:
            curr = badge
            for _ in range(5):
                if curr:
                    h3 = curr.find_previous_sibling("h3") or (curr.parent.find_previous_sibling("h3") if curr.parent else None)
                    if not h3 and curr.parent:
                        h3 = curr.parent.find("h3")
                    if h3:
                        country_hint = clean_text(h3.text)
                        break
                    curr = curr.parent

            badge_wrapper = badge.find_parent(["div"]) or badge
            next_p = badge_wrapper.find_next_sibling("p")
            if next_p and clean_text(next_p.text):
                headquarters = clean_text(next_p.text)
                break

    # 7. Split Headquarters into City, State, Country, Zipcode
    if headquarters or country_hint:
        city, state, companycountry, zipcode = parse_address_components(headquarters, country_hint=country_hint)

    # 8. Extract Email Domain from Website
    companyemaildomain = extract_email_domain(companywebsite)

    return {
        "companyname": companyname,
        "companywebsite": companywebsite,
        "companyemaildomain": companyemaildomain,
        "linkedincompanypageurl": clean_linkedin_url,
        "stocksymbol": stocksymbol,
        "industry": industry,
        "city": city,
        "state": state,
        "companycountry": companycountry,
        "zipcode": zipcode,
    }
