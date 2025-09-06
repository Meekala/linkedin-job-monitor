#!/usr/bin/env python3
"""
Railway Web Worker for LinkedIn Job Monitor
Combines web server (for Railway) with background job scheduler
"""
import os
import sys
import time
import logging
import threading
from datetime import datetime, timedelta
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

# Add src directory to path
sys.path.insert(0, 'src')

from linkedin_monitor import LinkedInJobMonitor
from config import config

# Setup logging for Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# Global variables
app = Flask(__name__)
job_monitor = None
scheduler = None
last_search_time = None
last_search_result = None

def initialize_monitor():
    """Initialize the job monitor with enhanced error handling."""
    global job_monitor
    logger.info("🔧 Initializing LinkedIn Job Monitor...")
    logger.info("=" * 50)
    
    # Check Railway environment
    railway_env = os.getenv('RAILWAY_ENVIRONMENT', 'local')
    logger.info(f"🚂 Railway Environment: {railway_env}")
    
    # Validate required environment variables
    required_env_vars = ['DISCORD_WEBHOOK_URL', 'JOB_TITLE', 'CITIES']
    missing_vars = []
    
    for var in required_env_vars:
        value = os.getenv(var)
        if value:
            # Mask webhook URLs for security
            if 'WEBHOOK' in var:
                masked_value = f"{value[:25]}...{value[-15:]}" if len(value) > 40 else value[:30] + "..."
                logger.info(f"  ✅ {var}: {masked_value}")
            else:
                logger.info(f"  ✅ {var}: {value}")
        else:
            missing_vars.append(var)
            logger.error(f"  ❌ {var}: NOT SET")
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        return False
    
    # Create data directory if it doesn't exist
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        logger.info(f"📁 Created data directory: {data_dir}")
    
    try:
        job_monitor = LinkedInJobMonitor()
        logger.info("📊 Initializing monitor components...")
        
        if job_monitor.initialize():
            logger.info("✅ Job monitor initialized successfully")
            
            # Send startup notification
            startup_message = (
                f"Railway Web Worker Started\n"
                f"Environment: {railway_env}\n"
                f"Time: {datetime.now().strftime('%H:%M:%S')}\n"
                f"Cities: {', '.join(job_monitor.config.cities)}\n"
                f"Job Title: {job_monitor.config.job_title}"
            )
            
            job_monitor.discord.notify_status(
                "Railway Web Worker Started",
                startup_message,
                'info'
            )
            
            logger.info("🚀 Running immediate startup job search...")
            # Run immediate job search to test everything works
            try:
                job_count = job_monitor.find_and_notify_jobs()
                logger.info(f"🎯 Startup job search completed: {job_count} jobs found")
            except Exception as e:
                logger.error(f"⚠️ Startup job search failed: {e}")
                # Don't fail initialization for this
            
            return True
        else:
            logger.error("❌ Job monitor initialization failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error initializing monitor: {e}")
        logger.error(f"Error details: {type(e).__name__}: {str(e)}")
        return False

def scheduled_job_search():
    """Scheduled job search task."""
    global last_search_time, last_search_result
    
    logger.info("🔍 STARTING SCHEDULED JOB SEARCH")
    last_search_time = datetime.now()
    
    try:
        # Send status notification
        job_monitor.discord.notify_status(
            "Scheduled Search Started",
            f"Starting job search at {last_search_time.strftime('%H:%M:%S')}",
            'info'
        )
        
        # Find and notify jobs
        total_jobs_sent = job_monitor.find_and_notify_jobs()
        
        last_search_result = {
            'jobs_found': total_jobs_sent,
            'success': True,
            'timestamp': last_search_time.isoformat()
        }
        
        duration = (datetime.now() - last_search_time).total_seconds()
        
        if total_jobs_sent > 0:
            logger.info(f"✅ SUCCESS: Found and sent {total_jobs_sent} jobs in {duration:.1f}s")
            job_monitor.discord.notify_status(
                "Job Search Complete",
                f"Found and sent {total_jobs_sent} product management jobs in {duration:.1f}s",
                'info'
            )
        else:
            logger.info(f"📭 No new jobs found in {duration:.1f}s")
        
    except Exception as e:
        logger.error(f"❌ ERROR during scheduled search: {e}")
        last_search_result = {
            'jobs_found': 0,
            'success': False,
            'error': str(e),
            'timestamp': last_search_time.isoformat()
        }
        
        try:
            job_monitor.discord.notify_status(
                "Job Search Error",
                f"Error during scheduled search: {str(e)[:200]}",
                'error'
            )
        except:
            logger.error("Failed to send error notification")
    
    logger.info("🏁 SCHEDULED JOB SEARCH COMPLETED")

