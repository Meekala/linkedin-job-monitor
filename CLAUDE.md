# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LinkedIn Job Monitor is an automated system that monitors LinkedIn for Associate Product Manager positions in NYC, LA, and SF. The system uses browser automation (Puppeteer) through an MCP server to extract job data, then sends Discord notifications every 30 minutes with salary ranges, location types, and company career page links.

## Development Commands

**Setup and Installation:**
```bash
./install.sh              # One-command setup with all dependencies
```

**System Management:**
```bash
./start.sh                 # Start both MCP server and Python monitor
./stop.sh                  # Stop all services gracefully
./restart.sh               # Restart entire system
./status.sh                # Check system status and logs
```

**Development and Testing:**
```bash
python src/monitor.py --test    # Test configuration and connections
python src/monitor.py --once    # Run single monitoring check
python src/monitor.py --status  # Detailed system status
```

**MCP Server (Node.js):**
```bash
cd mcp-linkedin-monitor
npm install                     # Install dependencies
node server.js                 # Run MCP server directly
```

**Logs and Monitoring:**
```bash
tail -f logs/monitor.log        # Monitor Python service
tail -f logs/mcp-server.log     # Monitor browser automation
```

## Architecture Notes

### Two-Service Architecture
The system consists of two main services that work together:

1. **MCP Server (Node.js + Puppeteer)**: Browser automation service that navigates LinkedIn and extracts job data from DOM
2. **Python Monitor**: Main orchestration service that processes job data, manages database, and sends Discord notifications

### Data Flow
1. **Python Monitor** calls MCP server every 30 minutes
2. **MCP Server** uses Puppeteer to navigate LinkedIn job searches  
3. **Browser automation** extracts job data directly from page DOM (no OCR)
4. **Job data** includes: title, company, salary, location type, posted time, job IDs
5. **Company career URLs** are generated from company database (100+ companies)
6. **Discord notifications** sent with rich embeds including all job details
7. **SQLite database** handles deduplication and job tracking

### Key Components

**Python Components (src/):**
- `monitor.py` - Main orchestration with APScheduler 
- `database.py` - SQLite job tracking with enhanced Job model
- `discord_notifier.py` - Rich Discord embeds with salary/location data
- `extractor.py` - Job data processing (OCR-free, processes JSON from MCP)
- `company_urls.py` - Database of 100+ company career page URLs
- `config.py` - Environment configuration and LinkedIn URL builders

**MCP Server (mcp-linkedin-monitor/):**
- `server.js` - Main MCP server with DOM extraction tools
- `tools/browser.js` - Puppeteer automation with job data extraction
- `tools/screenshot.js` - Screenshot utilities (legacy, minimally used)

**Management Scripts:**
- All scripts handle both services and provide detailed status/logging
- `install.sh` includes full dependency management and system verification

### Important Implementation Details

**No OCR Dependencies**: The system extracts structured data directly from LinkedIn's DOM using Puppeteer page evaluation, making it much more reliable than screenshot-based OCR approaches.

**LinkedIn Compliance**: 
- 30+ minute intervals to respect rate limits
- Real browser automation (not headless scraping)
- Session persistence to reduce login frequency
- No API violations or aggressive scraping patterns

**Enhanced Job Data**: Unlike typical job scrapers, this system extracts and processes:
- Salary ranges with min/max parsing
- Location types (Remote/Hybrid/On-site) with emoji indicators  
- Posted time with freshness indicators
- LinkedIn job IDs for deduplication
- Direct company career page links (bypasses LinkedIn)

**Error Handling**: The system includes comprehensive error handling for LinkedIn changes, rate limiting, browser crashes, and Discord webhook failures.

### Configuration

The system uses `.env` for configuration with `.env.example` as template. Key settings:
- LinkedIn credentials (personal account recommended)
- Discord webhook URL 
- City configuration (NYC, LA, SF with LinkedIn location IDs)
- Monitoring intervals and rate limiting settings

### Database Schema

SQLite database (`data/jobs.db`) with enhanced job model including new fields for pay ranges, location types, posted times, and company career URLs. Uses job hashing for deduplication based on title+company+location.

### Deployment Notes

Designed for local/personal use rather than cloud deployment. The browser automation requires a display server and works best on macOS/Linux. No Docker configuration due to Puppeteer complexity and limited benefits for single-user deployment.

## Development Tips

**When modifying LinkedIn extraction**: Update DOM selectors in `mcp-linkedin-monitor/tools/browser.js` - LinkedIn frequently changes their class names.

**When adding new companies**: Add to `COMPANY_URLS` dictionary in `src/company_urls.py` with direct links to company career pages filtered for product manager roles.

**When debugging**: Use `LOG_LEVEL=DEBUG` and check both log files. The MCP server logs browser automation issues, while the Python monitor logs data processing and Discord issues.

**Testing changes**: Always run `python src/monitor.py --test` before starting continuous monitoring to verify configuration and connections.