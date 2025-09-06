#!/usr/bin/env python3
"""
Railway-specific worker for LinkedIn Job Monitor
Optimized for Railway's worker process requirements
"""
import os
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

# Setup logging for Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # Railway captures stdout
)

logger = logging.getLogger(__name__)

class RailwayJobWorker:
    """Railway-optimized job monitoring worker."""
    
    def __init__(self):
        """Initialize Railway worker."""
        self.monitor = LinkedInJobMonitor()
        self.scheduler = BlockingScheduler()
        self.is_running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("🚀 Railway Job Worker initialized")
        
        # Log environment info
        railway_env = os.getenv('RAILWAY_ENVIRONMENT', 'unknown')
        logger.info(f"Environment: Railway ({railway_env})")
        logger.info(f"Python version: {sys.version}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
    
    def job_search_task(self):
        """Scheduled job search task."""
        logger.info("🔍 STARTING SCHEDULED JOB SEARCH")
        
        start_time = datetime.now()
        
        try:
            # Send status notification first
            self.monitor.discord.notify_status(
                "Scheduled Search Started",
                f"Starting job search at {start_time.strftime('%H:%M:%S')}",
                'info'
            )
            
            # Find and notify jobs
            total_jobs_sent = self.monitor.find_and_notify_jobs()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if total_jobs_sent > 0:
                logger.info(f"✅ SUCCESS: Found and sent {total_jobs_sent} jobs in {duration:.1f}s")
                self.monitor.discord.notify_status(
                    "Job Search Complete",
                    f"Found and sent {total_jobs_sent} product management jobs",
                    'info'
                )
            else:
                logger.info(f"📭 No new jobs found in {duration:.1f}s")
            
        except Exception as e:
            logger.error(f"❌ ERROR during scheduled search: {e}")
            try:
                self.monitor.discord.notify_status(
                    "Job Search Error",
                    f"Error during scheduled search: {str(e)[:200]}",
                    'error'
                )
            except:
                logger.error("Failed to send error notification")
        
        logger.info("🏁 SCHEDULED JOB SEARCH COMPLETED")
    
    def start(self):
        """Start the Railway worker."""
        logger.info("🚀 Starting Railway Job Worker...")
        
        try:
            # Initialize monitor
            if not self.monitor.initialize():
                logger.error("❌ Failed to initialize job monitor")
                return False
            
            # Send startup notification
            self.monitor.discord.notify_status(
                "Railway Worker Started",
                f"Job monitoring worker started on Railway at {datetime.now().strftime('%H:%M:%S')}",
                'info'
            )
            
            # Calculate next 4:30 PM
            now = datetime.now()
            next_430pm = now.replace(hour=16, minute=30, second=0, microsecond=0)
            
            # If past 4:30 PM today, start from next 30-minute interval
            if now.hour > 16 or (now.hour == 16 and now.minute >= 30):
                # Start from next 30-minute mark
                if now.minute < 30:
                    next_run = now.replace(minute=30, second=0, microsecond=0)
                else:
                    next_run = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
            else:
                next_run = next_430pm
            
            logger.info(f"⏰ Next run scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Schedule job
            self.scheduler.add_job(
                func=self.job_search_task,
                trigger=IntervalTrigger(minutes=30),
                start_date=next_run,
                id='railway_job_search',
                name='Railway LinkedIn Job Search',
                replace_existing=True
            )
            
            logger.info("📅 Scheduled job searches every 30 minutes")
            logger.info("🔄 Worker is running - Railway will keep this alive")
            
            self.is_running = True
            
            # Start scheduler (this blocks)
            self.scheduler.start()
            
        except Exception as e:
            logger.error(f"❌ Error starting Railway worker: {e}")
            return False
    
    def stop(self):
        """Stop the Railway worker."""
        logger.info("🛑 Stopping Railway worker...")
        
        self.is_running = False
        
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
        
        try:
            self.monitor.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        logger.info("✅ Railway worker stopped")

def main():
    """Main entry point for Railway worker."""
    logger.info("🚀 RAILWAY LINKEDIN JOB WORKER")
    logger.info("=" * 60)
    
    # Check if we're on Railway
    if os.getenv('RAILWAY_ENVIRONMENT'):
        logger.info(f"✅ Running on Railway environment: {os.getenv('RAILWAY_ENVIRONMENT')}")
    else:
        logger.info("⚠️ Not detected as Railway environment (running locally?)")
    
    # Validate config
    if not config.validate():
        logger.error("❌ Configuration validation failed")
        return 1
    
    # Create and start worker
    worker = RailwayJobWorker()
    
    try:
        worker.start()
        return 0
    except KeyboardInterrupt:
        logger.info("🛑 Received keyboard interrupt")
        worker.stop()
        return 0
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)