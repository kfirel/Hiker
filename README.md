# Gvar'am Hitchhiking Bot 🚗

A WhatsApp bot for the Gvar'am hitchhiking community, built with FastAPI, Google Cloud Firestore, and Gemini AI with Function Calling.

## Features

- **AI-Powered Conversations**: Uses Gemini 1.5 Flash to understand user intent in Hebrew
- **Role Detection**: Automatically identifies drivers and hitchhikers
- **Structured Data Extraction**: Function calling to save organized data to Firestore
- **Smart Matching**: Connects drivers with hitchhikers based on routes and schedules
- **Stateless Architecture**: Fully deployed on Google Cloud Run with Firestore persistence
- **Hebrew Language Support**: Native Hebrew conversation interface

## Architecture

```
WhatsApp User → Meta Cloud API → FastAPI Webhook → Gemini AI → Firestore
```

### Components

1. **main.py**: FastAPI application with WhatsApp webhook handlers and AI integration
2. **admin.py**: Secure admin API and testing utilities
3. **Dockerfile**: Container configuration for Cloud Run deployment

## 📚 Documentation

- **[Architecture Guide](docs/ARCHITECTURE.md)**: Complete architecture documentation and design principles
- **[Refactoring Guide](docs/REFACTORING_GUIDE.md)**: Details about the modular refactoring
- **[Admin Guide](docs/ADMIN_GUIDE.md)**: Complete guide for admin features and testing
- **[Migration Guide](docs/MIGRATION_GUIDE.md)**: Upgrade from old testing system
- **[Changes Summary](docs/CHANGES_SUMMARY.md)**: Quick reference for recent changes

## Prerequisites

1. **Google Cloud Project** with:
   - Firestore database enabled
   - Service account with Firestore permissions
   - Cloud Run API enabled

