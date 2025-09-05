#!/usr/bin/env python3
"""
Test script to compare different LinkedIn search parameters
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

def test_linkedin_search(job_title, location_id, time_filter=None, city_name=""):
    """Test LinkedIn search with different parameters"""
    
    base_url = "https://www.linkedin.com/jobs/search/"
    params = [
        f"keywords={quote(job_title)}",
        f"geoId={location_id}",
        "start=0"
    ]
    
    if time_filter:
        params.append(f"f_TPR={time_filter}")
    params.append("origin=JOB_SEARCH_PAGE_LOCATION_AUTOCOMPLETE")
    
    search_url = f"{base_url}?" + "&".join(params)
    
    print(f"\n=== {city_name} - {time_filter or 'No time filter'} ===")
    print(f"URL: {search_url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        job_cards = soup.find_all('div', class_='job-search-card')
        
        print(f"📊 Found {len(job_cards)} jobs")
        
        # Show first 3 jobs as examples
        for i, card in enumerate(job_cards[:3]):
            try:
                title_elem = card.find('h3', class_='base-search-card__title')
                title = title_elem.get_text().strip() if title_elem else 'No title'
                
                company_elem = card.find('h4', class_='base-search-card__subtitle')  
                company = company_elem.get_text().strip() if company_elem else 'No company'
                
                time_elem = card.find('time')
                posted_time = time_elem.get_text().strip() if time_elem else 'No time'
                
                print(f"  {i+1}. {title} at {company} ({posted_time})")
                
            except Exception as e:
                print(f"  {i+1}. Error parsing job: {e}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    job_title = "Associate Product Manager"
    
    # Test NYC with different time filters
    nyc_location_id = "90000070"
    
    print("🔍 COMPARING LINKEDIN SEARCH RESULTS")
    print("=" * 60)
    
    # Current scraper setting (last 30 minutes)
    test_linkedin_search(job_title, nyc_location_id, "r1800", "NYC (30 minutes)")
    
    # Last hour  
    test_linkedin_search(job_title, nyc_location_id, "r3600", "NYC (1 hour)")
    
    # Last 24 hours
    test_linkedin_search(job_title, nyc_location_id, "r86400", "NYC (24 hours)")
    
    # No time filter (all jobs)
    test_linkedin_search(job_title, nyc_location_id, None, "NYC (All time)")
    
    print("\n" + "=" * 60)
    print("💡 EXPLANATION:")
    print("- The scraper currently looks for jobs posted in the last 30 minutes")
    print("- Manual browsing shows all jobs or jobs from last 24 hours by default")
    print("- This explains why you see different results")
    print("- Very few jobs are posted every 30 minutes, so results are sparse")

if __name__ == "__main__":
    main()