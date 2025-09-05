"""
Discord notification module for LinkedIn Job Monitor

Handles sending job alerts and status updates to Discord via webhooks.
"""

import json
import requests
from datetime import datetime
from typing import List, Dict, Optional
import logging
from pathlib import Path

from database import Job
from config import config

# Setup logging
logger = logging.getLogger(__name__)

class DiscordNotifier:
    """Handle Discord notifications for job alerts."""
    
    def __init__(self, webhook_url: str = None):
        """
        Initialize Discord notifier.
        
        Args:
            webhook_url: Discord webhook URL (uses config if not provided)
        """
        self.webhook_url = webhook_url or config.discord_webhook_url
        self.city_webhooks = config.discord_webhook_urls
        
        # Validate webhook URLs
        self._validate_webhook_urls()
        
        if not self.webhook_url and not any(self.city_webhooks.values()):
            raise ValueError("No Discord webhook URLs configured")
    
        # Color scheme for embeds
        self.colors = {
            'new_job': 0x00ff00,      # Green for new jobs
            'error': 0xff0000,        # Red for errors
            'info': 0x0099ff,         # Blue for info
            'warning': 0xffaa00       # Orange for warnings
        }
    
    def _validate_webhook_urls(self):
        """Validate that webhook URLs are properly formatted Discord webhooks."""
        import re
        discord_webhook_pattern = r'^https://discord\.com/api/webhooks/\d+/[\w\-]+$'
        
        # Validate main webhook
        if self.webhook_url and not re.match(discord_webhook_pattern, self.webhook_url):
            logger.warning("Main Discord webhook URL format appears invalid")
        
        # Validate city webhooks
        for city, url in self.city_webhooks.items():
            if url and not re.match(discord_webhook_pattern, url):
                logger.warning(f"Discord webhook URL for {city} appears invalid")
    
    def _sanitize_text(self, text: str, max_length: int = 1000) -> str:
        """Sanitize text for Discord embeds to prevent injection and limit length."""
        if not text:
            return ""
        
        # Remove or escape potential markdown injection
        sanitized = str(text).replace('`', '\\`').replace('*', '\\*').replace('_', '\\_')
        
        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length-3] + "..."
        
        return sanitized
    
    def _get_company_logo_url(self, company_name: str) -> str:
        """
        Get company logo URL using Clearbit Logo API.
        
        Args:
            company_name: Company name to get logo for
            
        Returns:
            Logo URL or fallback icon
        """
        if not company_name:
            return "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"  # Generic building icon
        
        try:
            # Clean company name for domain generation
            clean_name = company_name.lower()
            
            # Remove common business suffixes
            suffixes = [' inc.', ' inc', ' llc', ' ltd', ' corporation', ' corp', ' co.', ' company']
            for suffix in suffixes:
                clean_name = clean_name.replace(suffix, '')
            
            # Remove special characters and spaces
            clean_name = ''.join(char for char in clean_name if char.isalnum() or char == ' ')
            clean_name = clean_name.strip().replace(' ', '')
            
            # Generate domain (most common pattern)
            if clean_name:
                domain = f"{clean_name}.com"
                return f"https://logo.clearbit.com/{domain}"
            else:
                return "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
                
        except Exception as e:
            logger.debug(f"Error generating logo URL for {company_name}: {e}")
            return "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
    
    def get_webhook_for_city(self, city: str) -> str:
        """Get the appropriate webhook URL for a city."""
        # Validate city input
        valid_cities = {'NYC', 'LA', 'SF', 'SD', 'Remote'}
        if city not in valid_cities:
            logger.warning(f"Invalid city '{city}', using main webhook")
            return self.webhook_url
        
        # Try city-specific webhook first
        if city in self.city_webhooks and self.city_webhooks[city]:
            return self.city_webhooks[city]
        
        # Fall back to main webhook
        return self.webhook_url
    
    def _create_job_embed(self, job: Job) -> Dict:
        """
        Create enhanced Discord embed for a job posting with all available data.
        
        Args:
            job: Job object with enhanced fields
            
        Returns:
            Discord embed dictionary with comprehensive job information
        """
        # Determine embed color based on job characteristics
        embed_color = self.colors['new_job']
        if job.pay_range_min and job.pay_range_min >= 150000:
            embed_color = 0xFFD700  # Gold for high-paying jobs
        elif job.location_type == 'Remote':
            embed_color = 0x00FFFF  # Cyan for remote jobs
        
        # Sanitize job data
        safe_title = self._sanitize_text(job.title or 'Unknown Position', 200)
        safe_company = self._sanitize_text(job.company or 'Unknown Company', 100)
        
        # Get company logo
        company_logo_url = self._get_company_logo_url(safe_company)
        
        embed = {
            "title": f"{safe_title}",
            "description": f"**{safe_company}**",
            "color": embed_color,
            "timestamp": datetime.utcnow().isoformat(),
            "thumbnail": {
                "url": company_logo_url
            },
            "author": {
                "name": safe_company,
                "icon_url": company_logo_url
            },
            "fields": [],
            "footer": {
                "text": "LinkedIn Job Monitor • Apply quickly for best results!",
                "icon_url": "https://cdn-icons-png.flaticon.com/512/174/174857.png"
            }
        }
        
        # Add salary information with proper formatting
        if job.pay_range_text:
            # Clean up LinkedIn's original text formatting
            salary_text = self._sanitize_text(job.pay_range_text.strip(), 100)
            # Remove extra whitespace and normalize
            salary_text = ' '.join(salary_text.split())
        elif job.pay_range_min and job.pay_range_max:
            # Format as clean range with proper spacing
            salary_text = f"${job.pay_range_min:,} - ${job.pay_range_max:,}"
            if job.pay_type and job.pay_type != 'yearly':
                salary_text += f" {job.pay_type}"
        elif job.pay_range_min:
            # Only minimum available
            salary_text = f"${job.pay_range_min:,}+"
            if job.pay_type and job.pay_type != 'yearly':
                salary_text += f" {job.pay_type}"
        else:
            salary_text = "Not disclosed"
        
        embed["fields"].append({
            "name": "💰 Salary",
            "value": salary_text,
            "inline": True
        })
        
        # Add location with type (no emoji for On-site)
        location_text = ""
        if job.location_type:
            # Use emojis for location type (except On-site)
            if job.location_type == 'Remote':
                location_text = f"🏠 {job.location_type}"
            elif job.location_type == 'Hybrid':
                location_text = f"🏢🏠 {job.location_type}"
            elif job.location_type == 'On-site':
                location_text = job.location_type  # No emoji for On-site
            else:
                location_text = f"📍 {job.location_type}"
                
            if job.location and job.location_type not in job.location:
                safe_location = self._sanitize_text(job.location, 100)
                location_text += f" • {safe_location}"
        else:
            location_text = self._sanitize_text(job.location, 100) if job.location else "Not specified"
        
        embed["fields"].append({
            "name": "📍 Location",
            "value": location_text,
            "inline": True
        })
        
        # Add posted time
        posted_text = "Recently posted"
        if job.posted_time:
            posted_text = job.posted_time
            if job.posted_hours_ago is not None:
                if job.posted_hours_ago < 1:
                    posted_text += " ⚡ (Very Recent!)"
                elif job.posted_hours_ago <= 24:
                    posted_text += " 🔥 (Hot!)"
        
        embed["fields"].append({
            "name": "🕒 Posted",
            "value": posted_text,
            "inline": True
        })
        
        # Add prominent application link (webhooks don't support buttons)
        if job.linkedin_url and 'linkedin.com' in job.linkedin_url:
            embed["fields"].append({
                "name": "\u200b",  # Zero-width space for invisible field name
                "value": f"**[➤ APPLY ON LINKEDIN]({job.linkedin_url})**",
                "inline": False
            })
        
        # Add job ID for reference (small text)
        if job.linkedin_job_id:
            embed["fields"].append({
                "name": "🆔 Job ID",
                "value": f"`{job.linkedin_job_id}`",
                "inline": True
            })
        
        return embed
    
    def _send_webhook(self, payload: Dict, webhook_url: str = None) -> bool:
        """
        Send payload to Discord webhook.
        
        Args:
            payload: Discord webhook payload
            webhook_url: Specific webhook URL to use (defaults to main webhook)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = webhook_url or self.webhook_url
            response = requests.post(
                url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 204:
                logger.info("Discord notification sent successfully")
                return True
            else:
                logger.error(f"Discord webhook failed: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending Discord webhook: {e}")
            return False
    
    def notify_new_job(self, job: Job) -> bool:
        """
        Send notification for a new job.
        
        Args:
            job: Job object
            
        Returns:
            True if notification sent successfully
        """
        city = getattr(job, 'city', 'Unknown')
        logger.info(f"Sending Discord notification for new job in {city}: {job.title} at {job.company}")
        
        embed = self._create_job_embed(job)
        
        payload = {
            "content": f"🚨 **New Product Position Found in {city}!**",
            "embeds": [embed]
        }
        
        # Use city-specific webhook
        webhook_url = self.get_webhook_for_city(city)
        return self._send_webhook(payload, webhook_url)
    
    def notify_multiple_jobs(self, jobs: List[Job], city: str = None) -> bool:
        """
        Send notification for multiple new jobs to the correct city webhook.
        
        Args:
            jobs: List of Job objects
            city: City to send to (uses first job's city if not specified)
            
        Returns:
            True if notification sent successfully
        """
        if not jobs:
            return True
        
        # Determine city for webhook routing
        target_city = city or getattr(jobs[0], 'city', 'Unknown')
        logger.info(f"Sending Discord notification for {len(jobs)} new jobs in {target_city}")
        
        # Get city-specific webhook
        webhook_url = self.get_webhook_for_city(target_city)
        
        # Discord has a limit of 10 embeds per message
        max_embeds = 10
        job_batches = [jobs[i:i + max_embeds] for i in range(0, len(jobs), max_embeds)]
        
        success = True
        for i, batch in enumerate(job_batches):
            embeds = [self._create_job_embed(job) for job in batch]
            
            content = f"🚨 **{len(batch)} New Product Position{'s' if len(batch) > 1 else ''} Found in {target_city}!**"
            if len(job_batches) > 1:
                content += f" (Batch {i + 1}/{len(job_batches)})"
            
            payload = {
                "content": content,
                "embeds": embeds
            }
            
            # Send to city-specific webhook
            batch_success = self._send_webhook(payload, webhook_url)
            success = success and batch_success
            
            # Rate limiting: Discord allows 30 requests per minute
            if i < len(job_batches) - 1:
                import time
                time.sleep(2)  # Wait 2 seconds between batches
        
        return success
    
    def notify_status(self, title: str, message: str, status_type: str = 'info') -> bool:
        """
        Send a status notification.
        
        Args:
            title: Notification title
            message: Notification message
            status_type: Type of status ('info', 'warning', 'error')
            
        Returns:
            True if notification sent successfully
        """
        logger.info(f"Sending Discord status notification: {title}")
        
        color = self.colors.get(status_type, self.colors['info'])
        
        # Choose appropriate emoji
        emoji_map = {
            'info': '💻',
            'warning': '⚠️',
            'error': '❌'
        }
        emoji = emoji_map.get(status_type, '💻')
        
        embed = {
            "title": f"{emoji} {title}",
            "description": message,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "LinkedIn Job Monitor",
                "icon_url": "https://cdn-icons-png.flaticon.com/512/174/174857.png"
            }
        }
        
        payload = {
            "embeds": [embed]
        }
        
        return self._send_webhook(payload)
    
    def notify_daily_summary(self, stats: Dict) -> bool:
        """
        Send enhanced daily summary notification with detailed statistics.
        
        Args:
            stats: Statistics dictionary from database and job processor
            
        Returns:
            True if notification sent successfully
        """
        logger.info("Sending Discord daily summary")
        
        # Basic stats
        jobs_today = stats.get('jobs_today', 0)
        total_jobs = stats.get('total_jobs', 0)
        searches_today = stats.get('successful_searches_today', 0)
        unnotified = stats.get('unnotified_jobs', 0)
        
        # Enhanced stats if available
        jobs_with_salary = stats.get('jobs_with_salary', 0)
        remote_jobs = stats.get('remote_jobs', 0)
        hybrid_jobs = stats.get('hybrid_jobs', 0)
        onsite_jobs = stats.get('onsite_jobs', 0)
        avg_salary_min = stats.get('avg_salary_min')
        avg_salary_max = stats.get('avg_salary_max')
        
        embed = {
            "title": "📊 Daily Job Search Summary",
            "color": self.colors['info'],
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "🆕 New Jobs Today",
                    "value": f"**{jobs_today}** new positions",
                    "inline": True
                },
                {
                    "name": "📊 Total in Database",
                    "value": f"**{total_jobs}** jobs tracked",
                    "inline": True
                },
                {
                    "name": "🔍 Searches Today",
                    "value": f"**{searches_today}** searches",
                    "inline": True
                }
            ],
            "footer": {
                "text": "LinkedIn Job Monitor - Daily Summary",
                "icon_url": "https://cdn-icons-png.flaticon.com/512/174/174857.png"
            }
        }
        
        # Add salary information if available
        if jobs_with_salary > 0:
            salary_text = f"**{jobs_with_salary}** jobs with disclosed salary"
            if avg_salary_min and avg_salary_max:
                salary_text += f"\n💰 Avg Range: ${avg_salary_min:,.0f} - ${avg_salary_max:,.0f}"
            
            embed["fields"].append({
                "name": "💰 Salary Data",
                "value": salary_text,
                "inline": False
            })
        
        # Add location type breakdown
        if remote_jobs + hybrid_jobs + onsite_jobs > 0:
            location_breakdown = []
            if remote_jobs > 0:
                location_breakdown.append(f"🏠 **{remote_jobs}** Remote")
            if hybrid_jobs > 0:
                location_breakdown.append(f"🏢🏠 **{hybrid_jobs}** Hybrid")
            if onsite_jobs > 0:
                location_breakdown.append(f"🏢 **{onsite_jobs}** On-site")
            
            embed["fields"].append({
                "name": "📍 Location Types",
                "value": " • ".join(location_breakdown),
                "inline": False
            })
        
        # Add notification status
        if unnotified > 0:
            embed["fields"].append({
                "name": "🔔 Pending Notifications",
                "value": f"**{unnotified}** jobs awaiting notification",
                "inline": True
            })
        
        # Add performance tip
        if jobs_today > 0:
            embed["description"] = "🎯 **Great day for job hunting!** Apply quickly for the best results."
        elif searches_today > 0:
            embed["description"] = "🔍 **Monitoring active** - No new matches today, but we're watching!"
        else:
            embed["description"] = "💤 **Quiet day** - System may need attention or LinkedIn changes detected."
        
        payload = {
            "content": "📅 **Daily Summary Report**",
            "embeds": [embed]
        }
        
        return self._send_webhook(payload)
    
    def notify_search_started(self, cities: List[str]) -> bool:
        """
        Notify that job search monitoring has started.
        
        Args:
            cities: List of cities being monitored
            
        Returns:
            True if notification sent successfully
        """
        cities_str = ", ".join(cities)
        message = f"Started monitoring LinkedIn for Product positions in: **{cities_str}**"
        
        return self.notify_status(
            "Job Monitor Started",
            message,
            'info'
        )
    
    def notify_search_error(self, error_message: str, city: str = None) -> bool:
        """
        Notify about search errors.
        
        Args:
            error_message: Error description
            city: City where error occurred (optional)
            
        Returns:
            True if notification sent successfully
        """
        title = "Search Error"
        if city:
            title += f" - {city}"
        
        message = f"An error occurred during job search:\n```{error_message}```"
        
        return self.notify_status(title, message, 'error')
    
    def test_notification(self) -> bool:
        """
        Send a test notification to verify Discord integration.
        
        Returns:
            True if test successful
        """
        return self.notify_status(
            "Test Notification",
            "LinkedIn Job Monitor Discord integration is working correctly! 🎉",
            'info'
        )

class DiscordCommandHandler:
    """Handle Discord bot commands (if using a full bot instead of webhooks)."""
    
    def __init__(self, token: str = None):
        """Initialize Discord bot command handler."""
        self.token = token
        # Note: This would require discord.py and a full bot implementation
        # For now, we'll focus on webhooks which are simpler
        pass
    
    # Future implementation for Discord bot commands like:
    # !status - Get current monitoring status
    # !pause - Pause monitoring
    # !resume - Resume monitoring
    # !stats - Get statistics
    # !test - Send test notification