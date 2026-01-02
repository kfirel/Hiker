#!/bin/bash
# Deploy script for Hiker application to Google Cloud Run

set -e  # Exit on error

echo "🚀 Starting deployment process..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"neat-mechanic-481119-c1"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME="hitchhiking-bot"

echo -e "${BLUE}📋 Configuration:${NC}"
echo "   Project ID: $PROJECT_ID"
echo "   Region: $REGION"
echo "   Service: $SERVICE_NAME"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Error: gcloud CLI is not installed${NC}"
    echo ""
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not logged in to gcloud. Running authentication...${NC}"
    gcloud auth login
fi

# Set project
echo -e "${YELLOW}🔧 Setting project...${NC}"
gcloud config set project $PROJECT_ID

echo -e "${YELLOW}📦 Building and deploying with Cloud Build...${NC}"
echo "   (This will build the React frontend automatically inside Docker)"
echo ""

# Build with Cloud Build (includes frontend build automatically via Dockerfile)
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

echo ""
echo -e "${YELLOW}🚢 Deploying to Cloud Run...${NC}"

# Get ADMIN_TOKEN from .env if exists
ADMIN_TOKEN=$(grep "^ADMIN_TOKEN=" .env 2>/dev/null | cut -d '=' -f2 || echo "")
ENV_VARS="GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
if [ ! -z "$ADMIN_TOKEN" ]; then
    ENV_VARS="$ENV_VARS,ADMIN_TOKEN=$ADMIN_TOKEN"
    echo "   ✅ Using ADMIN_TOKEN from .env"
fi

gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="$ENV_VARS" \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300s \
  --max-instances 10 \
  --min-instances 0

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo -e "${BLUE}🌐 Service URLs:${NC}"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
echo "   Bot API: $SERVICE_URL"
echo "   Admin Dashboard: $SERVICE_URL/admin"
echo ""
echo -e "${BLUE}🔑 Admin Access:${NC}"
if [ ! -z "$ADMIN_TOKEN" ]; then
    echo "   Token: $ADMIN_TOKEN"
    echo "   Set in browser console: localStorage.setItem('admin_token', '$ADMIN_TOKEN');"
else
    echo "   ⚠️  No ADMIN_TOKEN found in .env"
    echo "   Add it to .env: ADMIN_TOKEN=your-secret-token"
fi
echo ""
echo -e "${GREEN}🎉 Done! Open the dashboard at: $SERVICE_URL/admin${NC}"
