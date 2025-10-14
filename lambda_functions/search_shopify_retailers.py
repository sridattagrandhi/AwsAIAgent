# lambda_functions/search_shopify_retailers.py
import json, os, re, time, logging
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Fallback sample data file locations (put sample_prospects.json in repo root or this folder)
FALLBACK_PATHS = [
    "./sample_prospects.json",
    "./lambda_functions/sample_prospects.json",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

def _resp(code=200, body=None):
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body if body is not None else {"ok": True})
    }

def lambda_handler(event, context):
    """
    Lambda function to search for Shopify retailers and extract contact info.
    Body JSON:
      - query (str, required)
      - limit (int, optional, default 10)
    """
    try:
        body = event.get("body") or "{}"
        body = json.loads(body) if isinstance(body, str) else (body or {})

        query = (body.get("query") or "").strip()
        try:
            limit = int(body.get("limit") or 10)
        except Exception:
            limit = 10
        limit = max(1, min(limit, 50))  # cap to keep things polite

        if not query:
            return _resp(400, {"error": "Query parameter is required"})

        # Allow a DRY-RUN or offline fallback via env
        use_fallback = os.environ.get("SEARCH_DRY_RUN", "0").lower() in ("1", "true", "yes")

        retailers = []
        if not use_fallback:
            try:
                retailers = find_shopify_stores(query, limit)
            except Exception as e:
                logger.warning("find_shopify_stores failed: %s; falling back", str(e))
                retailers = []

        if not retailers:
            retailers = _load_fallback(limit)
            used_fallback = True
        else:
            used_fallback = False

        logger.info(json.dumps({
            "op": "search_shopify_retailers",
            "query": query,
            "count": len(retailers),
            "limit": limit,
            "fallback": used_fallback
        }))

        return _resp(200, {
            "retailers": retailers,
            "query": query,
            "count": len(retailers),
            "fallback": used_fallback
        })

    except Exception as e:
        logger.exception("Error in search_shopify_retailers")
        return _resp(500, {"error": "Internal server error", "detail": str(e)})

# ---------- Core search flow ----------

def find_shopify_stores(query: str, limit: int = 10) -> list[dict]:
    """
    Find Shopify stores and extract contact information.
    Currently uses a mocked "search_google" that returns Shopify-like domains.
    Replace 'search_google' with a proper API (e.g., Google CSE) when ready.
    """
    stores: list[dict] = []
    seen_domains: set[str] = set()
    seen_emails: set[str] = set()

    # Search phrase that tends to hit Shopify sites
    search_query = f'{query} site:myshopify.com OR "powered by shopify"'
    google_results = search_google(search_query, limit * 3)  # grab extra to filter

    for result in google_results:
        if len(stores) >= limit:
            break
        url = result.get("url")
        if not url:
            continue
        domain = urlparse(url).netloc.lower()
        if domain in seen_domains:
            continue

        try:
            store_data = extract_store_info(url)
            if not store_data:
                continue

            # Deduplicate by domain/email
            email = (store_data.get("email") or "").lower().strip()
            if email and email in seen_emails:
                continue

            stores.append(store_data)
            seen_domains.add(domain)
            if email:
                seen_emails.add(email)

            # polite pacing
            time.sleep(0.8)
        except Exception as e:
            logger.warning("extract_store_info failed for %s: %s", url, str(e))
            continue

    return stores

def search_google(query: str, num_results: int = 10) -> list[dict]:
    """
    Mocked Google search results (for hackathon/demo).
    In production, replace with Google Custom Search API or a compliant search API.
    """
    mock = [
        {"url": "https://example-store.myshopify.com", "title": f"Example Store - {query}"},
        {"url": "https://demo-shop.myshopify.com", "title": f"Demo Shop - {query}"},
        {"url": "https://test-retailer.myshopify.com", "title": f"Test Retailer - {query}"},
        {"url": "https://cool-sneaks.myshopify.com", "title": f"Cool Sneaks - {query}"},
        {"url": "https://westcoast-kicks.myshopify.com", "title": f"West Coast Kicks - {query}"},
    ]
    return mock[:num_results]

# ---------- Extraction helpers ----------

_SESSION = None
def _session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        s = requests.Session()
        s.headers.update({"User-Agent": USER_AGENT})
        _SESSION = s
    return _SESSION

def _get(url: str, timeout: float = 10.0) -> requests.Response | None:
    """GET with a short retry/backoff to be resilient during demo."""
    sess = _session()
    for i in range(2):  # small retry budget
        try:
            return sess.get(url, timeout=timeout)
        except Exception:
            time.sleep(0.5 * (i + 1))
    return None

def extract_store_info(url: str) -> dict | None:
    resp = _get(url)
    if not resp or resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.content, "html.parser")
    store = {
        "website": url,
        "companyName": extract_company_name(soup, url),
        "email": extract_email(soup, url),
        "phone": extract_phone(soup),
        "description": extract_description(soup),
        "industry": "E-commerce",
        "contactPage": find_contact_page(soup, url),
    }
    return store

def extract_company_name(soup: BeautifulSoup, url: str) -> str:
    title = soup.find("title")
    if title and title.get_text(strip=True):
        text = title.get_text(strip=True)
        # Shopify themes often use " - " in titles; pick the first chunk
        return text.split(" - ")[0][:80]
    domain = urlparse(url).netloc
    return domain.replace(".myshopify.com", "").replace("-", " ").title()[:80]

def extract_email(soup: BeautifulSoup, base_url: str) -> str | None:
    email_re = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    # Prefer contact/about pages
    contact_links = soup.find_all("a", href=re.compile(r"(contact|about)", re.I))
    for link in contact_links[:2]:
        href = link.get("href")
        if not href:
            continue
        contact_url = urljoin(base_url, href)
        r = _get(contact_url, timeout=7.0)
        if not r or r.status_code != 200:
            continue
        m = email_re.search(r.text)
        if m:
            return m.group(0)

    # Fallback: scan current page text
    m = email_re.search(soup.get_text(" ", strip=True))
    return m.group(0) if m else None

def extract_phone(soup: BeautifulSoup) -> str | None:
    # Simple North American pattern
    phone_re = re.compile(r"(\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})")
    m = phone_re.search(soup.get_text(" ", strip=True))
    return m.group(0) if m else None

def extract_description(soup: BeautifulSoup) -> str:
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta.get("content")[:200]
    p = soup.find("p")
    if p and p.get_text(strip=True):
        return (p.get_text(strip=True)[:200] + "...") if len(p.get_text(strip=True)) > 200 else p.get_text(strip=True)
    return "Shopify store"

def find_contact_page(soup: BeautifulSoup, base_url: str) -> str | None:
    link = soup.find("a", href=re.compile(r"contact", re.I))
    if link and link.get("href"):
        return urljoin(base_url, link.get("href"))
    return None

# ---------- Fallback ----------

def _load_fallback(limit: int) -> list[dict]:
    for p in FALLBACK_PATHS:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data[:limit]
            except Exception as e:
                logger.warning("Failed reading fallback %s: %s", p, str(e))
    # Minimal built-in fallback if file missing
    builtin = [
        {"companyName": "Acme Shoes", "website": "https://acmeshoes.example", "email": "owner@acmeshoes.example"},
        {"companyName": "Stride California", "website": "https://stride-ca.example", "email": "hello@stride-ca.example"},
        {"companyName": "Sole Society CA", "website": "https://solesociety.example", "email": "contact@solesociety.example"},
    ]
    return builtin[:limit]
