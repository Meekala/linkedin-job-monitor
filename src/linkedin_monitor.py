"""
LinkedIn monitoring module

Coordinates MCP server communication, screenshot capture, and job extraction.
"""

import json
import time
import logging
import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import quote

from config import config, LinkedInURLBuilder
from database import JobDatabase, Job
from discord_notifier import DiscordNotifier

# Setup logging
logger = logging.getLogger(__name__)


class LinkedInJobMonitor:
    """Main LinkedIn job monitoring coordinator."""
    
    def __init__(self):
        """Initialize LinkedIn job monitor."""
        self.config = config
        self.database = JobDatabase(self.config.database_path)
        self.discord = DiscordNotifier()
        
        # State tracking
        self.last_search_times = {}
        self.is_running = False
        
        logger.info("LinkedIn Job Monitor initialized")
    
    def initialize(self) -> bool:
        """Initialize all components."""
        logger.info("Initializing LinkedIn Job Monitor components...")
        
        try:
            # Test Discord notification
            if not self.discord.test_notification():
                logger.warning("Discord notification test failed")
            
            logger.info("LinkedIn Job Monitor initialized successfully (HTTP mode)")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    def extract_jobs_http(self, city: str) -> Tuple[bool, List[Job]]:
        """
        Extract jobs directly via HTTP requests to LinkedIn's guest API.
        
        Args:
            city: City code (NYC, LA, SF, SD, Remote)
            
        Returns:
            Tuple of (success, list of new jobs found)
        """
        logger.info(f"Starting HTTP job extraction for {city}")
        
        try:
            # Build LinkedIn guest API URL
            location_ids = {
                'NYC': '90000070',   # New York City Area
                'LA': '90000049',    # Los Angeles Area  
                'SF': '90000084',    # San Francisco Bay Area
                'SD': '90010472',    # San Diego Area
                'REMOTE': '90000072' # Remote (using US as fallback)
            }
            
            location_id = location_ids.get(city.upper())
            if not location_id:
                logger.error(f"Unknown city: {city}. Available cities: {list(location_ids.keys())}")
                return False, []
            
            # LinkedIn jobs search URL - exact format as manual browsing (lowercase keywords, same parameter order)
            keywords_lowercase = self.config.job_title.lower()
            search_url = f"https://www.linkedin.com/jobs/search/?f_TPR=r1800&geoId={location_id}&keywords={quote(keywords_lowercase)}&origin=JOB_SEARCH_PAGE_LOCATION_AUTOCOMPLETE&start=0"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }
            
            logger.info(f"Fetching jobs from: {search_url}")
            response = requests.get(search_url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}"
                logger.error(error_msg)
                self.database.log_search(city, search_url, success=False, error_message=error_msg)
                return False, []
            
            logger.info(f"Got {len(response.text)} chars of HTML")
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find job cards
            job_cards = soup.find_all('div', class_='job-search-card')
            logger.info(f"Found {len(job_cards)} job cards")
            
            jobs = []
            for i, card in enumerate(job_cards):
                try:
                    # Extract job data
                    title_elem = card.find('h3', class_='base-search-card__title')
                    title = title_elem.get_text().strip() if title_elem else ''
                    
                    company_elem = card.find('h4', class_='base-search-card__subtitle')
                    company = company_elem.get_text().strip() if company_elem else ''
                    
                    location_elem = card.find('span', class_='job-search-card__location')
                    location = location_elem.get_text().strip() if location_elem else ''
                    
                    # Extract job URL
                    link_elem = card.find('a', class_='base-card__full-link')
                    job_url = link_elem.get('href') if link_elem else ''
                    
                    # Extract salary if available
                    salary_elem = card.find('span', class_='job-search-card__salary-info')
                    salary = salary_elem.get_text().strip() if salary_elem else ''
                    
                    # Extract job description/summary if available
                    desc_elem = card.find('p', class_='job-search-card__snippet') or card.find('div', class_='job-search-card__snippet')
                    description = desc_elem.get_text().strip() if desc_elem else ''
                    
                    # Extract posted time
                    time_elem = card.find('time')
                    posted_time = time_elem.get_text().strip() if time_elem else ''
                    
                    # Create job object if we have essential data
                    if title and company:
                        # Filter for relevant product management jobs only
                        if not self._is_relevant_product_job(title, description):
                            logger.debug(f"Skipping irrelevant job: {title} at {company}")
                            continue
                        
                        # Generate company career page URL
                        company_career_url = None
                        if company:
                            search_query = quote(f"{company} {title} careers")
                            company_career_url = f"https://www.google.com/search?q={search_query}"
                        
                        # Determine location type
                        location_type = 'On-site'
                        if 'remote' in location.lower():
                            location_type = 'Remote'
                        elif 'hybrid' in location.lower():
                            location_type = 'Hybrid'
                        
                        # Extract salary information from job page (if available)
                        pay_range_min = None
                        pay_range_max = None
                        final_salary_text = salary
                        
                        # Try to get salary from individual job page if job URL exists
                        if job_url and 'linkedin.com' in job_url:
                            page_salary, page_min, page_max = self._extract_salary_from_job_page(job_url)
                            if page_salary:
                                final_salary_text = page_salary
                                pay_range_min = page_min
                                pay_range_max = page_max
                        
                        # Fallback: Check description for salary info if not found elsewhere
                        if not final_salary_text and description:
                            desc_salary = self._extract_salary_from_description(description)
                            if desc_salary:
                                final_salary_text = desc_salary
                                # Extract numeric values from description salary
                                import re
                                numbers = re.findall(r'\$([\d,]+)', final_salary_text)
                                if len(numbers) >= 2:
                                    pay_range_min = int(numbers[0].replace(',', ''))
                                    pay_range_max = int(numbers[1].replace(',', ''))
                                elif len(numbers) == 1:
                                    pay_range_min = int(numbers[0].replace(',', ''))
                        
                        job = Job(
                            title=title,
                            company=company,
                            location=location,
                            location_type=location_type,
                            pay_range_text=final_salary_text if final_salary_text else None,
                            pay_range_min=pay_range_min,
                            pay_range_max=pay_range_max,
                            posted_time=posted_time,
                            linkedin_url=job_url,
                            company_career_url=company_career_url,
                            city=city
                        )
                        
                        # Filter jobs based on city search criteria
                        should_include = True
                        if city.upper() == 'REMOTE':
                            # Only include jobs that are actually remote
                            if location_type != 'Remote':
                                should_include = False
                                logger.debug(f"Skipping non-remote job in Remote search: {title} at {company} ({location_type})")
                        
                        if should_include:
                            jobs.append(job)
                            logger.info(f"Extracted job {i+1}: {title} at {company}")
                        else:
                            logger.debug(f"Filtered out job {i+1}: {title} at {company} - doesn't match {city} criteria")
                    
                except Exception as e:
                    logger.warning(f"Error parsing job {i+1}: {e}")
                    continue
            
            # Add jobs to database and identify new ones
            new_jobs = []
            for job in jobs:
                is_new_job = self.database.add_job(job)
                if is_new_job:
                    new_jobs.append(job)
                    logger.info(f"New job found: {job.title} at {job.company}")
                else:
                    logger.debug(f"Job already exists: {job.title} at {job.company}")
            
            # Log search results
            self.database.log_search(
                city=city,
                search_url=search_url,
                jobs_found=len(new_jobs),
                success=True
            )
            
            logger.info(f"HTTP extraction completed for {city}. Found {len(new_jobs)} new jobs out of {len(jobs)} processed")
            return True, new_jobs
            
        except Exception as e:
            logger.error(f"Error during HTTP extraction for {city}: {e}")
            self.database.log_search(city, search_url or "", success=False, error_message=str(e))
            return False, []
    
    def _extract_salary_from_job_page(self, job_url: str) -> Tuple[str, int, int]:
        """
        Extract salary information from individual LinkedIn job page.
        
        Args:
            job_url: LinkedIn job URL
            
        Returns:
            Tuple of (salary_text, min_salary, max_salary)
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
            
            logger.debug(f"Fetching salary data from job page: {job_url}")
            response = requests.get(job_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.debug(f"Failed to fetch job page: {response.status_code}")
                return "", None, None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for salary information in job page
            salary_elem = soup.find('span', class_='main-job-card__salary-info')
            if salary_elem:
                salary_text = salary_elem.get_text().strip()
                # Clean up whitespace and format
                salary_text = ' '.join(salary_text.split())
                
                # Extract numeric values
                import re
                numbers = re.findall(r'\$([0-9,]+)', salary_text)
                if len(numbers) >= 2:
                    min_salary = int(numbers[0].replace(',', ''))
                    max_salary = int(numbers[1].replace(',', ''))
                    return salary_text, min_salary, max_salary
                elif len(numbers) == 1:
                    min_salary = int(numbers[0].replace(',', ''))
                    return salary_text, min_salary, None
                else:
                    return salary_text, None, None
            
            return "", None, None
            
        except Exception as e:
            logger.debug(f"Error extracting salary from job page: {e}")
            return "", None, None
    
    def _extract_salary_from_description(self, description: str) -> str:
        """Extract salary information from job description text."""
        import re
        
        # Common salary patterns in job descriptions
        salary_patterns = [
            # $80,000 - $120,000
            r'\$[\d,]+\s*[-–—]\s*\$[\d,]+',
            # $80K - $120K
            r'\$[\d,]+k?\s*[-–—]\s*\$[\d,]+k?',
            # 80k - 120k
            r'[\d,]+k?\s*[-–—]\s*[\d,]+k?(?:\s*(?:per\s+year|annually|salary))?',
            # Salary: $80,000
            r'(?:salary|compensation|pay):\s*\$[\d,]+',
            # Up to $120,000
            r'up\s+to\s+\$[\d,]+',
            # Starting at $80,000
            r'starting\s+(?:at|from)\s+\$[\d,]+',
            # $25-35/hour or $25-35 per hour
            r'\$[\d,]+\s*[-–—]\s*\$?[\d,]+\s*(?:/|\s+per\s+)hour',
            # Hourly rate: $25
            r'(?:hourly\s+rate|per\s+hour):\s*\$[\d,]+',
        ]
        
        for pattern in salary_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            if matches:
                # Return the first match, cleaned up
                salary_text = matches[0].strip()
                # Add $ prefix if missing for number-only ranges like "80k - 120k"
                if not salary_text.startswith('$') and re.match(r'\d', salary_text):
                    salary_text = f"${salary_text}"
                return salary_text
        
        return ""
    
    def _is_relevant_product_job(self, title: str, description: str = "") -> bool:
        """
        Filter jobs to only include relevant product management positions.
        
        Args:
            title: Job title
            description: Job description (optional)
            
        Returns:
            True if job is relevant product management role
        """
        if not title:
            return False
        
        title_lower = title.lower()
        desc_lower = description.lower() if description else ""
        
        # Specific product management role keywords - must contain at least one
        product_keywords = [
            'product manager',
            'associate product manager',
            'sr. product manager',
            'senior product manager', 
            'principal product manager',
            'staff product manager',
            'product operations',
            'product ops',
            'apm',  # Associate Product Manager
            'spm',  # Senior Product Manager
        ]
        
        # Check if title contains specific product management keywords
        has_product_keyword = any(keyword in title_lower for keyword in product_keywords)
        
        if not has_product_keyword:
            return False
        
        # Exclusion keywords - skip jobs with these terms (non-product management)
        exclusion_keywords = [
            'clinical',
            'medical', 
            'healthcare',
            'hospital',
            'patient',
            'nursing',
            'therapy',
            'pharmaceutical',
            'education',
            'academic',
            'school',
            'teaching',
            'instructor',
            'curriculum',
            'construction',
            'real estate',
            'property management',
            'facility',
            'maintenance',
            'janitorial',
            'security guard',
            'warehouse',
            'logistics coordinator',
            'driver',
            'delivery',
            'food service',
            'restaurant',
            'retail',
            'sales associate',
            'customer service rep',
        ]
        
        # Check for exclusions in both title and description
        text_to_check = f"{title_lower} {desc_lower}"
        has_exclusion = any(keyword in text_to_check for keyword in exclusion_keywords)
        
        if has_exclusion:
            return False
        
        # Additional positive signals in description
        positive_signals = [
            'product strategy',
            'product roadmap', 
            'user experience',
            'product development',
            'market research',
            'product launch',
            'feature',
            'agile',
            'scrum',
            'stakeholder',
            'kpi',
            'metrics',
            'a/b test',
            'user story',
            'mvp',
            'saas',
            'software',
            'tech',
            'startup',
        ]
        
        # Bonus points for positive signals, but not required
        has_positive_signal = any(signal in desc_lower for signal in positive_signals)
        
        # Log the decision for debugging
        logger.debug(f"Job filtering - '{title}': product_keyword={has_product_keyword}, exclusion={has_exclusion}, positive_signal={has_positive_signal}")
        
        return True  # Passed all filters
    
    def find_and_notify_jobs(self) -> int:
        """
        Find all new jobs from past 30 minutes, sort by location, and send to correct webhooks.
        
        Returns:
            Total number of jobs found and sent
        """
        logger.info("=" * 60)
        logger.info("FINDING JOBS FROM PAST 30 MINUTES")
        logger.info("=" * 60)
        
        all_jobs_by_city = {}
        total_jobs_found = 0
        
        # Search each city for jobs posted in last 30 minutes
        for city in self.config.cities:
            logger.info(f"🔍 Searching {city} for jobs posted in last 30 minutes...")
            
            success, new_jobs = self.extract_jobs_http(city)
            if success and new_jobs:
                all_jobs_by_city[city] = new_jobs
                total_jobs_found += len(new_jobs)
                logger.info(f"✅ Found {len(new_jobs)} new jobs in {city}")
            else:
                logger.info(f"📭 No new jobs found in {city}")
            
            # Small delay between cities
            time.sleep(2)
        
        # Send notifications to city-specific webhooks
        if total_jobs_found > 0:
            logger.info(f"📨 Sending {total_jobs_found} jobs to Discord webhooks...")
            
            for city, jobs in all_jobs_by_city.items():
                if jobs:
                    logger.info(f"Sending {len(jobs)} jobs to {city} webhook")
                    
                    # Send jobs to city-specific webhook
                    if len(jobs) == 1:
                        success = self.discord.notify_new_job(jobs[0])
                    else:
                        success = self.discord.notify_multiple_jobs(jobs, city)
                    
                    if success:
                        # Mark jobs as notified
                        for job in jobs:
                            self.database.mark_job_notified(job.job_hash)
                        logger.info(f"✅ Sent {len(jobs)} jobs to {city} Discord channel")
                    else:
                        logger.warning(f"❌ Failed to send jobs to {city} Discord channel")
        else:
            logger.info("📭 No new jobs found in any city - nothing to send")
        
        logger.info(f"🎯 TOTAL: Found and sent {total_jobs_found} jobs")
        return total_jobs_found

    
    
    def get_stats(self) -> Dict:
        """Get monitoring statistics."""
        try:
            db_stats = self.database.get_stats()
            
            stats = {
                'database': db_stats,
                'last_search_times': {
                    city: time.isoformat() if isinstance(time, datetime) else str(time)
                    for city, time in self.last_search_times.items()
                },
                'is_running': self.is_running
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}
    
    def send_daily_summary(self):
        """Send daily summary to Discord."""
        logger.info("Sending daily summary")
        
        try:
            stats = self.database.get_stats()
            self.discord.notify_daily_summary(stats)
            
        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up LinkedIn Job Monitor")
        
        try:
            self.database.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()