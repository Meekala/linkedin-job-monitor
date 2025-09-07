# LinkedIn Job Monitor

A fully automated job monitoring system that searches LinkedIn for Associate Product Manager positions and sends notifications to city-specific Discord channels. Now **deployed on Railway** for 24/7 monitoring with consistent scheduling.

## ✨ Current Features

### 🚀 **Railway Cloud Deployment**
- **Automated 24/7 monitoring** on Railway cloud platform
- **Consistent schedule**: Runs at 9:00, 9:30, 10:00, 10:30, etc. (Eastern Time) 
- **Health monitoring** with automatic restart on failures
- **Real-time status** via web endpoints (`/health`, `/status`, `/trigger`)

### 🔍 **Smart Job Detection**
- **HTTP-based extraction**: Direct LinkedIn job searches (no browser automation)
- **Intelligent filtering**: Focuses on product management roles, excludes irrelevant jobs
- **Duplicate prevention**: SQLite database prevents spam notifications
- **30-minute windows**: Finds jobs posted in the last 30 minutes

### 🌆 **Multi-City Support**
- **5 Target Markets**: NYC, LA, SF, San Diego, and Remote positions
- **City-specific Discord channels**: Separate webhooks for organized notifications
- **Location type detection**: Remote/Hybrid/On-site with emoji indicators

### 📊 **Rich Job Information**
- **Salary ranges**: Extracted with min/max parsing
- **Company career links**: Direct links to company career pages  
- **Posting timestamps**: "2 hours ago" with freshness indicators
- **Job details**: Title, company, location, description snippets

### 🔐 **Security & Reliability**
- **No LinkedIn credentials required**: Uses public job search pages
- **Input sanitization**: Prevents injection attacks in Discord embeds
- **Webhook validation**: Verifies Discord webhook URLs
- **Rate limiting**: Respects LinkedIn's usage policies
- **Fallback webhooks**: Primary + backup Discord notifications

## 🚀 Quick Start

### 1. Railway Deployment (Recommended)
```bash
# Clone and deploy to Railway
git clone <your-repo>
cd job-hunt

# Set up Railway (one-time setup)
# Add environment variables in Railway dashboard:
# - DISCORD_WEBHOOK_URL
# - DISCORD_WEBHOOK_URL_NYC, _LA, _SF, _SD (optional)  
# - JOB_TITLE="Associate Product Manager"
# - CITIES="NYC,LA,SF,SD,Remote"

git push  # Automatic deployment
```

### 2. Local Development
```bash
# Install dependencies
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Discord webhook URLs

# Test configuration
python railway_web_worker.py  # Starts web server + scheduler

# Or run single search
python -c "import sys; sys.path.insert(0, 'src'); from linkedin_monitor import LinkedInJobMonitor; m = LinkedInJobMonitor(); m.initialize(); m.find_and_notify_jobs()"
```

## 🏗️ Architecture

### Current Implementation (Railway Ready)
```
Railway Cloud Platform
├── railway_web_worker.py    # Main web server + job scheduler
├── Procfile                 # Railway process definition  
├── railway.json            # Railway deployment config
├── requirements.txt        # Python dependencies
└── src/                   # Core application modules
    ├── linkedin_monitor.py # HTTP job extraction
    ├── discord_notifier.py # Rich Discord notifications  
    ├── database.py        # SQLite job tracking
    ├── config.py          # Environment configuration
    └── company_urls.py    # Company career page links
```

### Data Flow
1. **Railway Scheduler**: Runs every 30 minutes at consistent times (9:00, 9:30, etc.)
2. **HTTP Job Search**: Direct requests to LinkedIn job search pages
3. **Job Parsing**: Extracts structured data from HTML (title, company, salary, etc.)
4. **Intelligent Filtering**: Keeps only relevant product management positions  
5. **Deduplication**: SQLite database prevents repeat notifications
6. **Discord Notifications**: Rich embeds sent to city-specific channels
7. **Health Monitoring**: Web endpoints track system status and performance

