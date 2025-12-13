# 🚀 Deployment Quick Start Guide

Quick reference for deploying Hiker Bot to Google Cloud Run.

## 📋 Prerequisites Checklist

- [ ] Google Cloud account with billing enabled
- [ ] GitHub repository created
- [ ] WhatsApp Cloud API credentials
- [ ] MongoDB URI (Atlas or self-hosted)
- [ ] Google Cloud SDK installed (`gcloud`)

## 🎯 Three Deployment Options

### Option 1: One-Time Manual Deployment

```bash
# Set environment variables
export WHATSAPP_PHONE_NUMBER_ID=your_id
export WHATSAPP_ACCESS_TOKEN=your_token
export WEBHOOK_VERIFY_TOKEN=your_token
export MONGODB_URI=your_mongodb_uri

# Deploy
./scripts/deploy_cloud_run.sh us-central1 your-project-id
```

### Option 2: GitHub Integration (CI/CD) - Recommended

```bash
# Set up automatic deployments from GitHub
./scripts/setup_github_cloud_build.sh your-project-id us-central1 your-github-username Hiker main

# Now every push to main branch automatically deploys!
```

### Option 3: Using Cloud Build Directly

```bash
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions=_REGION=us-central1,\
_WHATSAPP_PHONE_NUMBER_ID=your_id,\
_WHATSAPP_ACCESS_TOKEN=your_token,\
_WEBHOOK_VERIFY_TOKEN=your_token,\
_MONGODB_URI=your_uri
```

## 🔧 Initial Setup (One Time)

```bash
# 1. Login to Google Cloud
gcloud auth login

# 2. Set your project
gcloud config set project YOUR_PROJECT_ID

# 3. Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

## 🔗 Connect GitHub Repository

### Using Cloud Console (Easiest)

1. Go to [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)
2. Click "Connect Repository"
3. Select "GitHub (Cloud Build GitHub App)"
4. Authorize and select your repository
5. Click "Create Trigger"
6. Configure:
   - Name: `deploy-hiker-bot`
   - Event: Push to branch `main`
   - Config: `cloudbuild.yaml`
   - Set substitution variables

### Using Script

```bash
./scripts/setup_github_cloud_build.sh
```

## 🔐 Environment Variables

### Option A: Substitution Variables (Simple)

Set in Cloud Build trigger configuration:
- `_WHATSAPP_PHONE_NUMBER_ID`
- `_WHATSAPP_ACCESS_TOKEN`
- `_WEBHOOK_VERIFY_TOKEN`
- `_MONGODB_URI`
- `_MONGODB_DB_NAME` (default: `hiker_db`)

### Option B: Secret Manager (Secure)

```bash
# Create secrets
echo -n "value" | gcloud secrets create secret-name --data-file=-

# Grant Cloud Build access
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding secret-name \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## ✅ Verify Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe hiker-bot --region us-central1 --format 'value(status.url)')

# Test health endpoint
curl $SERVICE_URL/health

# View logs
gcloud run services logs read hiker-bot --region us-central1
```

## 🔄 Update Webhook URL

After deployment, update WhatsApp webhook:

1. Go to [Meta Developer Console](https://developers.facebook.com/)
2. Select your WhatsApp app
3. Configuration > Webhook
4. Set Callback URL: `https://YOUR_SERVICE_URL/webhook`
5. Set Verify Token: (match your `WEBHOOK_VERIFY_TOKEN`)

## 📊 Monitor Deployments

```bash
# View build history
gcloud builds list --limit=10

# View specific build logs
gcloud builds log BUILD_ID

# View Cloud Run service
gcloud run services describe hiker-bot --region us-central1
```

## 🐛 Troubleshooting

### Build Fails

```bash
# Check build logs
gcloud builds list --limit=1
gcloud builds log BUILD_ID
```

### Service Won't Start

```bash
# Check service logs
gcloud run services logs read hiker-bot --region us-central1 --limit=50
```

### GitHub Trigger Not Working

1. Verify repository is connected in Cloud Console
2. Check trigger is enabled
3. Verify branch pattern matches your branch
4. Check build history for errors

## 📚 Full Documentation

- **Cloud Run Deployment**: [docs/CLOUD_RUN_DEPLOYMENT.md](CLOUD_RUN_DEPLOYMENT.md)
- **GitHub Integration**: [docs/GITHUB_CLOUD_BUILD_SETUP.md](GITHUB_CLOUD_BUILD_SETUP.md)

## 🎉 Success!

Once deployed, your bot will:
- ✅ Automatically deploy on every push to `main` (if GitHub integration set up)
- ✅ Scale automatically based on traffic
- ✅ Handle webhook requests from WhatsApp
- ✅ Log all activity to Cloud Logging

---

**Need help?** Check the detailed guides or build logs!

