# 🚀 Railway.app Deployment Guide

## 🔒 Security-First Setup

### Step 1: Prepare Repository
```bash
# Make sure .env is NOT committed
git add .
git commit -m "Prepare for secure Railway deployment"
git push origin main
```

### Step 2: Railway Account Setup
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub (recommended)
3. Verify your account

### Step 3: Create New Project
1. Click "New Project"
2. Choose "Deploy from GitHub repo"
3. Select your job monitor repository
4. Click "Deploy Now"

### Step 4: Configure Environment Variables (CRITICAL)
In Railway dashboard → Variables tab, add these (use your actual values):

```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/[YOUR_MAIN_WEBHOOK]
DISCORD_WEBHOOK_URL_NYC=https://discord.com/api/webhooks/[YOUR_NYC_WEBHOOK] 
DISCORD_WEBHOOK_URL_LA=https://discord.com/api/webhooks/[YOUR_LA_WEBHOOK]
DISCORD_WEBHOOK_URL_SF=https://discord.com/api/webhooks/[YOUR_SF_WEBHOOK]
DISCORD_WEBHOOK_URL_SD=https://discord.com/api/webhooks/[YOUR_SD_WEBHOOK]
DISCORD_WEBHOOK_URL_Remote=https://discord.com/api/webhooks/[YOUR_REMOTE_WEBHOOK]
CHECK_INTERVAL_MINUTES=30
CITIES=NYC,LA,SF,SD,Remote
JOB_TITLE=Associate Product Manager
DATABASE_PATH=data/jobs.db
LOG_LEVEL=INFO
LOG_FILE=data/linkedin_monitor.log
```

### Step 5: Deploy & Monitor
1. Railway will automatically build and deploy
2. Check "Deployments" tab for build status
3. Monitor "Logs" tab for any issues
4. Verify Discord notifications are working

## 🛡️ Security Verification

After deployment, verify:
- [ ] No webhook URLs visible in logs
- [ ] Environment variables loaded correctly
- [ ] Application starts without errors
- [ ] Discord notifications work
- [ ] No sensitive data in Railway logs

## 📊 Monitoring

Railway provides:
- **Logs**: Real-time application logs
- **Metrics**: CPU/Memory usage
- **Deployments**: Build history
- **Variables**: Environment variable management

## 💰 Cost Estimate
- **Free Tier**: 500 execution hours/month
- **Your Usage**: ~15 hours/month (30 mins every 30 mins)
- **Cost**: $0/month (well within free limits)

## 🚨 Troubleshooting

**Build Fails**: Check Python version in runtime.txt
**App Crashes**: Check environment variables are set
**No Notifications**: Verify Discord webhook URLs
**Rate Limits**: Check LinkedIn/Discord rate limiting

## 🔄 Updates
To update the deployment:
```bash
git add .
git commit -m "Update job monitor"
git push origin main
# Railway auto-deploys from main branch
```