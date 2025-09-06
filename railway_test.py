#!/usr/bin/env python3
"""
Railway deployment test script
Tests if the environment is working correctly on Railway
"""
import os
import sys
import logging
from datetime import datetime

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def test_railway_environment():
    """Test Railway environment and configuration"""
    logger.info("🚀 RAILWAY ENVIRONMENT TEST")
    logger.info("=" * 50)
    
    # Check if we're on Railway
    railway_env = os.getenv('RAILWAY_ENVIRONMENT')
    if railway_env:
        logger.info(f"✅ Running on Railway environment: {railway_env}")
    else:
        logger.info("⚠️ Not detected as Railway environment")
    
    # Check Python version
    logger.info(f"🐍 Python version: {sys.version}")
    
    # Check current time
    now = datetime.now()
    logger.info(f"⏰ Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test environment variables
    logger.info("🔐 Checking environment variables...")
    env_vars = [
        'DISCORD_WEBHOOK_URL',
        'DISCORD_WEBHOOK_URL_NYC', 
        'DISCORD_WEBHOOK_URL_LA',
        'DISCORD_WEBHOOK_URL_SF',
        'DISCORD_WEBHOOK_URL_SD',
        'JOB_TITLE',
        'CITIES'
    ]
    
    missing_vars = []
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Show first/last few characters for security
            masked = f"{value[:10]}...{value[-10:]}" if len(value) > 20 else value
            logger.info(f"  ✅ {var}: {masked}")
        else:
            missing_vars.append(var)
            logger.info(f"  ❌ {var}: NOT SET")
    
    if missing_vars:
        logger.error(f"Missing environment variables: {missing_vars}")
        return False
    
    # Test imports
    logger.info("📦 Testing imports...")
    try:
        sys.path.insert(0, 'src')
        from linkedin_monitor import LinkedInJobMonitor
        from config import config
        logger.info("✅ All imports successful")
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        return False
    
    # Test Discord webhook
    logger.info("🔔 Testing Discord notification...")
    try:
        monitor = LinkedInJobMonitor()
        success = monitor.discord.notify_status(
            "Railway Test", 
            f"Railway worker process is running! Time: {now.strftime('%H:%M:%S')}", 
            'info'
        )
        if success:
            logger.info("✅ Discord notification sent successfully")
        else:
            logger.error("❌ Discord notification failed")
            return False
    except Exception as e:
        logger.error(f"❌ Discord test failed: {e}")
        return False
    
    logger.info("🎉 All Railway environment tests passed!")
    return True

def test_job_search():
    """Test a quick job search"""
    logger.info("🔍 Testing job search...")
    try:
        sys.path.insert(0, 'src')
        from linkedin_monitor import LinkedInJobMonitor
        
        monitor = LinkedInJobMonitor()
        if not monitor.initialize():
            logger.error("❌ Monitor initialization failed")
            return False
        
        # Test with one city
        success, jobs = monitor.extract_jobs_http('NYC')
        logger.info(f"Job search result: {len(jobs)} jobs found")
        
        for i, job in enumerate(jobs[:3]):
            logger.info(f"  {i+1}. {job.title} at {job.company}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Job search test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting Railway environment test...")
    
    env_ok = test_railway_environment()
    if env_ok:
        job_ok = test_job_search()
        
        if env_ok and job_ok:
            logger.info("✅ ALL TESTS PASSED - Railway environment is working")
        else:
            logger.error("❌ SOME TESTS FAILED")
    
    logger.info("Railway test completed")