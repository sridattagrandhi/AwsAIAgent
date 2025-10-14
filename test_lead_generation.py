#!/usr/bin/env python3
"""
Local testing script for lead generation functionality
Run this to test your lead generation logic before deploying to AWS
"""

import sys
import os
sys.path.append('lambda_functions')

from search_shopify_retailers import find_shopify_stores, extract_store_info
import json

def test_lead_generation():
    """Test the lead generation process locally"""
    
    print("🔍 Testing Lead Generation System")
    print("=" * 50)
    
    # Test query
    query = "fitness equipment"
    limit = 5
    
    print(f"Query: {query}")
    print(f"Limit: {limit}")
    print()
    
    try:
        # Test the search function
        print("Searching for Shopify stores...")
        retailers = find_shopify_stores(query, limit)
        
        print(f"Found {len(retailers)} retailers:")
        print()
        
        for i, retailer in enumerate(retailers, 1):
            print(f"Retailer {i}:")
            print(f"  Company: {retailer.get('company_name', 'N/A')}")
            print(f"  Website: {retailer.get('website', 'N/A')}")
            print(f"  Email: {retailer.get('email', 'N/A')}")
            print(f"  Phone: {retailer.get('phone', 'N/A')}")
            print(f"  Description: {retailer.get('description', 'N/A')[:100]}...")
            print()
        
        # Save results to file for inspection
        with open('test_results.json', 'w') as f:
            json.dump(retailers, f, indent=2)
        
        print("✅ Test completed successfully!")
        print("Results saved to test_results.json")

        # Tests should not return values; assert the expected shape instead
        assert isinstance(retailers, list), "find_shopify_stores should return a list"
        # Optionally assert non-empty when the environment allows network calls
        # assert len(retailers) > 0, "Expected at least one retailer"

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        # Fail the test explicitly
        assert False, f"test_lead_generation raised an exception: {e}"

def test_single_store_extraction():
    """Test extracting info from a single known Shopify store"""
    
    print("\n🏪 Testing Single Store Extraction")
    print("=" * 50)
    
    # Test with a known Shopify store (replace with actual store URL)
    test_url = "https://shop.tesla.com"  # Tesla's shop runs on Shopify
    
    print(f"Testing URL: {test_url}")
    
    try:
        store_info = extract_store_info(test_url)
        
        if store_info:
            print("✅ Successfully extracted store information:")
            for key, value in store_info.items():
                print(f"  {key}: {value}")
        else:
            print("❌ Failed to extract store information")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("🚀 Lead Generation Testing Suite")
    print("=" * 50)
    
    # Run tests
    test_lead_generation()
    test_single_store_extraction()
    
    print("\n📝 Next Steps:")
    print("1. Review the test_results.json file")
    print("2. Adjust the search and extraction logic as needed")
    print("3. Test with different queries")
    print("4. Deploy to AWS Lambda when ready")