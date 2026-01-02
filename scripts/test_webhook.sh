#!/bin/bash

# Webhook Testing Script
# Tests if your deployed webhook is working correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Testing WhatsApp Webhook Configuration"
echo "=========================================="
echo ""

# Get service URL from Cloud Run
echo "📡 Fetching Cloud Run service URL..."
SERVICE_URL=$(gcloud run services describe hitchhiking-bot \
  --platform managed \
  --region us-central1 \
  --format 'value(status.url)' 2>/dev/null)

if [ -z "$SERVICE_URL" ]; then
    echo -e "${RED}❌ Could not find Cloud Run service 'hitchhiking-bot'${NC}"
    echo "Make sure the service is deployed first."
    exit 1
fi

echo -e "${GREEN}✅ Service URL: $SERVICE_URL${NC}"
echo ""

# Test 1: Check if service is accessible
echo "🧪 Test 1: Checking if service is accessible..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $SERVICE_URL)
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Service is accessible (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${RED}❌ Service returned HTTP $HTTP_CODE${NC}"
fi
echo ""

# Test 2: Check webhook endpoint without parameters
echo "🧪 Test 2: Testing webhook endpoint (should fail without params)..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $SERVICE_URL/webhook)
if [ "$HTTP_CODE" = "403" ] || [ "$HTTP_CODE" = "422" ]; then
    echo -e "${GREEN}✅ Webhook endpoint exists (HTTP $HTTP_CODE - expected)${NC}"
else
    echo -e "${YELLOW}⚠️  Unexpected response: HTTP $HTTP_CODE${NC}"
fi
echo ""

# Test 3: Check with correct parameters
echo "🧪 Test 3: Testing webhook verification..."
if [ -z "$VERIFY_TOKEN" ]; then
    echo -e "${RED}❌ VERIFY_TOKEN not set. Please export it:${NC}"
    echo "   export VERIFY_TOKEN='your_verify_token_here'"
    exit 1
fi

CHALLENGE="test_challenge_12345"
RESPONSE=$(curl -s "$SERVICE_URL/webhook?hub.mode=subscribe&hub.verify_token=$VERIFY_TOKEN&hub.challenge=$CHALLENGE")

if [ "$RESPONSE" = "$CHALLENGE" ]; then
    echo -e "${GREEN}✅ Webhook verification works! Response: $RESPONSE${NC}"
else
    echo -e "${RED}❌ Webhook verification failed!${NC}"
    echo "   Expected: $CHALLENGE"
    echo "   Got: $RESPONSE"
    echo ""
    echo "Possible issues:"
    echo "   1. VERIFY_TOKEN mismatch (check environment variables)"
    echo "   2. Service not deployed correctly"
    echo "   3. Check logs: gcloud run logs read --service=hitchhiking-bot --region=us-central1 --limit=20"
fi
echo ""

# Test 4: Test with wrong token (should fail)
echo "🧪 Test 4: Testing with wrong token (should fail)..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/webhook?hub.mode=subscribe&hub.verify_token=WRONG_TOKEN&hub.challenge=$CHALLENGE")
if [ "$HTTP_CODE" = "403" ]; then
    echo -e "${GREEN}✅ Correctly rejects wrong token (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${YELLOW}⚠️  Unexpected response: HTTP $HTTP_CODE (expected 403)${NC}"
fi
echo ""

# Summary
echo "=========================================="
echo "📋 Summary:"
echo ""
echo "Webhook URL for Meta:"
echo -e "${GREEN}$SERVICE_URL/webhook${NC}"
echo ""
echo "Verify Token:"
echo -e "${GREEN}$VERIFY_TOKEN${NC}"
echo ""
echo "=========================================="
echo ""
echo "📝 To configure in Meta Developer Console:"
echo "1. Go to: https://developers.facebook.com/apps/"
echo "2. Select your app → WhatsApp → Configuration"
echo "3. Edit webhook:"
echo "   - Callback URL: $SERVICE_URL/webhook"
echo "   - Verify Token: $VERIFY_TOKEN"
echo "4. Subscribe to 'messages' field"
echo ""
echo "🔍 If verification still fails, check logs:"
echo "   gcloud run logs read --service=hitchhiking-bot --region=us-central1 --limit=50"
echo ""



