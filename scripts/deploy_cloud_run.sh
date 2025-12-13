#!/bin/bash

# Google Cloud Run Deployment Script for Hiker Bot
# Usage: ./scripts/deploy_cloud_run.sh [region] [project_id]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGION=${1:-us-central1}
PROJECT_ID=${2:-$(gcloud config get-value project 2>/dev/null)}

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: Project ID not set. Please provide it as second argument or set default with 'gcloud config set project YOUR_PROJECT_ID'${NC}"
    exit 1
fi

echo -e "${GREEN}🚀 Deploying Hiker Bot to Google Cloud Run${NC}"
echo -e "Project: ${YELLOW}$PROJECT_ID${NC}"
echo -e "Region: ${YELLOW}$REGION${NC}"
echo ""

# Check if required environment variables are set
if [ -z "$WHATSAPP_PHONE_NUMBER_ID" ] || [ -z "$WHATSAPP_ACCESS_TOKEN" ] || [ -z "$WEBHOOK_VERIFY_TOKEN" ] || [ -z "$MONGODB_URI" ]; then
    echo -e "${YELLOW}⚠️  Warning: Some environment variables are not set${NC}"
    echo "Required variables:"
    echo "  - WHATSAPP_PHONE_NUMBER_ID"
    echo "  - WHATSAPP_ACCESS_TOKEN"
    echo "  - WEBHOOK_VERIFY_TOKEN"
    echo "  - MONGODB_URI"
    echo ""
    echo "You can set them in your shell or use Secret Manager (recommended for production)"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Enable required APIs
echo -e "${GREEN}📦 Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com --project=$PROJECT_ID 2>/dev/null || true
gcloud services enable run.googleapis.com --project=$PROJECT_ID 2>/dev/null || true
gcloud services enable containerregistry.googleapis.com --project=$PROJECT_ID 2>/dev/null || true

# Build and push Docker image
echo -e "${GREEN}🔨 Building Docker image...${NC}"
IMAGE_NAME="gcr.io/$PROJECT_ID/hiker-bot"
gcloud builds submit --tag $IMAGE_NAME --project=$PROJECT_ID

# Prepare environment variables
ENV_VARS="FLASK_DEBUG=false"
if [ ! -z "$WHATSAPP_PHONE_NUMBER_ID" ]; then
    ENV_VARS="$ENV_VARS,WHATSAPP_PHONE_NUMBER_ID=$WHATSAPP_PHONE_NUMBER_ID"
fi
if [ ! -z "$WHATSAPP_ACCESS_TOKEN" ]; then
    ENV_VARS="$ENV_VARS,WHATSAPP_ACCESS_TOKEN=$WHATSAPP_ACCESS_TOKEN"
fi
if [ ! -z "$WEBHOOK_VERIFY_TOKEN" ]; then
    ENV_VARS="$ENV_VARS,WEBHOOK_VERIFY_TOKEN=$WEBHOOK_VERIFY_TOKEN"
fi
if [ ! -z "$MONGODB_URI" ]; then
    ENV_VARS="$ENV_VARS,MONGODB_URI=$MONGODB_URI"
fi
if [ ! -z "$MONGODB_DB_NAME" ]; then
    ENV_VARS="$ENV_VARS,MONGODB_DB_NAME=$MONGODB_DB_NAME"
else
    ENV_VARS="$ENV_VARS,MONGODB_DB_NAME=hiker_db"
fi

# Deploy to Cloud Run
echo -e "${GREEN}🚀 Deploying to Cloud Run...${NC}"
gcloud run deploy hiker-bot \
    --image $IMAGE_NAME \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 300 \
    --set-env-vars "$ENV_VARS" \
    --project=$PROJECT_ID

# Get service URL
SERVICE_URL=$(gcloud run services describe hiker-bot --region $REGION --format 'value(status.url)' --project=$PROJECT_ID)

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo -e "Service URL: ${YELLOW}$SERVICE_URL${NC}"
echo -e "Webhook URL: ${YELLOW}$SERVICE_URL/webhook${NC}"
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Update your WhatsApp webhook URL in Meta Developer Console:"
echo "   $SERVICE_URL/webhook"
echo ""
echo "2. Test the health endpoint:"
echo "   curl $SERVICE_URL/health"
echo ""
echo "3. View logs:"
echo "   gcloud run services logs read hiker-bot --region $REGION --project=$PROJECT_ID"
echo ""

