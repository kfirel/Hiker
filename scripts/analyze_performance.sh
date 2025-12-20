#!/bin/bash

# Performance Analysis Script
# Extracts and analyzes performance metrics from Cloud Run logs

echo "📊 Performance Analysis"
echo "======================"
echo ""

PROJECT_ID="neat-mechanic-481119-c1"
SERVICE_NAME="hiker"
REGION="europe-west1"
LIMIT=100

echo "Fetching performance logs..."
echo ""

# Function to extract average from logs
extract_average() {
    local pattern=$1
    local metric_name=$2
    
    echo "Analyzing: $metric_name"
    echo "-----------------------------------"
    
    # Get logs and extract timing values
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME AND textPayload=~'$pattern'" \
        --limit $LIMIT \
        --project $PROJECT_ID \
        --format json 2>/dev/null | \
        jq -r '.[] | select(.textPayload != null) | .textPayload' | \
        grep -oP 'took \K[0-9.]+' | \
        awk '{
            sum+=$1
            count++
            if ($1 > max || max == 0) max=$1
            if ($1 < min || min == 0) min=$1
        } END {
            if (count > 0) {
                print "  Count: " count
                print "  Average: " (sum/count) "s"
                print "  Min: " min "s"
                print "  Max: " max "s"
            } else {
                print "  No data found"
            }
        }'
    echo ""
}

# Function to extract end-to-end latency
extract_e2e() {
    echo "Analyzing: End-to-End Latency"
    echo "-----------------------------------"
    
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME AND textPayload=~'End-to-end latency'" \
        --limit $LIMIT \
        --project $PROJECT_ID \
        --format json 2>/dev/null | \
        jq -r '.[] | select(.textPayload != null) | .textPayload' | \
        grep -oP 'latency \(webhook→response\): \K[0-9.]+' | \
        awk '{
            sum+=$1
            count++
            if ($1 > max || max == 0) max=$1
            if ($1 < min || min == 0) min=$1
        } END {
            if (count > 0) {
                print "  Count: " count
                print "  Average: " (sum/count) "s"
                print "  Min: " min "s"
                print "  Max: " max "s"
            } else {
                print "  No data found"
            }
        }'
    echo ""
}

# Analyze different metrics
extract_average "webhook_total_response" "Webhook Response Time"
extract_average "conversation_engine_process" "Conversation Engine Processing"
extract_average "whatsapp_api_request" "WhatsApp API Call Time"
extract_average "total_message_processing" "Total Message Processing"
extract_e2e

echo "✅ Analysis complete!"
echo ""
echo "💡 Tip: Check Cloud Run Metrics dashboard for more details:"
echo "https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/metrics?project=$PROJECT_ID"

