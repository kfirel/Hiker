#!/bin/bash

# Test Cloud Run Logging Script
# Verifies that logs are appearing in Cloud Console

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Testing Cloud Run Logs"
echo "=========================="
echo ""

# Configuration
SERVICE_NAME="hiker"
REGION="europe-west1"

# 1. Check if service exists
echo "📡 Step 1: Checking if service exists..."
if gcloud run services describe $SERVICE_NAME --region=$REGION &>/dev/null; then
    echo -e "${GREEN}✅ Service '$SERVICE_NAME' found in region '$REGION'${NC}"
else
    echo -e "${RED}❌ Service '$SERVICE_NAME' not found in region '$REGION'${NC}"
    echo ""
    echo "Available services:"
    gcloud run services list
    exit 1
fi
echo ""

# 2. Get service URL
echo "🌐 Step 2: Getting service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --format='value(status.url)')
echo -e "${GREEN}Service URL: $SERVICE_URL${NC}"
echo ""

# 3. Send test request
echo "📤 Step 3: Sending test request to generate logs..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $SERVICE_URL)
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Request successful (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${YELLOW}⚠️  Request returned HTTP $HTTP_CODE${NC}"
fi
echo ""

# 4. Wait for logs
echo "⏳ Step 4: Waiting 10 seconds for logs to propagate..."
sleep 10
echo ""

# 5. Fetch recent logs
echo "📋 Step 5: Fetching recent logs..."
echo "=================================="
echo ""

LOGS=$(gcloud run services logs read $SERVICE_NAME \
    --region=$REGION \
    --limit=20 \
    --format="table(timestamp.date('%Y-%m-%d %H:%M:%S'), severity, textPayload)" \
    2>&1)

if [ $? -eq 0 ] && [ ! -z "$LOGS" ]; then
    echo "$LOGS"
    echo ""
    echo -e "${GREEN}✅ Logs are visible!${NC}"
else
    echo -e "${RED}❌ No logs found${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check service name: $SERVICE_NAME"
    echo "2. Check region: $REGION"
    echo "3. Try web console: https://console.cloud.google.com/run"
fi
echo ""

# 6. Show JSON logs
echo "📊 Step 6: Showing structured (JSON) logs..."
echo "==========================================="
echo ""

gcloud run services logs read $SERVICE_NAME \
    --region=$REGION \
    --limit=5 \
    --format=json | jq -r '.[] | "\(.timestamp) [\(.severity)] \(.textPayload // .jsonPayload.message)"' 2>/dev/null || \
    echo "Install 'jq' to see formatted JSON: brew install jq"

echo ""

# Summary
echo "=================================="
echo "📝 Summary:"
echo ""
echo "Service: $SERVICE_NAME"
echo "Region: $REGION"
echo "URL: $SERVICE_URL"
echo ""
echo "To view logs in real-time:"
echo -e "${YELLOW}gcloud run services logs tail $SERVICE_NAME --region=$REGION${NC}"
echo ""
echo "To view in web console:"
echo -e "${YELLOW}https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/logs${NC}"
echo ""



