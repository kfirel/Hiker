#!/bin/bash

# Deployment script for Gvar'am Hitchhiking Bot
# Usage: ./deploy.sh

set -e

echo "🚀 Deploying Gvar'am Hitchhiking Bot to Google Cloud Run"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first:"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📦 Project: $PROJECT_ID"

# Check for required environment variables
if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ GEMINI_API_KEY not set. Please export it first."
    exit 1
fi

if [ -z "$WHATSAPP_TOKEN" ]; then
    echo "❌ WHATSAPP_TOKEN not set. Please export it first."
    exit 1
fi

if [ -z "$WHATSAPP_PHONE_NUMBER_ID" ]; then
    echo "❌ WHATSAPP_PHONE_NUMBER_ID not set. Please export it first."
    exit 1
fi

if [ -z "$VERIFY_TOKEN" ]; then
    echo "❌ VERIFY_TOKEN not set. Please export it first."
    exit 1
fi

# Build container
echo "🔨 Building container image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/hitchhiking-bot

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy hitchhiking-bot \
  --image gcr.io/$PROJECT_ID/hitchhiking-bot \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY \
  --set-env-vars WHATSAPP_TOKEN=$WHATSAPP_TOKEN \
  --set-env-vars WHATSAPP_PHONE_NUMBER_ID=$WHATSAPP_PHONE_NUMBER_ID \
  --set-env-vars VERIFY_TOKEN=$VERIFY_TOKEN \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60 \
  --max-instances 10

# Get the service URL
SERVICE_URL=$(gcloud run services describe hitchhiking-bot --platform managed --region us-central1 --format 'value(status.url)')

echo ""
echo "✅ Deployment successful!"
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "📝 Next steps:"
echo "1. Configure WhatsApp webhook: $SERVICE_URL/webhook"
echo "2. Use VERIFY_TOKEN: $VERIFY_TOKEN"
echo "3. Subscribe to 'messages' webhook field"
echo ""




