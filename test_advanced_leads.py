#!/usr/bin/env python3
"""
Test the advanced lead generation system
"""

import sys
import os
sys.path.append('src')

from lead_generator import LeadGenerator
import json

def main():
    print("🚀 Advanced Lead Generation Test")
    print("=" * 50)
    
    # Initialize lead generator
    # Add your Google API credentials here if you have them
    generator = LeadGenerator(
        google_api_key=None,  # Add your Google API key
        google_cse_id=None    # Add your Custom Search Engine ID
    )
    
    # Test queries
    test_queries = [
        "fitness equipment",
        "organic skincare",
        "sustainable fashion",
        "home decor"
    ]
    
    all_leads = []
    
    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")
        print("-" * 30)
        
        try:
            leads = generator.find_shopify_leads(query, limit=3)
            
            print(f"Found {len(leads)} leads for '{query}':")
            
            for i, lead in enumerate(leads, 1):
                print(f"\n  Lead {i}:")
                print(f"    Company: {lead.get('company_name', 'N/A')}")
                print(f"    Website: {lead.get('website', 'N/A')}")
                print(f"    Email: {lead.get('email', 'Not found')}")
                print(f"    Phone: {lead.get('phone', 'Not found')}")
                print(f"    Industry: {lead.get('industry', 'N/A')}")
                print(f"    Description: {lead.get('description', 'N/A')[:100]}...")
                
                if lead.get('social_media'):
                    print(f"    Social: {', '.join(lead['social_media'].keys())}")
            
            all_leads.extend(leads)
            
        except Exception as e:
            print(f"❌ Error testing '{query}': {str(e)}")
    
    # Export all leads
    if all_leads:
        generator.export_leads(all_leads, 'advanced_test_leads.json')
        print(f"\n✅ Test completed! Generated {len(all_leads)} total leads")
        print("Results saved to 'advanced_test_leads.json'")
        
        # Show summary stats
        print(f"\n📊 Lead Quality Summary:")
        print(f"  Leads with email: {sum(1 for lead in all_leads if lead.get('email'))}")
        print(f"  Leads with phone: {sum(1 for lead in all_leads if lead.get('phone'))}")
        print(f"  Leads with social media: {sum(1 for lead in all_leads if lead.get('social_media'))}")
        
    else:
        print("\n❌ No leads generated")
    
    print(f"\n📝 Next Steps:")
    print("1. Review the generated leads in 'advanced_test_leads.json'")
    print("2. Get Google Custom Search API credentials for better results")
    print("3. Adjust search queries and validation criteria")
    print("4. Test with real Shopify stores")

if __name__ == "__main__":
    main()