def start_scheduler():
    """Start the job scheduler with 9am start and consistent schedule."""
    global scheduler
    logger.info("📅 Starting job scheduler...")
    
    scheduler = BackgroundScheduler(
        timezone='US/Eastern',  # Set timezone for consistent scheduling
        job_defaults={
            'coalesce': False,
            'max_instances': 1,
            'misfire_grace_time': 300  # 5 minutes grace time
        }
    )
    
    # Calculate interval from config (default 30 minutes)
    interval_minutes = int(os.getenv('CHECK_INTERVAL_MINUTES', '30'))
    
    # Schedule job to run at consistent times starting at 9:00 AM ET
    # This ensures jobs run at 9:00, 9:30, 10:00, 10:30, etc.
    logger.info(f"⏰ Scheduling jobs to run every {interval_minutes} minutes starting at 9:00 AM ET")
    logger.info("📋 Schedule: 9:00 AM, 9:30 AM, 10:00 AM, 10:30 AM, etc.")
    
    # Use cron trigger to run at specific minute intervals aligned to the hour
    if interval_minutes == 30:
        # Run at :00 and :30 minutes past each hour, starting from 9 AM
        cron_minute = "0,30"
        cron_hour = "9-23"  # 9 AM to 11 PM ET
    elif interval_minutes == 15:
        # Run every 15 minutes starting from 9 AM
        cron_minute = "0,15,30,45"
        cron_hour = "9-23"
    elif interval_minutes == 60:
        # Run every hour starting from 9 AM
        cron_minute = "0"
        cron_hour = "9-23"
    else:
        # Fallback to interval-based scheduling if custom interval
        logger.info(f"Using interval-based scheduling for {interval_minutes} minute interval")
        first_run = datetime.now() + timedelta(minutes=2)
        scheduler.add_job(
            func=scheduled_job_search,
            trigger=IntervalTrigger(minutes=interval_minutes),
            start_date=first_run,
            id='railway_job_search',
            name=f'Railway LinkedIn Job Search (every {interval_minutes}m)',
            replace_existing=True
        )
        scheduler.start()
        logger.info(f"✅ Job scheduler started with custom {interval_minutes}-minute interval")
        return
    
    # Schedule with cron trigger for consistent times
    scheduler.add_job(
        func=scheduled_job_search,
        trigger=CronTrigger(
            minute=cron_minute,
            hour=cron_hour,
            timezone='US/Eastern'
        ),
        id='railway_job_search_cron',
        name=f'Railway LinkedIn Job Search (every {interval_minutes}m from 9 AM)',
        replace_existing=True
    )
    
    # Also add immediate startup job (runs once in 2 minutes)
    startup_time = datetime.now() + timedelta(minutes=2)
    scheduler.add_job(
        func=lambda: logger.info("🚀 Startup job completed - cron schedule now active"),
        trigger='date',
        run_date=startup_time,
        id='startup_job',
        name='One-time startup job'
    )
    
    scheduler.start()
    logger.info(f"✅ Job scheduler started with cron schedule ({interval_minutes}m intervals from 9 AM)")
    
    # Log scheduler info
    logger.info(f"📊 Scheduler timezone: {scheduler.timezone}")
    jobs = scheduler.get_jobs()
    logger.info(f"📊 Active jobs: {len(jobs)}")
    for job in jobs:
        logger.info(f"  - {job.name} (next run: {job.next_run_time})")

@app.route('/')
def home():
    """Home page with status."""
    return jsonify({
        'status': 'running',
        'service': 'LinkedIn Job Monitor',
        'environment': 'Railway',
        'timestamp': datetime.now().isoformat(),
        'scheduler_running': scheduler.running if scheduler else False,
        'last_search': last_search_result
    })

