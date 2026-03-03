# BizClone Quick Start Guide

**Last Updated:** 2026-02-27
**Current Status:** WEEK 1 - COMPLETE ✅🎉

## Prerequisites
- Python 3.12.4 (installed in venv)
- Docker Desktop (for PostgreSQL and Redis)
- Twilio Account (for phone integration)
- OpenAI API Key (for GPT-4o-mini)
- ElevenLabs API Key (optional, for TTS)

## Setup Steps

### 1. Activate Virtual Environment
```bash
source venv/bin/activate
```

### 2. Verify Installation
```bash
python backend/scripts/verify_setup.py
```
Expected: All 23 dependencies should show ✓

### 3. Configure Environment
```bash
cp .env.example .env
```
Then edit `.env` with your actual credentials:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `OPENAI_API_KEY`
- `ELEVENLABS_API_KEY` (optional)

### 4. Start Database Services
```bash
docker-compose up -d
```

### 5. Verify Services
```bash
docker-compose ps
```
Both `bizclone_postgres` and `bizclone_redis` should be "Up"

### 6. Check Database Connection
```bash
docker exec -it bizclone_postgres psql -U bizclone_user -d bizclone_db -c "SELECT version();"
```

### 7. Check Redis Connection
```bash
docker exec -it bizclone_redis redis-cli ping
```
Expected: `PONG`

## Development Workflow

### Start the API Server
```bash
cd backend
source ../venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Server will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

### Test Voice Recording Upload (n8n Simulation)
```bash
# Using the test script
python backend/scripts/test_voice_upload.py test.wav +1234567890

# Using curl
curl -X POST http://localhost:8000/webhooks/n8n/voice/upload \
  -F "audio_file=@test.wav" \
  -F "from_number=+1234567890" \
  -F "customer_name=Test Customer"
```

### Run Tests
```bash
cd backend
pytest tests/ -v
pytest tests/ -v --cov=app  # With coverage
```

### Run Linting
```bash
black backend/app
flake8 backend/app
mypy backend/app
```

### Stop Services
```bash
docker-compose down
```

### Stop Services and Remove Data
```bash
docker-compose down -v
```

## Project Structure
```
BizClone/
├── backend/app/          # Main application code
├── data/                 # Data storage (recordings, transcripts, vectors)
├── logs/                 # Application logs
├── .env                  # Environment variables (create from .env.example)
├── docker-compose.yml    # Database services
└── requirements.txt      # Python dependencies
```

## Current Features (WEEK 1 - COMPLETE) 🎉

✅ **Environment Setup** - All dependencies installed and verified
✅ **FastAPI Core** - Health endpoints, logging, error handling, middleware
✅ **Database Layer** - PostgreSQL with SQLAlchemy, migrations, CRUD operations
✅ **Voice Recording Integration** - n8n webhooks, audio handling, Twilio downloads
✅ **Transcription Service** - Whisper CPU, Celery workers, automatic transcription

### Available Endpoints

- `GET /` - Welcome message
- `GET /info` - Application information
- `GET /health` - Health check with service status
- `GET /health/ping` - Simple ping
- `POST /webhooks/twilio/voice` - Twilio inbound call handler
- `POST /webhooks/twilio/recording` - Twilio recording callback
- `POST /webhooks/twilio/status` - Twilio status updates
- `POST /webhooks/n8n/voice/upload` - Upload voice recording (n8n simulation)
- `GET /webhooks/n8n/call/{call_sid}` - Get call information

## Running the Full System

### 1. Start Infrastructure

```bash
# Start PostgreSQL and Redis
docker-compose up -d
```

### 2. Start Celery Worker (Background Tasks)

```bash
cd backend
source ../venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info --queues=transcription,processing
```

### 3. Start API Server

```bash
# In a new terminal
cd backend
source ../venv/bin/activate
python -m uvicorn app.main:app --reload
```

### 4. Test the Full Pipeline

```bash
# Upload audio file
curl -X POST http://localhost:8000/webhooks/n8n/voice/upload \
  -F "audio_file=@test.wav" \
  -F "from_number=+1234567890"

# Check Celery logs to see transcription progress
# Check database for transcript
```

## Next Steps

**WEEK 2 - INTELLIGENCE:** AI-powered understanding
- Intent Classification (GPT-4o-mini)
- Entity Extraction
- Conversation State Manager
- Priority Detection

## Troubleshooting

### Port Already in Use
If PostgreSQL port 5432 or Redis port 6379 is already in use:
```bash
# Check what's using the port
lsof -i :5432
lsof -i :6379

# Stop the service or change ports in docker-compose.yml
```

### Dependencies Not Found
```bash
source venv/bin/activate
pip install -r requirements-core.txt
pip install git+https://github.com/openai/whisper.git
```

### Docker Not Running
```bash
# Start Docker Desktop
open -a Docker

# Wait for Docker to start, then:
docker-compose up -d
```

## Support

For issues, check:
1. Virtual environment is activated
2. Docker services are running
3. Environment variables are set correctly
4. All dependencies are installed

