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
    """Initialize the job monitor."""
    global job_monitor
    logger.info("🔧 Initializing LinkedIn Job Monitor...")
    
    try:
        job_monitor = LinkedInJobMonitor()
        if job_monitor.initialize():
            logger.info("✅ Job monitor initialized successfully")
            
            # Send startup notification
            job_monitor.discord.notify_status(
                "Railway Web Worker Started",
                f"Job monitoring web worker started at {datetime.now().strftime('%H:%M:%S')}. Health check available at /health",
                'info'
            )
            return True
        else:
            logger.error("❌ Job monitor initialization failed")
            return False
    except Exception as e:
        logger.error(f"❌ Error initializing monitor: {e}")
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
    """Start the job scheduler."""
    global scheduler
    logger.info("📅 Starting job scheduler...")
    
    scheduler = BackgroundScheduler()
    
    # Run first job immediately after 30 seconds to allow initialization
    first_run = datetime.now() + timedelta(seconds=30)
    logger.info(f"⏰ First job search will run at: {first_run.strftime('%H:%M:%S')}")
    logger.info(f"⏰ Then every 30 minutes after that")
    
    # Schedule job every 30 minutes, starting soon
    scheduler.add_job(
        func=scheduled_job_search,
        trigger=IntervalTrigger(minutes=30),
        start_date=first_run,
        id='railway_job_search',
        name='Railway LinkedIn Job Search'
    )
    
    scheduler.start()
    logger.info("✅ Job scheduler started")

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
    """Health check endpoint for Railway."""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'scheduler': 'running' if scheduler and scheduler.running else 'stopped',
        'monitor': 'initialized' if job_monitor else 'not initialized'
    }
    
    if last_search_time:
        health_status['last_search_time'] = last_search_time.isoformat()
        health_status['minutes_since_last_search'] = int((datetime.now() - last_search_time).total_seconds() / 60)
    
    return jsonify(health_status)

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
    """Manually trigger a job search for testing."""
    try:
        logger.info("🔥 Manual job search triggered via web endpoint")
        scheduled_job_search()
        return jsonify({
            'status': 'success',
            'message': 'Job search triggered successfully',
            'result': last_search_result
        })
    except Exception as e:
        logger.error(f"Error in manual trigger: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error triggering job search: {str(e)}'
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