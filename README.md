# BizClone - AI Voice Assistant for Plumbing Business

**An intelligent, automated voice assistant system for small enterprise plumbing services in Hamburg, Germany.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![Celery](https://img.shields.io/badge/Celery-5.3.6-green.svg)](https://docs.celeryproject.org/)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Processing Recordings](#processing-recordings)
- [Documentation](#documentation)
- [Development Status](#development-status)
- [Testing](#testing)
- [License](#license)

---

## 🎯 Overview

BizClone is an AI-powered voice assistant designed to automate customer call handling for plumbing businesses. The system processes customer call recordings, transcribes audio, classifies intent, extracts relevant information, and automatically schedules appointments—all without human intervention.

### Key Capabilities

- **Automated Transcription**: Converts customer call recordings to text using OpenAI Whisper
- **Intent Classification**: Identifies customer intent (appointment, emergency, information, etc.)
- **Entity Extraction**: Extracts key information (service type, urgency, preferred date/time, location)
- **Smart Scheduling**: Automatically books appointments based on availability and business hours
- **Priority Detection**: Identifies and flags emergency situations for immediate attention
- **Knowledge Base**: RAG-powered system with 50+ FAQs and business information

---

## ✨ Features

### Week 1: Call Pipeline ✅
- ✅ FastAPI backend with health monitoring
- ✅ PostgreSQL database with SQLAlchemy ORM
- ✅ Celery task queue with Redis
- ✅ Audio recording storage and management
- ✅ OpenAI Whisper transcription service
- ✅ Comprehensive logging and error handling

### Week 2: AI Intelligence ✅
- ✅ GPT-4o-mini powered intent classification (7 categories)
- ✅ Entity extraction (8 entity types)
- ✅ Priority detection and scoring (0-100)
- ✅ Conversation state management
- ✅ ChromaDB vector database for RAG
- ✅ Business knowledge base integration

### Week 3: Response & Scheduling ✅
- ✅ AI-powered response generation
- ✅ Intelligent appointment scheduling
- ✅ Calendar management system
- ✅ Business hours validation (09:00 - 18:00)
- ✅ Conflict detection and resolution
- ✅ Complete end-to-end automation

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Customer Call Recording                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Audio File Storage                          │
│                  (data/recordings/)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Transcription (Whisper)                         │
│              Celery Task: transcribe_audio_task              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│         Intent Classification (GPT-4o-mini)                  │
│         Celery Task: classify_intent_task                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│         Entity Extraction (GPT-4o-mini)                      │
│         Celery Task: extract_entities_task                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│         Appointment Scheduling                               │
│         Celery Task: schedule_appointment_task               │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Database & Event Logging                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

### Backend Framework
- **FastAPI** - Modern, high-performance web framework
- **Python 3.11+** - Programming language
- **Uvicorn** - ASGI server

### Database & Storage
- **PostgreSQL** - Primary relational database
- **SQLAlchemy** - ORM for database operations
- **Alembic** - Database migrations
- **ChromaDB** - Vector database for RAG

### Task Queue
- **Celery** - Distributed task queue
- **Redis** - Message broker and cache

### AI & ML
- **OpenAI GPT-4o-mini** - Intent classification, entity extraction, response generation
- **OpenAI Whisper** - Speech-to-text transcription
- **OpenAI Embeddings** - Text embeddings for RAG

### Development Tools
- **pytest** - Testing framework
- **structlog** - Structured logging
- **Docker Compose** - Container orchestration

---

## 📁 Project Structure

```
BizClone/
├── backend/
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   ├── core/             # Core utilities (logging, config, business data)
│   │   ├── db/               # Database connection & CRUD
│   │   ├── models/           # SQLAlchemy models (15 models)
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   │   ├── ai/           # AI services (intent, entity, response)
│   │   │   ├── voice/        # Transcription service
│   │   │   ├── scheduling/   # Appointment scheduling
│   │   │   └── rag/          # Knowledge base & RAG
│   │   └── workers/          # Celery tasks
│   ├── tests/                # Test suite (136 tests)
│   ├── migrations/           # Alembic migrations
│   ├── scripts/              # Utility scripts
│   └── process_recording.py  # CLI for processing recordings
├── data/
│   ├── recordings/           # Customer call recordings (WAV files)
│   ├── transcripts/          # Generated transcripts
│   └── chroma/               # ChromaDB vector store
├── documentation/            # Project documentation
│   ├── WEEK1_COMPLETE.md     # Week 1 summary
│   ├── WEEK2_COMPLETE.md     # Week 2 summary
│   ├── WEEK3_COMPLETE.md     # Week 3 summary
│   ├── PROJECT_STRUCTURE.md  # Detailed structure
│   ├── PROGRESS_SUMMARY.md   # Overall progress
│   ├── QUICK_DEMO_GUIDE.md   # Demo instructions
│   └── RECORDING_PROCESSING.md  # Processing guide
├── logs/                     # Application logs
├── venv/                     # Python virtual environment
├── docker-compose.yml        # Docker services (PostgreSQL, Redis)
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Docker & Docker Compose
- PostgreSQL 15+ (via Docker)
- Redis (via Docker)
- OpenAI API key

### 1. Clone Repository

```bash
git clone <repository-url>
cd BizClone
```

### 2. Set Up Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your credentials:
# - OPENAI_API_KEY
# - DATABASE_URL
# - REDIS_URL
```

### 4. Start Services

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 5. Initialize Database

```bash
cd backend

# Run migrations
alembic upgrade head

# Load business data (FAQs, services, policies)
python -c "from app.core.business_data_loader import load_business_data; from app.db.session import SessionLocal; db = SessionLocal(); load_business_data(db); db.close()"
```

### 6. Start Application

```bash
# Terminal 1: Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info
```

### 7. Verify Installation

```bash
# Check health endpoints
curl http://localhost:8000/health
curl http://localhost:8000/health/db
curl http://localhost:8000/health/redis

# View API documentation
open http://localhost:8000/docs
```

---

## 🎙️ Processing Recordings

The system processes customer call recordings from the `data/recordings/` folder using a controlled CLI script.

### Basic Usage

```bash
cd backend

# Process a single recording
python process_recording.py --file ../data/recordings/call_01.wav

# Process with custom customer phone
python process_recording.py --file ../data/recordings/call_01.wav --customer-phone "+491234567890"
```

### What Happens

1. ✅ Script validates the recording file exists
2. ✅ Creates a unique call ID and database entry
3. ✅ Triggers Celery transcription task
4. ✅ Celery pipeline automatically processes:
   - Transcription (Whisper)
   - Intent classification (GPT-4o-mini)
   - Entity extraction (GPT-4o-mini)
   - Priority detection
   - Response generation
   - Appointment scheduling (if applicable)
5. ✅ All events logged to database and log files

### Monitor Processing

```bash
# Watch logs in real-time
tail -f logs/bizclone.log

# Check Celery worker status
celery -A app.workers.celery_app status

# View Celery events
celery -A app.workers.celery_app events
```

---

## 📚 Documentation

Comprehensive documentation is available in the `documentation/` folder:

- **[WEEK1_COMPLETE.md](documentation/WEEK1_COMPLETE.md)** - Call pipeline implementation
- **[WEEK2_COMPLETE.md](documentation/WEEK2_COMPLETE.md)** - AI intelligence features
- **[WEEK3_COMPLETE.md](documentation/WEEK3_COMPLETE.md)** - Response generation & scheduling
- **[PROJECT_STRUCTURE.md](documentation/PROJECT_STRUCTURE.md)** - Detailed project structure
- **[PROGRESS_SUMMARY.md](documentation/PROGRESS_SUMMARY.md)** - Overall progress tracking
- **[QUICK_DEMO_GUIDE.md](documentation/QUICK_DEMO_GUIDE.md)** - 15-minute demo guide
- **[RECORDING_PROCESSING.md](documentation/RECORDING_PROCESSING.md)** - Recording processing guide

---

## 📊 Development Status

### Completed (Weeks 1-3)

- [x] **Week 1**: Call Pipeline
  - [x] Environment setup
  - [x] FastAPI core
  - [x] Database schema & migrations
  - [x] Voice recording integration
  - [x] Transcription service

- [x] **Week 2**: AI Intelligence
  - [x] Intent classification
  - [x] Entity extraction
  - [x] Priority detection
  - [x] RAG knowledge base

- [x] **Week 3**: Response & Scheduling
  - [x] Response generation
  - [x] Scheduling service
  - [x] Calendar integration
  - [x] Celery pipeline integration
  - [x] Business data integration

### In Progress (Week 4)

- [ ] **Week 4**: Escalation & Notifications
  - [ ] SMS notifications (Twilio)
  - [ ] Email notifications
  - [ ] Emergency escalation workflow
  - [ ] Admin dashboard

---

## 🧪 Testing

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_intent_classifier.py

# Run with verbose output
pytest -v
```

**Test Statistics:**
- Total Tests: 136
- Passing: 136 ✅
- Coverage: 65%

---

## 📈 Metrics

- **Total Lines of Code**: ~19,000
- **Python Files**: 74
- **Test Files**: 11
- **API Endpoints**: 12
- **Database Models**: 15
- **Celery Tasks**: 4 (fully chained)
- **Business FAQs**: 50+
- **Services Offered**: 8

---

## 🔧 Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps

# Restart PostgreSQL
docker-compose restart postgres

# Check database logs
docker-compose logs postgres
```

### Celery Worker Not Processing

```bash
# Check Redis is running
docker-compose ps

# Restart Redis
docker-compose restart redis

# Check Celery worker logs
celery -A app.workers.celery_app worker --loglevel=debug
```

### Transcription Errors

```bash
# Verify OpenAI API key is set
echo $OPENAI_API_KEY

# Check Whisper model is downloaded
python -c "import whisper; whisper.load_model('base')"

# Check audio file format
file data/recordings/call_01.wav
```

---

## 📞 Business Information

- **Business Name**: BizClone Plumbing Services
- **Location**: Hamburg, Germany
- **Business Type**: Small Enterprise Plumber
- **Business Hours**: Monday-Friday, 09:00 - 18:00
- **Services**: Leak repair, drain cleaning, water heater, pipe installation, emergency services

---

## 📄 License

This project is proprietary software developed for BizClone Plumbing Services.

---

## 👥 Contributors

- Development Team: AI Engineering & System Architecture
- Project Timeline: February 27 - March 3, 2026
- Status: Production-Ready (Weeks 1-3 Complete)

---

## 🎯 Next Steps

1. Complete Week 4 (Escalation & Notifications)
2. Deploy to production environment
3. Integrate with live phone system
4. Monitor and optimize performance
5. Gather customer feedback
6. Iterate and improve

---

**For detailed setup and demo instructions, see [QUICK_DEMO_GUIDE.md](documentation/QUICK_DEMO_GUIDE.md)**