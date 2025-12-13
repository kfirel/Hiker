#!/bin/bash

# Script to set up GitHub to Google Cloud Build integration
# Usage: ./scripts/setup_github_cloud_build.sh [project_id] [region] [github_owner] [repo_name] [branch]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔗 GitHub to Google Cloud Build Setup${NC}"
echo ""

# Configuration
PROJECT_ID=${1:-$(gcloud config get-value project 2>/dev/null)}
REGION=${2:-us-central1}
GITHUB_OWNER=${3:-""}
REPO_NAME=${4:-""}
BRANCH=${5:-main}

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: Project ID not set.${NC}"
    echo "Usage: $0 [project_id] [region] [github_owner] [repo_name] [branch]"
    echo "Or set default: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo -e "${GREEN}Project:${NC} $PROJECT_ID"
echo -e "${GREEN}Region:${NC} $REGION"
echo ""

# Get GitHub details if not provided
if [ -z "$GITHUB_OWNER" ]; then
    echo -e "${YELLOW}Enter your GitHub username or organization:${NC}"
    read -p "> " GITHUB_OWNER
fi

if [ -z "$REPO_NAME" ]; then
    echo -e "${YELLOW}Enter repository name (default: Hiker):${NC}"
    read -p "> " REPO_NAME
    REPO_NAME=${REPO_NAME:-Hiker}
fi

FULL_REPO_NAME="$GITHUB_OWNER/$REPO_NAME"

echo ""
echo -e "${BLUE}📋 Configuration Summary:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  GitHub Repo: $FULL_REPO_NAME"
echo "  Branch: $BRANCH"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

# Enable required APIs
echo ""
echo -e "${GREEN}📦 Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com --project=$PROJECT_ID 2>/dev/null || true
gcloud services enable run.googleapis.com --project=$PROJECT_ID 2>/dev/null || true
gcloud services enable containerregistry.googleapis.com --project=$PROJECT_ID 2>/dev/null || true
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID 2>/dev/null || true

# Check if cloudbuild.yaml exists
if [ ! -f "cloudbuild.yaml" ]; then
    echo -e "${RED}Error: cloudbuild.yaml not found in current directory${NC}"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Ask about environment variables
echo ""
echo -e "${YELLOW}How do you want to handle environment variables?${NC}"
echo "1) Use substitution variables (simpler, less secure)"
echo "2) Use Secret Manager (recommended for production)"
read -p "Choose (1 or 2): " VAR_METHOD

if [ "$VAR_METHOD" == "2" ]; then
    echo ""
    echo -e "${GREEN}Setting up Secret Manager...${NC}"
    
    # Check if secrets already exist
    echo -e "${YELLOW}Enter your WhatsApp Phone Number ID:${NC}"
    read -s WHATSAPP_PHONE_NUMBER_ID
    echo ""
    
    echo -e "${YELLOW}Enter your WhatsApp Access Token:${NC}"
    read -s WHATSAPP_ACCESS_TOKEN
    echo ""
    
    echo -e "${YELLOW}Enter your Webhook Verify Token:${NC}"
    read -s WEBHOOK_VERIFY_TOKEN
    echo ""
    
    echo -e "${YELLOW}Enter your MongoDB URI:${NC}"
    read -s MONGODB_URI
    echo ""
    
    # Create secrets
    echo -e "${GREEN}Creating secrets...${NC}"
    echo -n "$WHATSAPP_PHONE_NUMBER_ID" | gcloud secrets create whatsapp-phone-number-id --data-file=- --project=$PROJECT_ID 2>/dev/null || \
        echo -n "$WHATSAPP_PHONE_NUMBER_ID" | gcloud secrets versions add whatsapp-phone-number-id --data-file=- --project=$PROJECT_ID
    
    echo -n "$WHATSAPP_ACCESS_TOKEN" | gcloud secrets create whatsapp-access-token --data-file=- --project=$PROJECT_ID 2>/dev/null || \
        echo -n "$WHATSAPP_ACCESS_TOKEN" | gcloud secrets versions add whatsapp-access-token --data-file=- --project=$PROJECT_ID
    
    echo -n "$WEBHOOK_VERIFY_TOKEN" | gcloud secrets create webhook-verify-token --data-file=- --project=$PROJECT_ID 2>/dev/null || \
        echo -n "$WEBHOOK_VERIFY_TOKEN" | gcloud secrets versions add webhook-verify-token --data-file=- --project=$PROJECT_ID
    
    echo -n "$MONGODB_URI" | gcloud secrets create mongodb-uri --data-file=- --project=$PROJECT_ID 2>/dev/null || \
        echo -n "$MONGODB_URI" | gcloud secrets versions add mongodb-uri --data-file=- --project=$PROJECT_ID
    
    # Grant Cloud Build access
    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
    
    echo -e "${GREEN}Granting Cloud Build access to secrets...${NC}"
    gcloud secrets add-iam-policy-binding whatsapp-phone-number-id \
        --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor" \
        --project=$PROJECT_ID 2>/dev/null || true
    
    gcloud secrets add-iam-policy-binding whatsapp-access-token \
        --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor" \
        --project=$PROJECT_ID 2>/dev/null || true
    
    gcloud secrets add-iam-policy-binding webhook-verify-token \
        --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor" \
        --project=$PROJECT_ID 2>/dev/null || true
    
    gcloud secrets add-iam-policy-binding mongodb-uri \
        --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor" \
        --project=$PROJECT_ID 2>/dev/null || true
    
    echo -e "${GREEN}✅ Secrets configured!${NC}"
    echo -e "${YELLOW}Note: You'll need to update cloudbuild.yaml to use secrets.${NC}"
    echo "See docs/GITHUB_CLOUD_BUILD_SETUP.md for details."
    
    SUBSTITUTIONS="_REGION=$REGION"
