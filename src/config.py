"""
Configuration module for LinkedIn Job Monitor

Handles environment variables, settings, and LinkedIn search URLs.
"""

import os
from dataclasses import dataclass
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class Config:
    """Configuration class containing all application settings."""
    
    # Discord settings
    discord_webhook_url: str  # Main webhook (for backwards compatibility)
    
    # City-specific Discord webhooks
    discord_webhook_urls: Dict[str, str]
    
    # Monitoring settings
    check_interval_minutes: int
    cities: List[str]
    job_title: str
    
    # Database
    database_path: str
    
    # Logging
    log_level: str
    log_file: str
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables."""
        return cls(
            # Discord
            discord_webhook_url=os.getenv('DISCORD_WEBHOOK_URL', ''),
            
            # City-specific Discord webhooks
            discord_webhook_urls={
                'Remote': os.getenv('DISCORD_WEBHOOK_URL_Remote', ''),
                'NYC': os.getenv('DISCORD_WEBHOOK_URL_NYC', ''),
                'SF': os.getenv('DISCORD_WEBHOOK_URL_SF', ''),
                'LA': os.getenv('DISCORD_WEBHOOK_URL_LA', ''),
                'SD': os.getenv('DISCORD_WEBHOOK_URL_SD', '')
            },
            
            # Monitoring
            check_interval_minutes=int(os.getenv('CHECK_INTERVAL_MINUTES', '30')),
            cities=os.getenv('CITIES', 'NYC,LA,SF,SD').split(','),
            job_title=os.getenv('JOB_TITLE', 'Associate Product Manager'),
            
            # Database
            database_path=os.getenv('DATABASE_PATH', 'data/jobs.db'),
            
            # Logging
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            log_file=os.getenv('LOG_FILE', 'data/linkedin_monitor.log')
        )
    
    def validate(self) -> bool:
        """Validate that required configuration is present."""
        # Check if at least one Discord webhook is configured
        if not self.discord_webhook_url and not any(self.discord_webhook_urls.values()):
            import logging
            logger = logging.getLogger(__name__)
            logger.error("No Discord webhook URLs configured")
            return False
        
        return True

class LinkedInURLBuilder:
    """Builder class for LinkedIn job search URLs."""
    
    # Base LinkedIn job search URL
    BASE_URL = "https://www.linkedin.com/jobs/search/"
    
    # City location IDs for LinkedIn (updated from actual LinkedIn URLs)
    CITY_LOCATIONS = {
        'NYC': '90000070',   # New York City Area
        'LA': '90000049',    # Los Angeles Area  
        'SF': '90000084',    # San Francisco Bay Area
        'SD': '90010472'     # San Diego Area
    }
    
    @classmethod
    def build_search_url(cls, job_title: str, city: str, posted_time: str = '1h') -> str:
        """
        Build a LinkedIn job search URL for the given parameters.
        
        Args:
            job_title: Job title to search for (e.g. "Associate Product Manager")
            city: City code (NYC, LA, SF, SD)
            posted_time: Posted time filter (1h, 24h, week, month)
        
        Returns:
            Complete LinkedIn search URL matching LinkedIn's actual format
        """
        location_id = cls.CITY_LOCATIONS.get(city.upper())
        if not location_id:
            raise ValueError(f"Unknown city: {city}. Supported: {list(cls.CITY_LOCATIONS.keys())}")
        
        # LinkedIn URL parameters (matching actual LinkedIn URLs)
        params = {
            'keywords': job_title.replace(' ', '%20'),
            'geoId': location_id,
            'f_TPR': cls._get_time_filter(posted_time),
            'origin': 'JOB_SEARCH_PAGE_JOB_FILTER',
            'refresh': 'true'
        }
        
        # Build query string
        query_string = '&'.join([f'{key}={value}' for key, value in params.items()])
        
        return f"{cls.BASE_URL}?{query_string}"
    
    @classmethod
    def _get_time_filter(cls, posted_time: str) -> str:
        """Get LinkedIn's time filter parameter."""
        time_filters = {
            '1h': 'r3600',      # Last hour
            '24h': 'r86400',    # Last 24 hours
            'week': 'r604800',  # Last week
            'month': 'r2592000' # Last month
        }
        return time_filters.get(posted_time, 'r3600')  # Default to 1 hour
    
    @classmethod
    def get_all_search_urls(cls, job_title: str, cities: List[str]) -> Dict[str, str]:
        """Get search URLs for all specified cities."""
        urls = {}
        for city in cities:
            try:
                urls[city] = cls.build_search_url(job_title, city)
            except ValueError as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Warning: {e}")
        return urls

def get_config() -> Config:
    """Get validated configuration instance."""
    config = Config.from_env()
    
    if not config.validate():
        raise ValueError("Configuration validation failed. Check your .env file.")
    
    return config

# Global configuration instance
config = get_config()