# 🔗 GitHub to Google Cloud Build Integration Guide

This guide will help you connect your GitHub repository to Google Cloud Build, enabling automatic deployments to Cloud Run whenever you push code to GitHub.

## 📋 Prerequisites

1. **GitHub Repository** - Your code must be in a GitHub repository
2. **Google Cloud Project** - With billing enabled
3. **Google Cloud SDK** - Installed and configured
4. **Required APIs Enabled**:
   - Cloud Build API
   - Cloud Run API
   - Container Registry API

## 🚀 Setup Steps

### Method 1: Using Google Cloud Console (Recommended)

#### Step 1: Connect GitHub Repository

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **Cloud Build** > **Triggers**
3. Click **"Connect Repository"** or **"Create Trigger"**
4. Select **GitHub (Cloud Build GitHub App)** or **GitHub (Manually Connected)**
5. Authenticate with GitHub:
   - If using Cloud Build GitHub App: Click "Install Google Cloud Build" and authorize
   - If manually: You'll need to create a GitHub Personal Access Token

#### Step 2: Select Repository

1. Choose your GitHub account/organization
2. Select the repository (e.g., `your-username/Hiker`)
3. Click **"Connect"**

#### Step 3: Create Build Trigger

1. Click **"Create Trigger"**
2. Configure the trigger:
   - **Name**: `deploy-hiker-bot`
   - **Event**: `Push to a branch`
   - **Branch**: `^main$` (or your main branch name)
   - **Configuration**: `Cloud Build configuration file`
   - **Location**: `cloudbuild.yaml`
   - **Cloud Build configuration file location**: `cloudbuild.yaml`

#### Step 4: Set Substitution Variables

In the trigger configuration, add substitution variables:

```
_REGION=us-central1
_WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
_WHATSAPP_ACCESS_TOKEN=your_access_token
_WEBHOOK_VERIFY_TOKEN=your_verify_token
_MONGODB_URI=your_mongodb_uri
_MONGODB_DB_NAME=hiker_db
```

**⚠️ Security Note**: For production, use **Secret Manager** instead of substitution variables (see Method 2).

#### Step 5: Save and Test

1. Click **"Create"**
2. Push a commit to your `main` branch
3. Check Cloud Build > History to see the build start automatically

### Method 2: Using Secret Manager (More Secure)

For sensitive credentials, use Google Secret Manager:

#### Step 1: Create Secrets

```bash
# Create secrets
echo -n "your_whatsapp_phone_number_id" | gcloud secrets create whatsapp-phone-number-id --data-file=-
echo -n "your_whatsapp_access_token" | gcloud secrets create whatsapp-access-token --data-file=-
echo -n "your_webhook_verify_token" | gcloud secrets create webhook-verify-token --data-file=-
echo -n "your_mongodb_uri" | gcloud secrets create mongodb-uri --data-file=-
```

#### Step 2: Grant Cloud Build Access

```bash
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")

gcloud secrets add-iam-policy-binding whatsapp-phone-number-id \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding whatsapp-access-token \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding webhook-verify-token \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding mongodb-uri \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

#### Step 3: Update cloudbuild.yaml

Update the deploy step to use secrets:

```yaml
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  entrypoint: gcloud
  args:
    - 'run'
    - 'deploy'
    - 'hiker-bot'
    # ... other args ...
    - '--update-secrets'
    - 'WHATSAPP_PHONE_NUMBER_ID=whatsapp-phone-number-id:latest,WHATSAPP_ACCESS_TOKEN=whatsapp-access-token:latest,WEBHOOK_VERIFY_TOKEN=webhook-verify-token:latest,MONGODB_URI=mongodb-uri:latest'
```

### Method 3: Using Command Line (gcloud)

```bash
# Set variables
PROJECT_ID=your-project-id
REGION=us-central1
REPO_NAME=your-username/Hiker
BRANCH=main

