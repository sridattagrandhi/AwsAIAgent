"""
Advanced Lead Generation Module
Handles finding and validating Shopify store leads
"""

import requests
import json
import re
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LeadGenerator:
    def __init__(self, google_api_key: Optional[str] = None, google_cse_id: Optional[str] = None):
        self.google_api_key = google_api_key
        self.google_cse_id = google_cse_id
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def find_shopify_leads(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Find Shopify store leads based on search query
        """
        logger.info(f"Searching for Shopify stores: {query}")
        
        # Search for potential stores
        store_urls = self._search_shopify_stores(query, limit * 2)
        
        leads = []
        for url in store_urls[:limit]:
            try:
                lead_data = self._extract_lead_info(url)
                if lead_data and self._validate_lead(lead_data):
                    leads.append(lead_data)
                    logger.info(f"Found valid lead: {lead_data['company_name']}")
                
                # Be respectful with requests
                time.sleep(1)
                
            except Exception as e:
                logger.warning(f"Failed to process {url}: {str(e)}")
                continue
        
        logger.info(f"Generated {len(leads)} qualified leads")
        return leads
    
    def _search_shopify_stores(self, query: str, limit: int) -> List[str]:
        """
        Search for Shopify stores using Google Custom Search API or fallback methods
        """
        if self.google_api_key and self.google_cse_id:
            return self._google_custom_search(query, limit)
        else:
            return self._fallback_search(query, limit)
    
    def _google_custom_search(self, query: str, limit: int) -> List[str]:
        """
        Use Google Custom Search API to find Shopify stores
        """
        search_query = f'{query} site:myshopify.com OR "powered by shopify"'
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': self.google_api_key,
            'cx': self.google_cse_id,
            'q': search_query,
            'num': min(limit, 10)  # Google CSE max is 10 per request
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            results = response.json()
            urls = [item['link'] for item in results.get('items', [])]
            
            return urls
            
        except Exception as e:
            logger.error(f"Google Custom Search failed: {str(e)}")
            return self._fallback_search(query, limit)
    
    def _fallback_search(self, query: str, limit: int) -> List[str]:
        """
        Fallback search method using known Shopify store patterns
        """
        # For testing, return some known Shopify stores
        # In production, you might use other APIs or scraping methods
        known_stores = [
            "https://shop.tesla.com",
            "https://www.allbirds.com",
            "https://www.gymshark.com",
            "https://shop.kylie.com",
            "https://www.colourpop.com"
        ]
        
        # Filter based on query relevance (simple keyword matching)
        relevant_stores = []
        for store in known_stores:
            if any(keyword.lower() in store.lower() for keyword in query.split()):
                relevant_stores.append(store)
        
        return relevant_stores[:limit] if relevant_stores else known_stores[:limit]
    
    def _extract_lead_info(self, url: str) -> Optional[Dict]:
        """
        Extract comprehensive lead information from a Shopify store
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check if it's actually a Shopify store
            if not self._is_shopify_store(soup, response.text):
                logger.warning(f"{url} doesn't appear to be a Shopify store")
                return None
            
            lead_info = {
                'website': url,
                'company_name': self._extract_company_name(soup, url),
                'email': self._extract_email(soup, url),
                'phone': self._extract_phone(soup),
                'description': self._extract_description(soup),
                'industry': self._extract_industry(soup),
                'social_media': self._extract_social_links(soup),
                'contact_page': self._find_contact_page(soup, url),
                'about_page': self._find_about_page(soup, url),
                'products': self._extract_product_categories(soup),
                'location': self._extract_location(soup)
            }
            
            return lead_info
            
        except Exception as e:
            logger.error(f"Error extracting info from {url}: {str(e)}")
            return None
    
    def _is_shopify_store(self, soup: BeautifulSoup, page_text: str) -> bool:
        """
        Verify if the site is actually a Shopify store
        """
        shopify_indicators = [
            'shopify',
            'myshopify.com',
            'cdn.shopify.com',
            'Shopify.theme',
            'shopify-section'
        ]
        
        return any(indicator in page_text.lower() for indicator in shopify_indicators)
    
    def _extract_company_name(self, soup: BeautifulSoup, url: str) -> str:
        """Extract company name with multiple fallback methods"""
        # Try title tag
        title = soup.find('title')
        if title:
            name = title.get_text().strip()
            # Clean up common title patterns
            name = re.sub(r'\s*[-–|]\s*(Shop|Store|Online|Home).*$', '', name, flags=re.IGNORECASE)
            if name:
                return name
        
        # Try h1 tag
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
        
        # Fallback to domain
        domain = urlparse(url).netloc
        return domain.replace('.myshopify.com', '').replace('.com', '').replace('-', ' ').title()
    
    def _extract_email(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract email with improved accuracy"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        # Priority order: contact page, about page, current page
        pages_to_check = [
            self._find_contact_page(soup, base_url),
            self._find_about_page(soup, base_url),
            base_url
        ]
        
        for page_url in pages_to_check:
            if not page_url:
                continue
                
            try:
                if page_url == base_url:
                    page_text = soup.get_text()
                else:
                    response = self.session.get(page_url, timeout=5)
                    page_text = response.text
                
                emails = re.findall(email_pattern, page_text)
                # Filter out common false positives
                valid_emails = [email for email in emails 
                              if not any(skip in email.lower() 
                                       for skip in ['example.com', 'test.com', 'noreply'])]
                
                if valid_emails:
                    return valid_emails[0]
                    
            except Exception as e:
                logger.debug(f"Failed to check {page_url} for email: {str(e)}")
                continue
        
        return None
    
    def _extract_phone(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract phone number with better pattern matching"""
        phone_patterns = [
            r'\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            r'\+?([0-9]{1,3})[-.\s]?([0-9]{3,4})[-.\s]?([0-9]{3,4})[-.\s]?([0-9]{3,4})'
        ]
        
        text = soup.get_text()
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return ''.join(matches[0])
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract store description with multiple sources"""
        # Try meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc.get('content').strip()
        
        # Try Open Graph description
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc and og_desc.get('content'):
            return og_desc.get('content').strip()
        
        # Try first meaningful paragraph
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 50:  # Meaningful content
                return text[:300] + '...' if len(text) > 300 else text
        
        return 'E-commerce store'
    
    def _extract_industry(self, soup: BeautifulSoup) -> str:
        """Determine industry based on content analysis"""
        text = soup.get_text().lower()
        
        industry_keywords = {
            'fashion': ['clothing', 'fashion', 'apparel', 'dress', 'shirt', 'pants'],
            'beauty': ['beauty', 'cosmetics', 'skincare', 'makeup', 'fragrance'],
            'fitness': ['fitness', 'gym', 'workout', 'exercise', 'sports'],
            'electronics': ['electronics', 'gadgets', 'tech', 'computer', 'phone'],
            'home': ['home', 'furniture', 'decor', 'kitchen', 'bedroom'],
            'food': ['food', 'snacks', 'organic', 'nutrition', 'supplements']
        }
        
        for industry, keywords in industry_keywords.items():
            if any(keyword in text for keyword in keywords):
                return industry.title()
        
        return 'E-commerce'
    
    def _extract_social_links(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract social media links"""
        social_links = {}
        social_patterns = {
            'facebook': r'facebook\.com/[^/\s]+',
            'instagram': r'instagram\.com/[^/\s]+',
            'twitter': r'twitter\.com/[^/\s]+',
            'linkedin': r'linkedin\.com/company/[^/\s]+'
        }
        
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            for platform, pattern in social_patterns.items():
                if re.search(pattern, href, re.IGNORECASE):
                    social_links[platform] = href
                    break
        
        return social_links
    
    def _find_contact_page(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Find contact page URL"""
        contact_link = soup.find('a', href=re.compile(r'contact', re.I))
        if contact_link:
            return urljoin(base_url, contact_link.get('href'))
        return None
    
    def _find_about_page(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Find about page URL"""
        about_link = soup.find('a', href=re.compile(r'about', re.I))
        if about_link:
            return urljoin(base_url, about_link.get('href'))
        return None
    
    def _extract_product_categories(self, soup: BeautifulSoup) -> List[str]:
        """Extract product categories"""
        categories = []
        
        # Look for navigation menus
        nav_elements = soup.find_all(['nav', 'ul'], class_=re.compile(r'nav|menu', re.I))
        for nav in nav_elements:
            links = nav.find_all('a')
            for link in links:
                text = link.get_text().strip()
                if text and len(text) < 30:  # Reasonable category name length
                    categories.append(text)
        
        return categories[:10]  # Limit to top 10 categories
    
    def _extract_location(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract business location"""
        # Look for address patterns
        address_pattern = r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl)\b'
        
        text = soup.get_text()
        addresses = re.findall(address_pattern, text, re.IGNORECASE)
        
        if addresses:
            return addresses[0]
        
        # Look for city, state patterns
        location_pattern = r'\b[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5}\b'
        locations = re.findall(location_pattern, text)
        
        return locations[0] if locations else None
    
    def _validate_lead(self, lead_data: Dict) -> bool:
        """
        Validate that the lead has minimum required information
        """
        required_fields = ['company_name', 'website']
        has_contact = lead_data.get('email') or lead_data.get('phone')
        
        return (all(lead_data.get(field) for field in required_fields) and 
                has_contact and 
                len(lead_data.get('company_name', '')) > 2)
    
    def export_leads(self, leads: List[Dict], filename: str = 'leads.json'):
        """Export leads to JSON file"""
        with open(filename, 'w') as f:
            json.dump(leads, f, indent=2)
        
        logger.info(f"Exported {len(leads)} leads to {filename}")