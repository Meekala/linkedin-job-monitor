# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LinkedIn Job Monitor is a fully automated system deployed on Railway that monitors LinkedIn for Associate Product Manager positions in NYC, LA, SF, San Diego, and Remote locations. The system uses HTTP-based job extraction (no browser automation) and sends Discord notifications every 30 minutes at consistent scheduled times (9:00, 9:30, 10:00, etc. Eastern Time).

## Current Architecture (Railway Deployment)

The system is designed as a single-service Railway application that combines web server and job scheduling:

### Main Components

**Railway Web Worker (`railway_web_worker.py`):**
- Flask web server providing health checks and manual triggers
- APScheduler with cron-based timing for consistent schedule
- Integrated job monitoring and Discord notification system  
- Environment variable validation and Railway-specific logging

**Core Python Modules (`src/`):**
- `linkedin_monitor.py` - HTTP-based job extraction from LinkedIn search pages
- `discord_notifier.py` - Rich Discord embeds with webhook fallback logic
- `database.py` - SQLite job tracking with deduplication  
- `config.py` - Environment configuration with Railway support
- `company_urls.py` - Company career page URL generation

**Railway Configuration:**
- `Procfile` - Defines web process for Railway
- `railway.json` - Health check configuration and deployment settings
- `requirements.txt` - Python dependencies (Flask, APScheduler, BeautifulSoup, etc.)

## Data Flow (Current Implementation)

1. **Railway Cron Scheduler**: Runs at 9:00, 9:30, 10:00, 10:30, etc. (Eastern Time)
2. **HTTP Job Search**: Direct GET requests to LinkedIn job search URLs for each city
3. **HTML Parsing**: BeautifulSoup extracts structured job data from search results
4. **Smart Filtering**: Keeps only relevant product management positions, excludes medical/education/etc.
5. **SQLite Deduplication**: Prevents repeat notifications using job hash (title+company+location)
6. **Discord Notifications**: Rich embeds sent to city-specific webhooks with fallback logic
7. **Health Monitoring**: Web endpoints (`/health`, `/status`) track system performance

## Development Commands

**Railway Management:**
```bash
# Deploy to Railway (automatic on git push)
git push origin main

# Check Railway deployment logs  
# (Use Railway dashboard or CLI)

# Test Railway endpoints
curl https://your-app.railway.app/health
curl https://your-app.railway.app/status
curl https://your-app.railway.app/trigger  # Manual job search
```

**Local Development and Testing:**
```bash
# Install dependencies
pip install -r requirements.txt
cp .env.example .env  # Add your Discord webhook URLs

# Test Railway web worker locally
python railway_web_worker.py

# Test single job search
python railway_test.py

# Test Discord notifications
python debug_webhooks.py

# Check configuration
python -c "from src.config import config; print(f'Cities: {config.cities}, Job Title: {config.job_title}')"
```

## Key Implementation Details

### HTTP-Based Job Extraction (No Browser Automation)
- Uses `requests` library with proper headers to fetch LinkedIn job search pages
- Parses HTML with BeautifulSoup to extract job cards and data
- No Puppeteer, no MCP server, no browser dependencies
- Much more reliable and faster than browser automation
- Respects LinkedIn rate limits with appropriate delays

### Railway-Optimized Scheduling
- **Cron-based timing**: Ensures jobs run at exact times (9:00, 9:30, etc.) regardless of deployment time
- **Eastern Time zone**: Configured for US business hours  
- **Health check integration**: Railway monitors `/health` endpoint for automatic restart
- **Environment variable validation**: Comprehensive startup checks for missing configuration

### Enhanced Discord Integration
- **City-specific webhooks**: Separate Discord channels for each city (NYC, LA, SF, SD, Remote)
- **Webhook fallback logic**: If city webhook fails, falls back to main webhook
- **Rich embeds**: Company logos, salary ranges, location types, direct apply links
- **Rate limiting**: Prevents spam with built-in delays and manual trigger cooldowns

### Database and Deduplication
- **SQLite database**: Lightweight, persistent job tracking in `data/jobs.db`
- **Job hashing**: Unique identification prevents duplicate notifications
- **Enhanced job model**: Salary ranges, location types, posting times, career URLs
- **Search logging**: Tracks all search attempts for debugging and analytics

## Configuration (Railway Environment Variables)

**Required:**
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/MAIN_WEBHOOK_ID/TOKEN
JOB_TITLE=Associate Product Manager  
CITIES=NYC,LA,SF,SD,Remote
```

**Optional:**
```env
DISCORD_WEBHOOK_URL_NYC=https://discord.com/api/webhooks/NYC_WEBHOOK_ID/TOKEN
DISCORD_WEBHOOK_URL_LA=https://discord.com/api/webhooks/LA_WEBHOOK_ID/TOKEN
DISCORD_WEBHOOK_URL_SF=https://discord.com/api/webhooks/SF_WEBHOOK_ID/TOKEN
DISCORD_WEBHOOK_URL_SD=https://discord.com/api/webhooks/SD_WEBHOOK_ID/TOKEN
DISCORD_WEBHOOK_URL_Remote=https://discord.com/api/webhooks/REMOTE_WEBHOOK_ID/TOKEN
CHECK_INTERVAL_MINUTES=30
```

## Development Tips

**When modifying job extraction logic:**
- Update selectors in `linkedin_monitor.py` - LinkedIn occasionally changes CSS classes
- Test with `railway_test.py` to verify extraction works correctly
- Check logs for parsing errors or missed job fields

**When adding new cities:**
- Add location ID to `CITY_LOCATIONS` in `src/config.py`  
- Update `CITIES` environment variable in Railway
- Create city-specific Discord webhook if needed

**When debugging Railway issues:**
- Check Railway deployment logs for startup errors
- Use `/health` endpoint to verify system status
- Use `/trigger` endpoint for manual job search testing
- Monitor Discord webhooks to ensure notifications are working

**When modifying schedule:**
- Update cron trigger in `start_scheduler()` function
- Test locally to ensure timing is correct
- Consider timezone implications (system uses Eastern Time)

**Testing changes locally:**
- Always set up `.env` file with real Discord webhooks
- Run `python railway_web_worker.py` to test full system
- Use `python railway_test.py` for quick configuration validation
- Check `data/jobs.db` to verify database operations

## Important Notes

**No MCP Server Required**: The system previously used an MCP server with Puppeteer for browser automation. This has been completely removed in favor of direct HTTP requests, making the system much more reliable and Railway-compatible.

**Railway-First Design**: The current architecture is optimized for Railway deployment with proper health checks, environment variable management, and cloud-native scheduling.

**Production Ready**: The system includes comprehensive error handling, logging, webhook fallbacks, and health monitoring suitable for 24/7 operation.

**Compliance Friendly**: Uses only public LinkedIn job search pages with appropriate rate limiting and no aggressive scraping patterns.