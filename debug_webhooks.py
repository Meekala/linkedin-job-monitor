#!/usr/bin/env python3
"""
Debug webhook URLs in production environment
"""
import os
import sys
import requests
from src.config import config
import re

def validate_webhook_url(url, name):
    """Test webhook URL format and connectivity"""
    print(f"\n=== Testing {name} ===")
    
    if not url:
        print(f"❌ {name}: No URL configured")
        return False
    
    print(f"🔗 URL Length: {len(url)} characters")
    print(f"🔗 First 50 chars: {url[:50]}...")
    print(f"🔗 Last 50 chars: ...{url[-50:]}")
    
    # Check format
    discord_pattern = r'^https://discord\.com/api/webhooks/\d+/[\w\-]+$'
    if not re.match(discord_pattern, url):
        print(f"❌ {name}: Invalid Discord webhook format")
        return False
    else:
        print(f"✅ {name}: Valid Discord webhook format")
    
    # Test connectivity
    try:
        # Send a test payload
        test_payload = {
            "content": f"🧪 **Webhook Test** - Testing {name} from Railway deployment",
            "embeds": [{
                "title": "Webhook Diagnostic Test",
                "description": f"This is a test of the {name} webhook from the Railway environment.",
                "color": 0x00ff00,
                "fields": [
                    {
                        "name": "Environment",
                        "value": "Railway Production" if os.getenv('RAILWAY_ENVIRONMENT') else "Local Development",
                        "inline": True
                    },
                    {
                        "name": "URL Length", 
                        "value": f"{len(url)} characters",
                        "inline": True
                    }
                ]
            }]
        }
        
        response = requests.post(url, json=test_payload, timeout=10)
        
        if response.status_code == 204:
            print(f"✅ {name}: Webhook test successful (204)")
            return True
        else:
            print(f"❌ {name}: Webhook failed with status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ {name}: Connection error - {e}")
        return False

def main():
    print("🔍 Discord Webhook Diagnostics")
    print("=" * 50)
    
    # Show environment info
    print(f"Environment: {'Railway' if os.getenv('RAILWAY_ENVIRONMENT') else 'Local'}")
    print(f"Python version: {sys.version}")
    
    # Test main webhook
    main_success = validate_webhook_url(config.discord_webhook_url, "Main Webhook")
    
    # Test city webhooks
    city_results = {}
    for city, url in config.discord_webhook_urls.items():
        if url:
            city_results[city] = validate_webhook_url(url, f"{city} Webhook")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    total_webhooks = 1 + len([url for url in config.discord_webhook_urls.values() if url])
    successful_webhooks = int(main_success) + sum(city_results.values())
    
    print(f"Total webhooks configured: {total_webhooks}")
    print(f"Successful webhooks: {successful_webhooks}")
    print(f"Failed webhooks: {total_webhooks - successful_webhooks}")
    
    if successful_webhooks == total_webhooks:
        print("✅ All webhooks are working correctly!")
        sys.exit(0)
    else:
        print("❌ Some webhooks are failing - check the details above")
        sys.exit(1)

if __name__ == "__main__":
    main()