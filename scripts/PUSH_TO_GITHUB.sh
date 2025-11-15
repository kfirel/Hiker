#!/bin/bash

# 📤 Script to push Hiker project to GitHub
# Make sure you've created a repository on GitHub first!

# Color codes for pretty output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚗 Hiker - GitHub Upload Script${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo -e "${RED}❌ Error: Please run this script from the Hiker project root directory${NC}"
    exit 1
fi

# Get GitHub username
echo -e "${YELLOW}📝 Enter your GitHub username:${NC}"
read -p "> " GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo -e "${RED}❌ Username cannot be empty${NC}"
    exit 1
fi

# Confirm repository name
echo ""
echo -e "${YELLOW}📝 Repository name (default: Hiker):${NC}"
read -p "> " REPO_NAME
REPO_NAME=${REPO_NAME:-Hiker}

# Choose HTTPS or SSH
echo ""
echo -e "${YELLOW}🔐 Connection method:${NC}"
echo "1) HTTPS (recommended for first-time users)"
echo "2) SSH (if you have SSH keys configured)"
read -p "Choose (1 or 2): " CONNECTION_METHOD

if [ "$CONNECTION_METHOD" == "2" ]; then
    REMOTE_URL="git@github.com:${GITHUB_USERNAME}/${REPO_NAME}.git"
else
    REMOTE_URL="https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"
fi

# Summary
echo ""
echo -e "${BLUE}📋 Summary:${NC}"
echo "  Username: $GITHUB_USERNAME"
echo "  Repository: $REPO_NAME"
echo "  Remote URL: $REMOTE_URL"
echo ""
read -p "Is this correct? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo -e "${YELLOW}⚠️  Cancelled${NC}"
    exit 0
fi

# Check if remote already exists
if git remote get-url origin > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Remote 'origin' already exists. Removing...${NC}"
    git remote remove origin
fi

# Add remote
echo ""
echo -e "${BLUE}➕ Adding remote...${NC}"
git remote add origin "$REMOTE_URL"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to add remote${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Remote added successfully${NC}"

# Ensure we're on main branch
echo ""
echo -e "${BLUE}🔄 Setting branch to main...${NC}"
git branch -M main
echo -e "${GREEN}✅ Branch set to main${NC}"

# Push to GitHub
echo ""
echo -e "${BLUE}🚀 Pushing to GitHub...${NC}"
echo ""

git push -u origin main

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ Push failed${NC}"
    echo ""
    echo -e "${YELLOW}💡 Common solutions:${NC}"
    echo "1. Make sure you've created the repository on GitHub first"
    echo "   Visit: https://github.com/new"
    echo ""
    echo "2. If using HTTPS, you may need a Personal Access Token"
    echo "   Generate one at: https://github.com/settings/tokens"
    echo ""
    echo "3. If the repository is not empty, try:"
    echo "   git pull origin main --allow-unrelated-histories"
    echo "   git push -u origin main"
    exit 1
fi

# Success!
echo ""
echo -e "${GREEN}✅ ✅ ✅ Success! ✅ ✅ ✅${NC}"
echo ""
echo -e "${BLUE}🎉 Your project is now on GitHub!${NC}"
echo ""
echo "📍 Repository URL:"
echo "   https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Visit your repository on GitHub"
echo "2. Add topics/tags: whatsapp, bot, hitchhiking, israel, flask"
echo "3. Update README.md with your actual GitHub username"
echo "4. Star your own project! ⭐"
echo ""
echo -e "${BLUE}יש טרמפ! 🚗✨${NC}"

