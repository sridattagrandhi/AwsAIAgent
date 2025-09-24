import json
import requests
from bs4 import BeautifulSoup
import re
import logging
import time
from urllib.parse import urljoin, urlparse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda function to search for Shopify retailers and extract contact info
    """
    try:
        body = json.loads(event.get('body', '{}'))
        query = body.get('query', '')
        limit = body.get('limit', 10)
        
        if not query:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Query parameter is required'})
            }
        
        # Search for Shopify stores
        retailers = find_shopify_stores(query, limit)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'retailers': retailers,
                'query': query,
                'count': len(retailers)
            })
        }
        
    except Exception as e:
        logger.error(f"Error in search_shopify_retailers: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }

def find_shopify_stores(query, limit=10):
    """
    Find Shopify stores using Google search and extract contact information
    """
    stores = []
    
    # Search Google for Shopify stores
    search_query = f'{query} site:myshopify.com OR "powered by shopify"'
    google_results = search_google(search_query, limit * 2)  # Get more results to filter
    
    for result in google_results[:limit]:
        try:
            store_data = extract_store_info(result['url'])
            if store_data:
                stores.append(store_data)
                time.sleep(1)  # Be respectful with requests
        except Exception as e:
            logger.warning(f"Failed to extract info from {result['url']}: {str(e)}")
            continue
    
    return stores

def search_google(query, num_results=10):
    """
    Search Google for Shopify stores (simplified version)
    In production, use Google Custom Search API
    """
    # For now, return mock data that looks realistic
    # You'll replace this with actual Google Custom Search API calls
    mock_results = [
        {'url': 'https://example-store.myshopify.com', 'title': f'Example Store - {query}'},
        {'url': 'https://demo-shop.myshopify.com', 'title': f'Demo Shop - {query} Products'},
        {'url': 'https://test-retailer.myshopify.com', 'title': f'Test Retailer - Premium {query}'},
    ]
    return mock_results[:num_results]

def extract_store_info(url):
    """
    Extract contact information and store details from a Shopify store
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract store information
        store_info = {
            'website': url,
            'company_name': extract_company_name(soup, url),
            'email': extract_email(soup, url),
            'phone': extract_phone(soup),
            'description': extract_description(soup),
            'industry': 'E-commerce',
            'contact_page': find_contact_page(soup, url)
        }
        
        return store_info
        
    except Exception as e:
        logger.error(f"Error extracting info from {url}: {str(e)}")
        return None

def extract_company_name(soup, url):
    """Extract company name from various sources"""
    # Try title tag first
    title = soup.find('title')
    if title:
        return title.get_text().strip().split(' - ')[0]
    
    # Fallback to domain name
    domain = urlparse(url).netloc
    return domain.replace('.myshopify.com', '').replace('-', ' ').title()

def extract_email(soup, base_url):
    """Extract email addresses from the page"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    # Check contact page first
    contact_links = soup.find_all('a', href=re.compile(r'contact|about', re.I))
    for link in contact_links[:2]:  # Check first 2 contact pages
        try:
            contact_url = urljoin(base_url, link.get('href'))
            contact_response = requests.get(contact_url, timeout=5)
            emails = re.findall(email_pattern, contact_response.text)
            if emails:
                return emails[0]  # Return first valid email
        except:
            continue
    
    # Search current page
    emails = re.findall(email_pattern, soup.get_text())
    return emails[0] if emails else None

def extract_phone(soup):
    """Extract phone numbers"""
    phone_pattern = r'(\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})'
    phones = re.findall(phone_pattern, soup.get_text())
    return phones[0] if phones else None

def extract_description(soup):
    """Extract store description"""
    # Try meta description first
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc:
        return meta_desc.get('content', '').strip()
    
    # Fallback to first paragraph
    first_p = soup.find('p')
    if first_p:
        return first_p.get_text().strip()[:200] + '...'
    
    return 'Shopify store'

def find_contact_page(soup, base_url):
    """Find contact page URL"""
    contact_link = soup.find('a', href=re.compile(r'contact', re.I))
    if contact_link:
        return urljoin(base_url, contact_link.get('href'))
    return None