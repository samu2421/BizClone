# ⚡ BizClone Quick Demo Guide - Week 1-3

**5-Minute Quick Start** | Version 1.0.0

---

## 🚀 Quick Start (3 Commands)

```bash
# Terminal 1: Start API Server
cd backend && source ../venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2: Start Celery Worker
cd backend && source ../venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info

# Terminal 3: Process Recording
cd backend && source ../venv/bin/activate
python process_recording.py --file data/recordings/call_01.wav
```

---

## ✅ Prerequisites Checklist

```bash
# 1. PostgreSQL running
pg_isready

# 2. Redis running
redis-cli ping

# 3. Virtual environment
source venv/bin/activate

# 4. Database ready
cd backend && alembic upgrade head

# 5. Environment configured
cd .. && cat .env | grep -E "DATABASE_URL|OPENAI_API_KEY|REDIS_URL"
```

---

## 🎯 Demo Flow

### 1. Health Check (30 seconds)
```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy", ...}
```

### 2. Process Recording (2 minutes)
```bash
cd backend
python process_recording.py --file data/recordings/sample_call.wav
# Watch Terminal 2 for task execution
```

### 3. Verify Results (1 minute)
```bash
# Check appointments
curl http://localhost:8000/api/calendar/appointments/upcoming?days=7

# Check today's calendar
curl http://localhost:8000/api/calendar/day/$(date +%Y-%m-%d)
```

---

## 📊 What to Show

### 1. **Pipeline Execution** (Terminal 2)
Watch for these log messages:
```
✅ transcription_task_started
✅ transcription_task_completed
✅ intent_classification_task_started
✅ intent_classification_task_completed
✅ entity_extraction_task_started
✅ entity_extraction_task_completed
✅ schedule_appointment_task_started
✅ schedule_appointment_task_completed
```

### 2. **API Endpoints**
```bash
# Health
curl http://localhost:8000/health

# Calendar Day View
curl http://localhost:8000/api/calendar/day/2026-03-03

# Availability
curl "http://localhost:8000/api/calendar/availability?date=2026-03-03&duration=60"

# Upcoming Appointments
curl http://localhost:8000/api/calendar/appointments/upcoming?days=7
```

### 3. **Database Records**
```bash
cd backend
python -c "
from app.db.session import SessionLocal
from app.db.crud import get_all_calls, get_all_appointments
db = SessionLocal()
print(f'Calls: {len(get_all_calls(db, limit=10))}')
print(f'Appointments: {len(get_all_appointments(db, limit=10))}')
db.close()
"
```

---

## 🎬 Demo Script (5 Minutes)

### Minute 1: Introduction
> "BizClone is an AI voice assistant for a plumbing business. It automatically processes customer calls, understands their needs, and schedules appointments."

### Minute 2: Show Architecture
> "The system uses FastAPI for the API, Celery for background tasks, PostgreSQL for data, and OpenAI GPT-4o-mini for AI intelligence."

### Minute 3: Process Recording
```bash
python process_recording.py --file data/recordings/sample_call.wav
```
> "Watch as the system transcribes the call, classifies intent, extracts details, and schedules the appointment automatically."

### Minute 4: Show Results
```bash
curl http://localhost:8000/api/calendar/appointments/upcoming?days=7
```
> "Here's the scheduled appointment with all details extracted from the call."

### Minute 5: Explain Pipeline
> "The complete pipeline: Recording → Transcription → Intent Classification → Entity Extraction → Scheduling. All automated, no human intervention needed."

---

## 🔧 Quick Troubleshooting

### Server won't start?
```bash
# Check port 8000 is free
lsof -i :8000
# Kill if needed: kill -9 <PID>
```

### Celery won't connect?
```bash
# Check Redis
redis-cli ping
# Restart if needed: redis-server
```

### No recordings?
```bash
# Check directory
ls backend/data/recordings/
# Need at least one .wav file
```

### Database error?
```bash
# Run migrations
cd backend && alembic upgrade head
```

---

## 📈 Success Metrics

After demo, you should see:

- ✅ API server running (http://localhost:8000)
- ✅ Celery worker connected
- ✅ Recording processed successfully
- ✅ Appointment scheduled
- ✅ Calendar API returning data
- ✅ All tasks completed without errors

---

## 🎯 Key Features to Highlight

1. **Automated Pipeline**: No manual intervention
2. **AI Intelligence**: GPT-4o-mini for understanding
3. **Smart Scheduling**: Finds available slots automatically
4. **Business Knowledge**: 50+ FAQs integrated
5. **Emergency Detection**: Prioritizes urgent calls
6. **Complete Tracking**: Full audit trail

---

## 📚 Quick Reference

### Important URLs:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

### Important Commands:
```bash
# Start server
uvicorn app.main:app --reload

# Start worker
celery -A app.workers.celery_app worker --loglevel=info

# Process recording
python process_recording.py --file <path>

# Run tests
pytest tests/ -v
```

### Important Files:
- `.env` - Configuration
- `backend/app/main.py` - API entry point
- `backend/app/workers/tasks.py` - Celery tasks
- `backend/process_recording.py` - Recording processor

---

## 🎉 Demo Complete!

**What was demonstrated:**
- ✅ Full AI voice assistant pipeline
- ✅ Automated call processing
- ✅ Intelligent appointment scheduling
- ✅ Calendar management
- ✅ Business knowledge integration

**Next Steps:**
- Week 4: Voice Response + Escalation
- Production deployment
- Advanced features

---

*Quick Demo Guide v1.0 | March 3, 2026*
