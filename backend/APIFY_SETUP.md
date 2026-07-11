# Apify API Setup Guide

## Quick Start

### 1. Sign Up for Apify (Free Tier)

1. Go to [https://apify.com](https://apify.com)
2. Click "Sign Up" (free tier includes 5,000 results/month)
3. Verify your email

### 2. Get Your API Token

1. Log in to Apify Console: [https://console.apify.com](https://console.apify.com)
2. Go to **Settings** → **Integrations**
3. Copy your **Personal API Token**

### 3. Configure the Backend

**Option A: Environment Variable (Recommended)**

Windows PowerShell:
```powershell
$env:APIFY_API_TOKEN="your_token_here"
```

Windows CMD:
```cmd
set APIFY_API_TOKEN=your_token_here
```

Linux/Mac:
```bash
export APIFY_API_TOKEN=your_token_here
```

**Option B: .env File**

1. Create a `.env` file in the `StrategaAi/` backend directory:
```bash
cd d:\StrategaAi\StrategaAi
copy .env.example .env
```

2. Edit `.env` and add your token:
```
APIFY_API_TOKEN=your_actual_token_here
```

3. Install python-dotenv (if not already installed):
```bash
pip install python-dotenv
```

4. Update `apify_service.py` to load from .env:
```python
from dotenv import load_dotenv
load_dotenv()
```

### 4. Restart the Backend Server

The server should auto-reload, but if not:
```bash
# Stop the current server (Ctrl+C)
# Then restart:
cd d:\StrategaAi\StrategaAi
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Test the API

```bash
curl -X POST http://localhost:8000/scraper/start \
  -H "Content-Type: application/json" \
  -d '{"product_name": "headset", "category": "electronics"}'
```

Or use PowerShell:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/scraper/start" `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"product_name": "headset", "category": "electronics"}'
```

## What Happens Without API Token?

- **Made-in-China**: ✅ Works normally (no API needed)
- **DHgate**: Returns empty array (graceful fallback)
- **AliExpress**: Returns empty array (graceful fallback)
- **Retail scrapers**: ✅ Work normally (no API needed)

The system will print warnings in the console:
```
⚠️ APIFY_API_TOKEN not set. Skipping DHgate API scraping.
⚠️ APIFY_API_TOKEN not set. Skipping AliExpress API scraping.
```

## Free Tier Limits

- **5,000 results per month**
- **Unlimited actors** (scrapers)
- **100 MB storage**
- **10 concurrent runs**

For your use case (100 products/day):
- Daily: 100 products × 2 platforms = 200 results
- Monthly: 200 × 30 = 6,000 results
- **You'll need the paid tier** ($49/month for 100K results)

**OR** use the free tier strategically:
- Use Made-in-China (free) as primary
- Use Apify only when Made-in-China has no results
- Cache results to reduce API calls

## Monitoring Usage

1. Go to [https://console.apify.com](https://console.apify.com)
2. Click **Usage** in the sidebar
3. View your monthly consumption

## Troubleshooting

### "APIFY_API_TOKEN not set"
- Check environment variable is set
- Restart the backend server after setting the variable

### "API returned status 401"
- Invalid API token
- Token expired (regenerate in Apify Console)

### "API returned status 429"
- Rate limit exceeded
- Upgrade to paid tier or wait for monthly reset

### "Timeout error"
- Apify API can take 30-120 seconds
- This is normal for first-time scraping
- Results are cached for subsequent requests

## Cost Optimization Tips

1. **Cache results** - Store scraped data for 24 hours
2. **Batch requests** - Scrape multiple products at once
3. **Use Made-in-China first** - Only call Apify if MIC fails
4. **Monitor usage** - Set up alerts in Apify Console
5. **Start with free tier** - Test before committing to paid

## Alternative: Keep Made-in-China Only

If you don't want to use Apify:
- Made-in-China scraper works perfectly
- Returns 2-10 wholesale products
- 100% free and reliable
- No API key needed

The system is designed to work with or without Apify!