else
    echo ""
    echo -e "${YELLOW}Enter environment variables (press Enter to skip):${NC}"
    
    echo -n "WhatsApp Phone Number ID: "
    read WHATSAPP_PHONE_NUMBER_ID
    
    echo -n "WhatsApp Access Token: "
    read WHATSAPP_ACCESS_TOKEN
    
    echo -n "Webhook Verify Token: "
    read WEBHOOK_VERIFY_TOKEN
    
    echo -n "MongoDB URI: "
    read MONGODB_URI
    
    MONGODB_DB_NAME=${MONGODB_DB_NAME:-hiker_db}
    
    SUBSTITUTIONS="_REGION=$REGION"
    [ ! -z "$WHATSAPP_PHONE_NUMBER_ID" ] && SUBSTITUTIONS="$SUBSTITUTIONS,_WHATSAPP_PHONE_NUMBER_ID=$WHATSAPP_PHONE_NUMBER_ID"
    [ ! -z "$WHATSAPP_ACCESS_TOKEN" ] && SUBSTITUTIONS="$SUBSTITUTIONS,_WHATSAPP_ACCESS_TOKEN=$WHATSAPP_ACCESS_TOKEN"
    [ ! -z "$WEBHOOK_VERIFY_TOKEN" ] && SUBSTITUTIONS="$SUBSTITUTIONS,_WEBHOOK_VERIFY_TOKEN=$WEBHOOK_VERIFY_TOKEN"
    [ ! -z "$MONGODB_URI" ] && SUBSTITUTIONS="$SUBSTITUTIONS,_MONGODB_URI=$MONGODB_URI"
    SUBSTITUTIONS="$SUBSTITUTIONS,_MONGODB_DB_NAME=$MONGODB_DB_NAME"
fi

# Create trigger
echo ""
echo -e "${GREEN}🔗 Creating Cloud Build trigger...${NC}"

TRIGGER_NAME="deploy-hiker-bot"

# Check if trigger already exists
if gcloud builds triggers describe $TRIGGER_NAME --project=$PROJECT_ID >/dev/null 2>&1; then
    echo -e "${YELLOW}Trigger '$TRIGGER_NAME' already exists.${NC}"
    read -p "Delete and recreate? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        gcloud builds triggers delete $TRIGGER_NAME --project=$PROJECT_ID --quiet
    else
        echo -e "${YELLOW}Cancelled.${NC}"
        exit 0
    fi
fi

# Create the trigger
if [ "$VAR_METHOD" == "2" ]; then
    # With secrets - note: user needs to update cloudbuild.yaml manually
    echo -e "${YELLOW}Creating trigger (you'll need to update cloudbuild.yaml to use secrets)...${NC}"
    gcloud builds triggers create github \
        --name="$TRIGGER_NAME" \
        --repo-name="$REPO_NAME" \
        --repo-owner="$GITHUB_OWNER" \
        --branch-pattern="^${BRANCH}$" \
        --build-config="cloudbuild.yaml" \
        --substitutions="$SUBSTITUTIONS" \
        --project=$PROJECT_ID
else
    # With substitution variables
    gcloud builds triggers create github \
        --name="$TRIGGER_NAME" \
        --repo-name="$REPO_NAME" \
        --repo-owner="$GITHUB_OWNER" \
        --branch-pattern="^${BRANCH}$" \
        --build-config="cloudbuild.yaml" \
        --substitutions="$SUBSTITUTIONS" \
        --project=$PROJECT_ID
fi

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Trigger created successfully!${NC}"
    echo ""
    echo -e "${BLUE}📝 Next steps:${NC}"
    echo "1. Make sure your GitHub repository is connected to Cloud Build"
    echo "2. Push a commit to the '$BRANCH' branch to test"
    echo "3. Check Cloud Build > History to see the build"
    echo ""
    echo -e "${YELLOW}View triggers:${NC}"
    echo "  gcloud builds triggers list --project=$PROJECT_ID"
    echo ""
    echo -e "${YELLOW}View trigger details:${NC}"
    echo "  gcloud builds triggers describe $TRIGGER_NAME --project=$PROJECT_ID"
    echo ""
else
    echo -e "${RED}❌ Failed to create trigger${NC}"
    echo ""
    echo "Common issues:"
    echo "1. GitHub repository not connected - connect it in Cloud Console"
    echo "2. Missing permissions - check IAM roles"
    echo "3. Invalid repository name - verify format: owner/repo"
    exit 1
fi