2. **Gemini API Key**:
   - Get from [Google AI Studio](https://makersuite.google.com/app/apikey)

3. **WhatsApp Business Account**:
   - Set up via [Meta for Developers](https://developers.facebook.com/)
   - Get Phone Number ID and Access Token

## Local Development Setup

### 1. Clone and Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required variables:
- `GEMINI_API_KEY`: Your Gemini API key
- `WHATSAPP_TOKEN`: WhatsApp access token
- `WHATSAPP_PHONE_NUMBER_ID`: Your WhatsApp phone number ID
- `VERIFY_TOKEN`: Custom token for webhook verification (you create this)
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account JSON
- `ADMIN_TOKEN`: Token for admin API access (generate with `openssl rand -hex 32`)
- `TESTING_MODE`: Enable/disable testing features (`true` or `false`)
- `ADMIN_PHONE_NUMBERS`: Comma-separated phone numbers for WhatsApp admin commands

### 3. Set Up Google Cloud Firestore

```bash
# Install Google Cloud CLI
# https://cloud.google.com/sdk/docs/install

# Login and set project
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Create Firestore database (if not exists)
gcloud firestore databases create --location=us-central1
```

### 4. Run Locally

```bash
# Run the server
python main.py

# Or with uvicorn
uvicorn main:app --reload --port 8080
```

### 5. Test Webhook (Local)

Use ngrok to expose your local server:

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8080

# Use the ngrok URL for WhatsApp webhook configuration
# Example: https://abc123.ngrok.io/webhook
```

## Google Cloud Run Deployment

### 1. Build and Deploy

```bash
# Set your project ID
export PROJECT_ID=your-gcp-project-id

# Build container image
gcloud builds submit --tag gcr.io/$PROJECT_ID/hitchhiking-bot

# Deploy to Cloud Run
gcloud run deploy hitchhiking-bot \
  --image gcr.io/$PROJECT_ID/hitchhiking-bot \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY \
  --set-env-vars WHATSAPP_TOKEN=$WHATSAPP_TOKEN \
  --set-env-vars WHATSAPP_PHONE_NUMBER_ID=$WHATSAPP_PHONE_NUMBER_ID \
  --set-env-vars VERIFY_TOKEN=$VERIFY_TOKEN \
  --service-account YOUR_SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com
```

### 2. Configure WhatsApp Webhook

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Navigate to your WhatsApp app
3. Go to WhatsApp → Configuration
4. Add webhook callback URL: `https://your-cloud-run-url.run.app/webhook`
5. Add verify token (must match your `VERIFY_TOKEN`)
6. Subscribe to `messages` webhook field

### 3. Test the Deployment

Send a message to your WhatsApp Business number:

```
אני מחפש טרמפ לתל אביב מחר בשעה 9
```

## Data Schema

### Firestore Collection: `users`

Document ID: `phone_number`

```json
{
  "phone_number": "+972501234567",
  "role": "driver",
  "notification_level": "all",
  "driver_data": {
    "origin": "גברעם",
    "destination": "תל אביב",
    "days": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"],
    "departure_time": "09:00",
    "return_time": "17:30",
    "available_seats": 3,
    "notes": ""
  },
  "hitchhiker_data": {},
  "last_seen": "2024-01-15T10:30:00.000Z",
  "chat_history": [
    {
      "role": "user",
      "content": "אני נוסע לתל אביב כל יום",
      "timestamp": "2024-01-15T10:29:00.000Z"
    },
    {
      "role": "assistant",
      "content": "נהדר! באיזה ימים בשבוע אתה נוסע?",
      "timestamp": "2024-01-15T10:29:05.000Z"
    }
  ]
}
```

## AI Function Calling

The bot uses Gemini's function calling feature to extract structured data:

**Function**: `update_user_records`

**Parameters**:
- `role`: "driver" or "hitchhiker"
- `origin`: Starting location
- `destination`: Destination
- `days`: Array of days (for drivers)
- `departure_time`: Departure time
- `return_time`: Return time (drivers)
- `available_seats`: Number of seats (drivers)
- `travel_date`: Specific date (hitchhikers)
- `flexibility`: Time flexibility (hitchhikers)
- `notes`: Additional information

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Gemini AI API key | Yes |
| `WHATSAPP_TOKEN` | WhatsApp access token | Yes |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp phone number ID | Yes |
| `VERIFY_TOKEN` | Custom webhook verification token | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP service account JSON | Yes (local) |
| `ADMIN_TOKEN` | Admin API authentication token | Yes (for admin features) |
| `TESTING_MODE` | Enable testing features (`true`/`false`) | No (default: `false`) |
| `ADMIN_PHONE_NUMBERS` | Whitelisted phones for admin commands | No |
| `PORT` | Server port (default: 8080) | No |

## Monitoring and Logs

### View Cloud Run Logs

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=hitchhiking-bot" --limit 50
```

### Common Issues

**Issue**: Webhook verification fails
- Solution: Ensure `VERIFY_TOKEN` matches exactly in both .env and WhatsApp configuration

**Issue**: Firestore permission denied
- Solution: Verify service account has `roles/datastore.user` role

**Issue**: Gemini API rate limit
- Solution: Implement request throttling or upgrade API quota

## Security Best Practices

1. **Never commit** `.env` or service account JSON files
2. Use Google Secret Manager for production credentials
3. Implement rate limiting for webhook endpoints
4. Validate all incoming webhook requests
5. Use HTTPS only (Cloud Run enforces this)

## Cost Estimation

### Google Cloud Services
- **Cloud Run**: ~$0 for light usage (free tier: 2M requests/month)
- **Firestore**: ~$0 for small communities (free tier: 1GB storage, 50K reads/day)
- **Gemini API**: Check [current pricing](https://ai.google.dev/pricing)

### WhatsApp Business API
- Check [Meta's pricing](https://developers.facebook.com/docs/whatsapp/pricing)

## Admin & Testing Features

The bot includes a secure admin system for testing and management:

- **Admin API**: REST endpoints with token authentication
- **WhatsApp Commands**: Convenient admin commands for testing
- **Testing Mode**: Can be enabled/disabled per environment

**Quick Start:**
```bash
# Generate admin token
openssl rand -hex 32

# Add to .env
ADMIN_TOKEN=your_generated_token
TESTING_MODE=true
ADMIN_PHONE_NUMBERS=972501234567

# Test via WhatsApp
/admin:help

# Or test via API
curl -H "X-Admin-Token: your_token" http://localhost:8080/admin/health
```

**Full Documentation:** See [docs/ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md)

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear description

## License

MIT License - Feel free to use this for your community!

## Support

For issues or questions, please open a GitHub issue or contact the maintainer.

---

Built with ❤️ for the Gvar'am community


