# LinkedIn Job Monitor

A lightweight job monitoring system that automatically searches LinkedIn for Associate Product Manager positions and sends notifications to city-specific Discord channels.

## Features

- **Fast HTTP Extraction**: Direct LinkedIn API requests (no browser automation needed)
- **City-Specific Webhooks**: Separate Discord channels for NYC, LA, SF, SD, and Remote jobs  
- **Rich Job Information**: Company, salary, location type, posting time, and apply links
- **Duplicate Prevention**: SQLite database prevents spam notifications
- **Security Focused**: Input validation, webhook URL verification, and sanitized outputs
- **Lightweight**: ~5MB total size, minimal dependencies
- **30-Minute Monitoring**: Finds jobs posted in the last 30 minutes

## Quick Start

### 1. Setup
```bash
git clone <your-repo>
cd job-hunt
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Discord webhook URLs
```

### 2. Run
```bash
# Start continuous monitoring (every 30 minutes)
python continuous_monitor.py

# Run once for testing
python continuous_monitor.py test
```

## Configuration

Create Discord webhooks for each city:
1. Go to Discord Server → Settings → Integrations → Webhooks
2. Create webhooks for different channels (optional)
3. Add URLs to your `.env` file

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_MAIN_WEBHOOK
DISCORD_WEBHOOK_URL_NYC=https://discord.com/api/webhooks/YOUR_NYC_WEBHOOK
DISCORD_WEBHOOK_URL_SF=https://discord.com/api/webhooks/YOUR_SF_WEBHOOK
# ... etc
```

## Project Structure

```
Job Hunt/
├── .env                    # Your webhook URLs (create from .env.example)
├── continuous_monitor.py   # Main monitoring script  
├── requirements.txt        # Python dependencies
├── src/
│   ├── config.py          # Configuration management
│   ├── database.py        # Job tracking database
│   ├── discord_notifier.py # Discord notifications
│   └── linkedin_monitor.py # HTTP job extraction
└── data/                  # Runtime data (auto-created)
    └── jobs.db            # SQLite database
```

## Security

- ✅ No LinkedIn credentials required
- ✅ Input sanitization prevents injection
- ✅ Webhook URL validation
- ✅ Rate limiting respects LinkedIn
- ✅ No sensitive data in logs

## Commands

- `python continuous_monitor.py` - Start monitoring
- `python continuous_monitor.py test` - Run single test
- `python continuous_monitor.py status` - Show status  
- `python continuous_monitor.py help` - Show help