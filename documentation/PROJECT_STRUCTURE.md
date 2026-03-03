# 📁 BizClone Project Structure - Week 1-3

**Version**: 1.0.0  
**Last Updated**: March 3, 2026

---

## 🗂️ Directory Structure

```
BizClone/
├── backend/                          # Backend application
│   ├── app/                          # Main application package
│   │   ├── api/                      # API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── calendar.py           # Calendar API (Week 3)
│   │   │   ├── health.py             # Health check endpoint
│   │   │   ├── n8n_webhooks.py       # n8n webhook handlers
│   │   │   └── twilio_webhooks.py    # Twilio webhook handlers
│   │   │
│   │   ├── config/                   # Configuration
│   │   │   ├── __init__.py
│   │   │   └── settings.py           # Application settings
│   │   │
│   │   ├── core/                     # Core utilities
│   │   │   ├── __init__.py
│   │   │   ├── business_data.json    # Business knowledge (Week 3)
│   │   │   ├── business_data_loader.py # Data loader (Week 3)
│   │   │   ├── exceptions.py         # Custom exceptions
│   │   │   ├── logging.py            # Logging configuration
│   │   │   └── middleware.py         # FastAPI middleware
│   │   │
│   │   ├── db/                       # Database layer
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # SQLAlchemy base
│   │   │   ├── crud.py               # CRUD operations
│   │   │   └── session.py            # Database session
│   │   │
│   │   ├── models/                   # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── appointment.py        # Appointment model
│   │   │   ├── call.py               # Call model
│   │   │   ├── call_event.py         # Call event model
│   │   │   ├── conversation_state.py # Conversation state model
│   │   │   ├── customer.py           # Customer model
│   │   │   ├── faq.py                # FAQ model (Week 3)
│   │   │   ├── policy.py             # Policy model (Week 3)
│   │   │   ├── service.py            # Service model (Week 3)
│   │   │   └── transcript.py         # Transcript model
│   │   │
│   │   ├── schemas/                  # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── appointment.py        # Appointment schemas
│   │   │   ├── calendar.py           # Calendar schemas (Week 3)
│   │   │   ├── call.py               # Call schemas
│   │   │   └── customer.py           # Customer schemas
│   │   │
│   │   ├── services/                 # Business logic services
│   │   │   ├── ai/                   # AI services (Week 2-3)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── conversation_manager.py  # Conversation management
│   │   │   │   ├── entity_extractor.py      # Entity extraction
│   │   │   │   ├── intent_classifier.py     # Intent classification
│   │   │   │   ├── priority_detector.py     # Emergency detection
│   │   │   │   └── response_generator.py    # Response generation (Week 3)
│   │   │   │
│   │   │   ├── calendar/             # Calendar services (Week 3)
│   │   │   │   ├── __init__.py
│   │   │   │   └── calendar_service.py      # Calendar management
│   │   │   │
│   │   │   ├── scheduling/           # Scheduling services (Week 3)
│   │   │   │   ├── __init__.py
│   │   │   │   └── scheduler.py             # Appointment scheduling
│   │   │   │
│   │   │   └── voice/                # Voice services (Week 1)
│   │   │       ├── __init__.py
│   │   │       ├── audio_handler.py         # Audio processing
│   │   │       ├── downloader.py            # Audio download
│   │   │       └── transcription.py         # Whisper transcription
│   │   │
│   │   ├── workers/                  # Celery workers
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py         # Celery configuration
│   │   │   └── tasks.py              # Background tasks
│   │   │
│   │   └── main.py                   # FastAPI application entry point
│   │
│   ├── data/                         # Data storage
│   │   ├── recordings/               # Audio recordings
│   │   └── transcripts/              # Transcript files
│   │
│   ├── migrations/                   # Alembic migrations
│   │   ├── versions/                 # Migration versions
│   │   ├── env.py                    # Alembic environment
│   │   └── script.py.mako            # Migration template
│   │
│   ├── scripts/                      # Utility scripts
│   │   ├── test_voice_upload.py      # Voice upload test
│   │   └── verify_setup.py           # Setup verification
│   │
│   ├── tests/                        # Test suite
│   │   ├── __init__.py
│   │   ├── conftest.py               # Pytest configuration
│   │   ├── test_api.py               # API tests
│   │   ├── test_calendar.py          # Calendar tests (Week 3)
│   │   ├── test_conversation_manager.py  # Conversation tests
│   │   ├── test_database.py          # Database tests
│   │   ├── test_entity_extraction.py # Entity extraction tests
│   │   ├── test_intent_classification.py # Intent tests
│   │   ├── test_priority_detection.py    # Priority tests
│   │   ├── test_response_generator.py    # Response tests (Week 3)
│   │   ├── test_scheduler.py         # Scheduler tests (Week 3)
│   │   ├── test_transcription.py     # Transcription tests
│   │   └── test_voice_recording.py   # Voice recording tests
│   │
│   ├── alembic.ini                   # Alembic configuration
│   ├── process_recording.py          # Recording processor script
│   ├── pytest.ini                    # Pytest configuration
│   ├── README.md                     # Backend documentation
│   └── RECORDING_PROCESSING.md       # Recording processing guide
│
├── data/                             # Shared data directory
│   ├── chroma/                       # ChromaDB storage (future)
│   ├── recordings/                   # Shared recordings
│   └── transcripts/                  # Shared transcripts
│
├── logs/                             # Application logs
│
├── tests/                            # Root-level tests
│   └── mock_transcripts/             # Mock transcript data
│       ├── transcript_001.json
│       ├── transcript_002.json
│       └── ... (10 files)
│
├── venv/                             # Python virtual environment
│
├── .env                              # Environment variables
├── .gitignore                        # Git ignore rules
├── docker-compose.yml                # Docker configuration
├── requirements.txt                  # Python dependencies
├── requirements-core.txt             # Core dependencies
│
└── Documentation Files:
    ├── BUSINESS_DATA_INTEGRATION_COMPLETE.md
    ├── CLEANUP_NOTES.md
    ├── CONTROLLED_PROCESSING_COMPLETE.md
    ├── DEMO_README.md
    ├── PROGRESS_SUMMARY.md
    ├── PROJECT_STRUCTURE.md (this file)
    ├── QUICK_DEMO_GUIDE.md
    ├── QUICK_START.md
    ├── README.md
    ├── WEEK1_COMPLETE_SUMMARY.md
    ├── WEEK1_STEP1_COMPLETE.md
    ├── WEEK1_STEP2_COMPLETE.md
    ├── WEEK1_STEP3_COMPLETE.md
    ├── WEEK1_STEP4_COMPLETE.md
    ├── WEEK1_STEP5_COMPLETE.md
    ├── WEEK2_COMPLETE_SUMMARY.md
    ├── WEEK2_STEP1_COMPLETE.md
    ├── WEEK2_STEP2_COMPLETE.md
    ├── WEEK2_STEP3_COMPLETE.md
    ├── WEEK2_STEP4_COMPLETE.md
    ├── WEEK3_COMPLETE_SUMMARY.md
    ├── WEEK3_STEP1_COMPLETE.md
    ├── WEEK3_STEP2_COMPLETE.md
    ├── WEEK3_STEP3_COMPLETE.md
    └── WEEK3_STEP4_COMPLETE.md
```