# Create trigger
gcloud builds triggers create github \
  --name="deploy-hiker-bot" \
  --repo-name="$REPO_NAME" \
  --repo-owner="your-username" \
  --branch-pattern="^${BRANCH}$" \
  --build-config="cloudbuild.yaml" \
  --substitutions="_REGION=$REGION,_WHATSAPP_PHONE_NUMBER_ID=your_id,_WHATSAPP_ACCESS_TOKEN=your_token,_WEBHOOK_VERIFY_TOKEN=your_token,_MONGODB_URI=your_uri,_MONGODB_DB_NAME=hiker_db" \
  --project=$PROJECT_ID
```

## 🔄 How It Works

1. **Push to GitHub**: You push code to your `main` branch
2. **Webhook Triggered**: GitHub sends a webhook to Cloud Build
3. **Build Starts**: Cloud Build automatically starts a build
4. **Docker Image Built**: Your code is built into a Docker image
5. **Deployed to Cloud Run**: The new image is automatically deployed

## 📊 Monitoring Builds

### View Build History

```bash
# List recent builds
gcloud builds list --limit=10

# View specific build
gcloud builds describe BUILD_ID

# Stream logs
gcloud builds log BUILD_ID --stream
```

### In Cloud Console

1. Go to **Cloud Build** > **History**
2. See all builds, their status, and logs
3. Click on any build to see detailed logs

## 🔧 Troubleshooting

### Build Not Triggering

1. **Check Trigger Configuration**:
   - Verify branch pattern matches your branch name
   - Ensure `cloudbuild.yaml` exists in repository root
   - Check trigger is enabled

2. **Check GitHub Connection**:
   - Go to Cloud Build > Triggers
   - Verify repository shows as "Connected"
   - Re-authenticate if needed

3. **Check Build Logs**:
   ```bash
   gcloud builds list --limit=5
   ```

### Build Fails

1. **Check Build Logs**:
   ```bash
   gcloud builds log BUILD_ID
   ```

2. **Common Issues**:
   - Missing environment variables
   - Docker build errors
   - Permission issues
   - Invalid substitution variables

### Secret Manager Issues

If using Secret Manager and builds fail:

```bash
# Verify secrets exist
gcloud secrets list

# Check IAM permissions
gcloud projects get-iam-policy $(gcloud config get-value project) \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:*@cloudbuild.gserviceaccount.com"
```

## 🔒 Security Best Practices

1. **Use Secret Manager** for sensitive credentials (not substitution variables)
2. **Limit Branch Access**: Only trigger on `main` or `production` branches
3. **Review Build Logs**: Regularly check for exposed secrets
4. **Use Service Accounts**: Don't use your personal account for builds
5. **Enable Audit Logs**: Track who triggered builds

## 🎯 Advanced Configuration

### Multiple Environments

Create separate triggers for different environments:

- `deploy-hiker-bot-staging` → triggers on `develop` branch → deploys to `hiker-bot-staging`
- `deploy-hiker-bot-prod` → triggers on `main` branch → deploys to `hiker-bot`

### Conditional Deployments

Modify `cloudbuild.yaml` to add conditions:

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', '...']
    id: 'build'
  
  # Only deploy if build succeeded
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args: ['run', 'deploy', ...]
    waitFor: ['build']
```

### Build Notifications

Set up notifications for build status:

1. Go to Cloud Build > Settings
2. Configure Pub/Sub notifications
3. Set up Cloud Functions to send emails/Slack messages

## ✅ Verification Checklist

- [ ] GitHub repository connected to Cloud Build
- [ ] Build trigger created and enabled
- [ ] Substitution variables set (or secrets configured)
- [ ] Test push triggers a build
- [ ] Build completes successfully
- [ ] Cloud Run service updated with new image
- [ ] Health endpoint responds: `curl https://YOUR_SERVICE_URL/health`

## 📚 Additional Resources

- [Cloud Build Triggers Documentation](https://cloud.google.com/build/docs/triggers)
- [GitHub App Integration](https://cloud.google.com/build/docs/automating-builds/create-github-app-triggers)
- [Secret Manager with Cloud Build](https://cloud.google.com/build/docs/securing-builds/use-secrets)

---

**Need help?** Check the build logs or open an issue in your repository.