@app.route('/health')
def health():
    """Enhanced health check endpoint for Railway."""
    now = datetime.now()
    
    # Determine overall health status
    is_healthy = True
    issues = []
    
    if not job_monitor:
        is_healthy = False
        issues.append("Job monitor not initialized")
    
    if not scheduler or not scheduler.running:
        is_healthy = False
        issues.append("Scheduler not running")
    
    # Check if we've had a recent search (within last 2 hours)
    if last_search_time:
        minutes_since = int((now - last_search_time).total_seconds() / 60)
        if minutes_since > 120:  # More than 2 hours
            is_healthy = False
            issues.append(f"No search in {minutes_since} minutes")
    else:
        issues.append("No searches recorded yet")
    
    health_status = {
        'status': 'healthy' if is_healthy else 'unhealthy',
        'timestamp': now.isoformat(),
        'uptime_minutes': int((now - datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds() / 60),
        'railway_environment': os.getenv('RAILWAY_ENVIRONMENT', 'local'),
        'scheduler': {
            'running': scheduler.running if scheduler else False,
            'job_count': len(scheduler.get_jobs()) if scheduler else 0,
            'next_job_time': scheduler.get_jobs()[0].next_run_time.isoformat() if scheduler and scheduler.get_jobs() else None
        },
        'monitor': {
            'initialized': job_monitor is not None,
            'cities': job_monitor.config.cities if job_monitor else None,
            'job_title': job_monitor.config.job_title if job_monitor else None
        },
        'last_search': {
            'time': last_search_time.isoformat() if last_search_time else None,
            'minutes_ago': int((now - last_search_time).total_seconds() / 60) if last_search_time else None,
            'result': last_search_result
        },
        'issues': issues
    }
    
    # Return appropriate HTTP status
    status_code = 200 if is_healthy else 503
    return jsonify(health_status), status_code

@app.route('/status')
def status():
    """Detailed status endpoint."""
    return jsonify({
        'service': 'LinkedIn Job Monitor',
        'environment': os.getenv('RAILWAY_ENVIRONMENT', 'unknown'),
        'scheduler_running': scheduler.running if scheduler else False,
        'job_monitor_initialized': job_monitor is not None,
        'cities_monitored': config.cities,
        'job_title': config.job_title,
        'last_search_result': last_search_result,
        'last_search_time': last_search_time.isoformat() if last_search_time else None,
        'uptime': datetime.now().isoformat()
    })

@app.route('/trigger')  
def trigger_search():
    """Manually trigger a job search for testing with rate limiting."""
    global last_search_time
    
    # Simple rate limiting - only allow manual triggers every 5 minutes
    if last_search_time and (datetime.now() - last_search_time).total_seconds() < 300:
        minutes_left = 5 - int((datetime.now() - last_search_time).total_seconds() / 60)
        return jsonify({
            'status': 'rate_limited',
            'message': f'Please wait {minutes_left} minutes before triggering again',
            'last_search_time': last_search_time.isoformat()
        }), 429
    
    try:
        logger.info("🔥 Manual job search triggered via web endpoint")
        scheduled_job_search()
        return jsonify({
            'status': 'success',
            'message': 'Job search triggered successfully',
            'timestamp': datetime.now().isoformat(),
            'result': last_search_result
        })
    except Exception as e:
        logger.error(f"Error in manual trigger: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error triggering job search: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    logger.info("🚀 RAILWAY WEB WORKER STARTING")
    logger.info("=" * 60)
    
    # Check Railway environment
    railway_env = os.getenv('RAILWAY_ENVIRONMENT', 'local')
    port = int(os.getenv('PORT', 8080))
    
    logger.info(f"Environment: {railway_env}")
    logger.info(f"Port: {port}")
    
    # Initialize components
    if not initialize_monitor():
        logger.error("❌ Failed to initialize monitor - exiting")
        sys.exit(1)
    
    # Start scheduler
    try:
        start_scheduler()
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {e}")
        sys.exit(1)
    
    # Start web server
    logger.info(f"🌐 Starting web server on port {port}")
    logger.info("📍 Available endpoints:")
    logger.info("  / - Home status")
    logger.info("  /health - Health check")
    logger.info("  /status - Detailed status")
    logger.info("  /trigger - Manual job search trigger")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.error(f"❌ Web server error: {e}")
        if scheduler:
            scheduler.shutdown()
        sys.exit(1)