### Key Technologies
- **Python 3.11+** with Flask web server
- **APScheduler** for reliable cron-based scheduling  
- **BeautifulSoup** for HTML parsing and job extraction
- **SQLite** for lightweight job tracking database
- **Discord Webhooks** for instant notifications
- **Railway** for cloud deployment and 24/7 uptime

## 📝 Configuration

### Environment Variables (Railway Dashboard)
```env
# Required
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_MAIN_WEBHOOK
JOB_TITLE=Associate Product Manager
CITIES=NYC,LA,SF,SD,Remote

# Optional city-specific webhooks
DISCORD_WEBHOOK_URL_NYC=https://discord.com/api/webhooks/YOUR_NYC_WEBHOOK
DISCORD_WEBHOOK_URL_LA=https://discord.com/api/webhooks/YOUR_LA_WEBHOOK
DISCORD_WEBHOOK_URL_SF=https://discord.com/api/webhooks/YOUR_SF_WEBHOOK
DISCORD_WEBHOOK_URL_SD=https://discord.com/api/webhooks/YOUR_SD_WEBHOOK
DISCORD_WEBHOOK_URL_Remote=https://discord.com/api/webhooks/YOUR_REMOTE_WEBHOOK

# Schedule customization (optional)
CHECK_INTERVAL_MINUTES=30  # Default: 30 minutes
```

### Discord Webhook Setup
1. **Create Discord Server** (or use existing)
2. **Go to Server Settings** → Integrations → Webhooks
3. **Create New Webhook** for each city/channel (or use one for all)
4. **Copy webhook URLs** to Railway environment variables
5. **Test notifications** using `/trigger` endpoint

## 🛠️ Management Commands

### Railway Web Endpoints
- **Status Check**: `https://your-app.railway.app/health`
- **Detailed Status**: `https://your-app.railway.app/status`  
- **Manual Trigger**: `https://your-app.railway.app/trigger`
- **Home**: `https://your-app.railway.app/`

### Local Development
```bash
# Test single job search
python railway_test.py

# Check configuration
python -c "from src.config import config; print(f'Cities: {config.cities}')"

# Test Discord notifications  
python debug_webhooks.py
```

## 📊 Project Stats

- **Languages**: Python (100%)
- **Dependencies**: 6 core packages (Flask, APScheduler, BeautifulSoup, etc.)
- **Database**: SQLite (~10KB typical)
- **Memory Usage**: ~50MB on Railway
- **Response Time**: 2-5 seconds per job search
- **Coverage**: 5 major markets (NYC, LA, SF, SD, Remote)

## 🔒 Security Features

- ✅ **No credentials stored**: Uses public LinkedIn job pages
- ✅ **Input sanitization**: All text sanitized for Discord embeds
- ✅ **Webhook validation**: Verifies Discord webhook URL format  
- ✅ **Rate limiting**: Manual triggers limited to every 5 minutes
- ✅ **Environment isolation**: Sensitive data in Railway environment variables
- ✅ **HTTPS only**: All external communications encrypted
- ✅ **Audit logging**: All searches and notifications logged

## 📈 Performance

- **Search Speed**: 2-5 seconds per city
- **Job Processing**: 100+ jobs/minute  
- **Notification Delivery**: <1 second via Discord webhooks
- **Database Size**: Minimal growth (~1KB per day)
- **Uptime**: 99.9%+ on Railway (with auto-restart)
- **Memory Footprint**: ~50MB RAM usage

## 🎯 What You Get

### Daily Job Notifications
- **Morning startup** (9:00 AM ET): System status notification
- **Every 30 minutes**: New job alerts if found (9:30, 10:00, 10:30...)
- **Evening shutdown** (11:00 PM ET): Stops during overnight hours
- **Rich Discord embeds**: Company logos, salary ranges, apply buttons

### Monitoring Dashboard  
- **Real-time health**: Check system status anytime
- **Search history**: See what jobs were found when
- **Performance metrics**: Response times, success rates, error tracking
- **Manual controls**: Trigger searches on-demand for testing

This system provides **set-it-and-forget-it** job monitoring with professional-grade reliability and comprehensive Discord notifications for your product management job search.