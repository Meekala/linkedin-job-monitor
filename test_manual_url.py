#!/usr/bin/env python3
"""
Test the exact manual LinkedIn URL format you provided
"""
import requests
from bs4 import BeautifulSoup

def test_exact_manual_format():
    """Test your exact manual LinkedIn URL format"""
    
    # Your exact manual URL format (without the specific currentJobId)
    manual_url = "https://www.linkedin.com/jobs/search/?f_TPR=r1800&geoId=90000070&keywords=associate%20product%20manager&origin=JOB_SEARCH_PAGE_LOCATION_AUTOCOMPLETE"
    
    # Compare to current scraper guest API
    guest_api_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=Associate%20Product%20Manager&geoId=90000070&f_TPR=r1800&start=0"
    
    print("🔍 COMPARING URL FORMATS")
    print("=" * 80)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    urls_to_test = [
        ("Manual format (your URL)", manual_url),
        ("Original guest API", guest_api_url)
    ]
    
    for name, url in urls_to_test:
        print(f"\n=== {name} ===")
        print(f"URL: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ HTTP {response.status_code}")
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            job_cards = soup.find_all('div', class_='job-search-card')
            
            print(f"📊 Found {len(job_cards)} jobs")
            
            # Show first 5 jobs
            for i, card in enumerate(job_cards[:5]):
                try:
                    title_elem = card.find('h3', class_='base-search-card__title')
                    title = title_elem.get_text().strip() if title_elem else 'No title'
                    
                    company_elem = card.find('h4', class_='base-search-card__subtitle')  
                    company = company_elem.get_text().strip() if company_elem else 'No company'
                    
                    time_elem = card.find('time')
                    posted_time = time_elem.get_text().strip() if time_elem else 'No time'
                    
                    # Check if this looks like a product management role
                    is_relevant = any(keyword in title.lower() for keyword in [
                        'product manager', 'product management', 'associate product', 
                        'product marketing', 'pm ', 'apm'
                    ])
                    
                    relevance = "✅ RELEVANT" if is_relevant else "❌ IRRELEVANT"
                    
                    print(f"  {i+1}. {title} at {company} ({posted_time}) - {relevance}")
                    
                except Exception as e:
                    print(f"  {i+1}. Error parsing job: {e}")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 80)
    print("💡 RECOMMENDATION:")
    print("The format that returns more relevant product management jobs should be used")

if __name__ == "__main__":
    test_exact_manual_format()