---

## 📊 File Count Summary

### Application Code:
- **Python Files**: ~60 files
- **Test Files**: 11 files
- **Migration Files**: Multiple versions
- **Configuration Files**: 5 files

### Documentation:
- **Markdown Files**: 25+ files
- **README Files**: 3 files
- **Step Guides**: 12 files
- **Summary Docs**: 4 files

### Data:
- **Business Data**: 1 JSON file (62 entries)
- **Mock Transcripts**: 10 JSON files
- **Recordings**: Variable (user-generated)

---

## 🎯 Key Directories Explained

### `/backend/app/`
Main application package containing all business logic, API endpoints, and services.

### `/backend/app/services/`
Service layer organized by domain:
- `ai/` - AI-powered services (Week 2-3)
- `calendar/` - Calendar management (Week 3)
- `scheduling/` - Appointment scheduling (Week 3)
- `voice/` - Voice processing (Week 1)

### `/backend/app/workers/`
Celery background task workers for asynchronous processing.

### `/backend/tests/`
Comprehensive test suite with 136+ test cases.

### `/data/`
Shared data storage for recordings, transcripts, and ChromaDB.

---

## 📈 Code Statistics

### Lines of Code (Approximate):
- **Application Code**: ~8,000 lines
- **Test Code**: ~3,000 lines
- **Configuration**: ~500 lines
- **Documentation**: ~5,000 lines
- **Total**: ~16,500 lines

### Week-by-Week Additions:
- **Week 1**: ~3,500 lines (Foundation)
- **Week 2**: ~2,500 lines (AI Intelligence)
- **Week 3**: ~2,500 lines (Scheduling & Response)

---

## 🔧 Configuration Files

### `.env`
Environment variables for database, Redis, OpenAI, etc.

### `alembic.ini`
Database migration configuration.

### `pytest.ini`
Test suite configuration.

### `docker-compose.yml`
Docker services (PostgreSQL, Redis).

### `requirements.txt`
Python package dependencies.

---

## 📚 Documentation Organization

### Setup & Getting Started:
- `README.md` - Main project README
- `QUICK_START.md` - Quick start guide
- `DEMO_README.md` - Demo guide
- `QUICK_DEMO_GUIDE.md` - 5-minute demo

### Week Summaries:
- `WEEK1_COMPLETE_SUMMARY.md`
- `WEEK2_COMPLETE_SUMMARY.md`
- `WEEK3_COMPLETE_SUMMARY.md`

### Step-by-Step Guides:
- `WEEK*_STEP*_COMPLETE.md` (12 files)

### Special Topics:
- `BUSINESS_DATA_INTEGRATION_COMPLETE.md`
- `CONTROLLED_PROCESSING_COMPLETE.md`
- `CLEANUP_NOTES.md`
- `PROJECT_STRUCTURE.md` (this file)

---

*Project Structure v1.0 | March 3, 2026*
