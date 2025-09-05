#!/usr/bin/env python3
"""
Continuous LinkedIn Job Monitor
Runs every 30 minutes to check for new Associate Product Manager positions
"""

import sys
import time
import logging
import signal
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Add src directory to path
sys.path.insert(0, 'src')

from linkedin_monitor import LinkedInJobMonitor
from config import config

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ContinuousJobMonitor:
    """Continuous job monitoring with APScheduler."""
    
    def __init__(self):
        """Initialize continuous monitor."""
        self.monitor = LinkedInJobMonitor()
        self.scheduler = BlockingScheduler()
        self.is_running = False
        self.last_run = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("Continuous Job Monitor initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
    
    def job_check_task(self):
        """Task that runs every 30 minutes to find and send new jobs."""
        logger.info("🚨 STARTING 30-MINUTE JOB SEARCH")
        
        start_time = datetime.now()
        
        try:
            # Find jobs from past 30 minutes and send to correct webhooks
            total_jobs_sent = self.monitor.find_and_notify_jobs()
            
            self.last_run = start_time
            duration = (datetime.now() - start_time).total_seconds()
            
            if total_jobs_sent > 0:
                logger.info(f"✅ SUCCESS: Found and sent {total_jobs_sent} jobs in {duration:.1f}s")
            else:
                logger.info(f"📭 No new jobs found in {duration:.1f}s")
            
            # Send daily summary at 9 AM
            if self._should_send_daily_summary():
                logger.info("Sending daily summary")
                self.monitor.send_daily_summary()
            
            # Clean up old database entries (run once per day at 2 AM)
            if self._should_cleanup_database():
                logger.info("Running database cleanup...")
                deleted_count = self.monitor.database.cleanup_old_jobs()  # Uses default 3 days
                if deleted_count > 0:
                    logger.info(f"Database cleanup completed - removed {deleted_count} old jobs")
            
        except Exception as e:
            logger.error(f"❌ ERROR during job search: {e}")
            try:
                self.monitor.discord.notify_search_error(str(e))
            except:
                logger.error("Failed to send error notification to Discord")
        
        logger.info("🏁 30-MINUTE JOB SEARCH COMPLETED")
    
    def _should_send_daily_summary(self) -> bool:
        """Check if we should send daily summary (once per day at 9 AM)."""
        now = datetime.now()
        
        # Send summary at 9 AM
        if now.hour == 9 and now.minute < 30:  # Within 30 minutes of 9 AM
            return True
        
        return False
    
    def _should_cleanup_database(self) -> bool:
        """Check if we should clean up database (once per day at 2 AM)."""
        now = datetime.now()
        
        # Clean up at 2 AM (when usage is low)
        if now.hour == 2 and now.minute < 30:  # Within 30 minutes of 2 AM
            return True
        
        return False
    
    def start(self):
        """Start continuous monitoring."""
        logger.info("Starting continuous LinkedIn job monitoring...")
        
        try:
            # Initialize the monitor
            if not self.monitor.initialize():
                logger.error("Failed to initialize job monitor")
                return False
            
            # Send startup notification
            cities_str = ", ".join(config.cities)
            self.monitor.discord.notify_search_started(config.cities)
            logger.info(f"Monitoring started for cities: {cities_str}")
            
            # Determine next 4pm run time
            now = datetime.now()
            next_4pm = now.replace(hour=16, minute=0, second=0, microsecond=0)
            
            # If it's already past 4pm today, schedule for 4pm tomorrow
            if now.hour >= 16:
                next_4pm = next_4pm + timedelta(days=1)
            
            logger.info(f"Next job search scheduled for: {next_4pm.strftime('%Y-%m-%d at 4:00 PM')}")
            
            # Schedule job checks every 30 minutes starting at 4:00pm
            # This will run at 4:00, 4:30, 5:00, 5:30, etc.
            self.scheduler.add_job(
                func=self.job_check_task,
                trigger=IntervalTrigger(minutes=30),
                start_date=next_4pm,
                id='job_check',
                name='LinkedIn Job Check (every 30 min from 4pm)',
                replace_existing=True
            )
            
            # Schedule daily summary at 9 AM
            self.scheduler.add_job(
                func=self.monitor.send_daily_summary,
                trigger='cron',
                hour=9,
                minute=0,
                id='daily_summary',
                name='Daily Summary',
                replace_existing=True
            )
            
            logger.info(f"Scheduled job checks every 30 minutes starting at 4:00 PM")
            logger.info("Press Ctrl+C to stop monitoring")
            
            self.is_running = True
            
            # Start the scheduler (this blocks)
            self.scheduler.start()
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
            self.stop()
        except Exception as e:
            logger.error(f"Error starting continuous monitor: {e}")
            self.stop()
            return False
        
        return True
    
    def stop(self):
        """Stop continuous monitoring."""
        logger.info("Stopping continuous monitoring...")
        
        self.is_running = False
        
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
        
        # Clean up monitor resources
        try:
            self.monitor.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        logger.info("Continuous monitoring stopped")
    
    def status(self):
        """Print current monitoring status."""
        print(f"Continuous Job Monitor Status:")
        print(f"  Running: {self.is_running}")
        print(f"  Last run: {self.last_run or 'Never'}")
        print(f"  Check interval: {config.check_interval_minutes} minutes")
        print(f"  Cities: {', '.join(config.cities)}")
        print(f"  Job title: {config.job_title}")
        
        if self.scheduler.running:
            next_run = self.scheduler.get_job('job_check').next_run_time if self.scheduler.get_job('job_check') else None
            print(f"  Next check: {next_run}")
            print(f"  Schedule: Every 30 minutes starting at 4:00 PM")

def main():
    """Main entry point."""
    print("🚀 LinkedIn Associate Product Manager Job Monitor")
    print("=" * 60)
    
    # Validate configuration
    if not config.validate():
        logger.error("Configuration validation failed. Please check your .env file.")
        return 1
    
    monitor = ContinuousJobMonitor()
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'status':
            monitor.status()
            return 0
        elif command == 'test':
            logger.info("Running test search...")
            monitor.monitor.initialize()
            new_jobs = monitor.monitor.find_and_notify_jobs()
            logger.info(f"Test completed - found and sent {new_jobs} jobs")
            return 0
        elif command == 'help':
            print("Available commands:")
            print("  python continuous_monitor.py        - Start continuous monitoring")
            print("  python continuous_monitor.py test   - Run single test check")
            print("  python continuous_monitor.py status - Show status")
            print("  python continuous_monitor.py help   - Show this help")
            return 0
        else:
            logger.error(f"Unknown command: {command}")
            return 1
    
    # Start continuous monitoring
    try:
        success = monitor.start()
        return 0 if success else 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)