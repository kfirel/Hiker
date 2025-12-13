# 🚀 Google Cloud Run Deployment Guide

This guide will walk you through deploying the Hiker WhatsApp Bot to Google Cloud Run using Docker.

## 📋 Prerequisites

1. **Google Cloud Account** with billing enabled
2. **Google Cloud SDK (gcloud)** installed and configured
3. **Docker** installed (for local testing)
4. **MongoDB Atlas** account (or MongoDB instance accessible from Cloud Run)
5. **WhatsApp Cloud API** credentials

## 🔧 Setup Steps

### 1. Install Google Cloud SDK

```bash
# macOS
brew install google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Windows
# Download from https://cloud.google.com/sdk/docs/install
```

### 2. Authenticate and Set Project

```bash
# Login to Google Cloud
gcloud auth login

# Set your project ID
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 3. Configure Environment Variables

You have two options for setting environment variables:

#### Option A: Using Secret Manager (Recommended for Production)

```bash
# Create secrets
echo -n "your_whatsapp_phone_number_id" | gcloud secrets create whatsapp-phone-number-id --data-file=-
echo -n "your_whatsapp_access_token" | gcloud secrets create whatsapp-access-token --data-file=-
echo -n "your_webhook_verify_token" | gcloud secrets create webhook-verify-token --data-file=-
echo -n "your_mongodb_uri" | gcloud secrets create mongodb-uri --data-file=-

# Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding whatsapp-phone-number-id \
    --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
# Repeat for other secrets...
```

#### Option B: Using Cloud Build Substitutions (Simpler)

Set substitution variables in `cloudbuild.yaml` or via command line (see step 4).

### 4. Deploy Using Cloud Build

#### Method 1: Using Cloud Build with Substitutions

```bash
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions=_REGION=us-central1,\
_WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id,\
_WHATSAPP_ACCESS_TOKEN=your_access_token,\
_WEBHOOK_VERIFY_TOKEN=your_verify_token,\
_MONGODB_URI=your_mongodb_uri,\
_MONGODB_DB_NAME=hiker_db
```

#### Method 2: Using gcloud run deploy directly

```bash
# Build and push image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/hiker-bot

# Deploy to Cloud Run
gcloud run deploy hiker-bot \
  --image gcr.io/YOUR_PROJECT_ID/hiker-bot \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 300 \
  --set-env-vars "WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id,WHATSAPP_ACCESS_TOKEN=your_access_token,WEBHOOK_VERIFY_TOKEN=your_verify_token,MONGODB_URI=your_mongodb_uri,MONGODB_DB_NAME=hiker_db,FLASK_DEBUG=false"
```

### 5. Set Up Cloud Build Trigger (Optional)

For automatic deployments on git push:

**📖 See detailed guide**: [docs/GITHUB_CLOUD_BUILD_SETUP.md](GITHUB_CLOUD_BUILD_SETUP.md)

**Quick setup using script**:
```bash
./scripts/setup_github_cloud_build.sh [project_id] [region] [github_owner] [repo_name] [branch]
```

**Manual setup**:
1. Go to Cloud Build > Triggers in Google Cloud Console
2. Click "Create Trigger"
3. Connect your repository (GitHub, Cloud Source Repositories, etc.)
4. Configure:
   - **Name**: `deploy-hiker-bot`
   - **Event**: Push to branch (e.g., `main`)
   - **Configuration**: Cloud Build configuration file
   - **Location**: `cloudbuild.yaml`
   - **Substitution variables**: Set your environment variables

### 6. Get Your Cloud Run URL

After deployment, get your service URL:

```bash
gcloud run services describe hiker-bot --region us-central1 --format 'value(status.url)'
```

The URL will look like: `https://hiker-bot-xxxxx-uc.a.run.app`

### 7. Configure WhatsApp Webhook

Update your WhatsApp Cloud API webhook URL to point to your Cloud Run service:

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Navigate to your WhatsApp app
3. Go to Configuration > Webhook
4. Set Callback URL to: `https://YOUR_SERVICE_URL/webhook`
5. Set Verify Token to match your `WEBHOOK_VERIFY_TOKEN`

## 🧪 Testing Locally with Docker

Before deploying, test locally:

```bash
# Build Docker image
docker build -t hiker-bot .

# Run container locally
docker run -p 8080:8080 \
  -e WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id \
  -e WHATSAPP_ACCESS_TOKEN=your_access_token \
  -e WEBHOOK_VERIFY_TOKEN=your_verify_token \
  -e MONGODB_URI=your_mongodb_uri \
  -e MONGODB_DB_NAME=hiker_db \
  -e FLASK_DEBUG=false \
  hiker-bot

# Test health endpoint
curl http://localhost:8080/health
```

## 📊 Monitoring and Logs

### View Logs

```bash
# View logs in terminal
gcloud run services logs read hiker-bot --region us-central1

# Or view in Cloud Console
# Go to Cloud Run > hiker-bot > Logs
```

### Monitor Metrics

- Go to Cloud Run > hiker-bot > Metrics
- View request count, latency, error rate, etc.

## 🔄 Updating the Service

### Update Environment Variables

```bash
gcloud run services update hiker-bot \
  --region us-central1 \
  --update-env-vars "MONGODB_URI=new_uri"
```

### Redeploy with New Code

```bash
# Rebuild and redeploy
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/hiker-bot
gcloud run deploy hiker-bot \
  --image gcr.io/YOUR_PROJECT_ID/hiker-bot \
  --region us-central1
```

## 🔒 Security Best Practices

1. **Use Secret Manager** for sensitive credentials (recommended)
2. **Enable VPC Connector** if MongoDB is in a private network
3. **Set up IAM** roles properly
4. **Enable Cloud Armor** for DDoS protection (optional)
5. **Use HTTPS only** (enabled by default in Cloud Run)

## 💰 Cost Optimization

- **Min instances**: Set to 0 to scale to zero when idle
- **Max instances**: Adjust based on expected load
- **Memory**: Start with 512Mi, increase if needed
- **CPU**: Start with 1, increase for better performance

## 🐛 Troubleshooting

### Service won't start

```bash
# Check logs
gcloud run services logs read hiker-bot --region us-central1 --limit 50

# Check service status
gcloud run services describe hiker-bot --region us-central1
```

### Connection to MongoDB fails

- Ensure MongoDB allows connections from Cloud Run IPs
- For MongoDB Atlas, add `0.0.0.0/0` to IP whitelist (or use VPC peering)
- Check MongoDB URI format: `mongodb+srv://user:pass@cluster.mongodb.net/dbname`

### Webhook verification fails

- Verify `WEBHOOK_VERIFY_TOKEN` matches in Cloud Run and Meta Console
- Check that webhook URL is correct and accessible
- Ensure Cloud Run service allows unauthenticated requests

## 📚 Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)

## ✅ Deployment Checklist

- [ ] Google Cloud project created and billing enabled
- [ ] Required APIs enabled
- [ ] Docker image builds successfully
- [ ] Environment variables configured
- [ ] MongoDB accessible from Cloud Run
- [ ] Service deployed and healthy
- [ ] Webhook URL updated in Meta Console
- [ ] Health endpoint responding (`/health`)
- [ ] Test message sent successfully

---

**Need help?** Check the logs or open an issue in the repository.

