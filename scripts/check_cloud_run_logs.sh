#!/bin/bash

# Script to check Cloud Run logs and diagnose startup issues

PROJECT_ID=${1:-neat-mechanic-481119-c1}
REGION=${2:-europe-west1}
SERVICE_NAME=${3:-hiker}

echo "📋 Checking Cloud Run logs for service: $SERVICE_NAME"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Get the latest revision
echo "🔍 Getting latest revision..."
LATEST_REVISION=$(gcloud run revisions list \
  --service=$SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(metadata.name)" \
  --limit=1)

if [ -z "$LATEST_REVISION" ]; then
    echo "❌ No revisions found for service $SERVICE_NAME"
    exit 1
fi

echo "Latest revision: $LATEST_REVISION"
echo ""

# Get logs
echo "📜 Fetching logs (last 100 lines)..."
echo "----------------------------------------"
gcloud run services logs read $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --limit=100

echo ""
echo "----------------------------------------"
echo ""
echo "💡 To view more logs:"
echo "  gcloud run services logs read $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --limit=200"
echo ""
echo "🌐 View in Console:"
echo "  https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/logs?project=$PROJECT_ID"

