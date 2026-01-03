#!/bin/bash
# Development script - Run everything locally

echo "🚀 Starting Hiker Development Environment..."
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Python venv exists
if [ ! -d "venv" ]; then
    echo -e "${BLUE}📦 Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Check if dependencies are installed
if [ ! -f "venv/bin/uvicorn" ]; then
    echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
    pip install -r requirements.txt
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}⚠️  .env file not found!${NC}"
    echo "Creating .env template..."
    cat > .env << EOF
# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id

# WhatsApp (optional for local dev)
WHATSAPP_TOKEN=your-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-id
VERIFY_TOKEN=my_verify_token

# Gemini AI
GEMINI_API_KEY=your-gemini-key

# Admin
ADMIN_TOKEN=local-dev-token-123
EOF
    echo -e "${BLUE}✏️  Please edit .env with your credentials${NC}"
    echo ""
fi

# Check if node_modules exists in frontend
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${BLUE}📦 Installing Frontend dependencies...${NC}"
    cd frontend
    npm install
    cd ..
fi

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo -e "${BLUE}Starting services...${NC}"
echo ""

# Kill any existing processes on ports 8080 and 3000
lsof -ti:8080 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null

# Start backend in background
echo -e "${GREEN}🐍 Starting Backend (port 8080)...${NC}"
python main.py > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait a bit for backend to start
sleep 2

# Start frontend in background
echo -e "${GREEN}⚛️  Starting Frontend (port 3000)...${NC}"
cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Development environment is running!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📍 URLs:${NC}"
echo -e "   Frontend:  ${GREEN}http://localhost:3000/admin${NC}"
echo -e "   Backend:   ${GREEN}http://localhost:8080${NC}"
echo -e "   API Docs:  ${GREEN}http://localhost:8080/docs${NC}"
echo ""
echo -e "${BLUE}📝 Logs:${NC}"
echo -e "   Backend:   tail -f logs/backend.log"
echo -e "   Frontend:  tail -f logs/frontend.log"
echo ""
echo -e "${RED}Press Ctrl+C to stop all services${NC}"
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Wait for Ctrl+C
trap "echo ''; echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'; exit 0" INT

# Keep script running
wait

