# 🔧 Troubleshooting Guide

Common issues and solutions for the BizClone AI Voice Assistant.

---

## 🔴 RecursionError: Maximum Recursion Depth Exceeded

### Problem
```
RecursionError: maximum recursion depth exceeded while getting the repr of an object
```

### Cause
Circular references in SQLAlchemy model relationships when Pydantic or Python tries to represent the objects. This happens because:
1. Models have bidirectional relationships (Customer ↔ Call ↔ Appointment)
2. The `__repr__` method tries to access related objects
3. Related objects try to access their relationships, creating infinite loops

### Solution ✅
**COMPLETE FIX Applied:**

**Step 1:** Replace `backref` with `back_populates` (prevents implicit circular refs)
**Step 2:** Add `repr=False` to all relationships (prevents repr recursion)
**Step 3:** Add `lazy="select"` for explicit loading strategy

**Files Fixed:**
- `backend/app/models/customer.py` - Added `repr=False, lazy="select"` to relationships
- `backend/app/models/call.py` - Added `repr=False, lazy="select"` to relationships
- `backend/app/models/appointment.py` - Added `repr=False, lazy="select"` to relationships
- `backend/app/models/transcript.py` - Added `repr=False, lazy="select"` to relationships
- `backend/app/models/call_event.py` - Added `repr=False, lazy="select"` to relationships

**Example Fix:**
```python
# BEFORE (causes recursion):
calls = relationship("Call", back_populates="customer", cascade="all, delete-orphan")

# AFTER (fixed):
calls = relationship("Call", back_populates="customer", cascade="all, delete-orphan", lazy="select", repr=False)
```

### Verification
```bash
cd backend
python -c "from app.models import Customer, Call, Appointment; print('✅ Models imported successfully')"

# Test server startup
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 🔴 Port 8000 Already in Use

### Problem
```
ERROR: [Errno 48] Address already in use
```

### Cause
Another process (usually a previous uvicorn instance) is still running on port 8000.

### Solution 1: Kill the Process (Quick)
```bash
# From project root
lsof -ti:8000 | xargs kill -9

# Or use the helper script
bash backend/scripts/kill_port.sh 8000
```

### Solution 2: Find and Kill Manually
```bash
# Find the process
lsof -i:8000

# Kill it (replace PID with actual process ID)
kill -9 <PID>
```

### Solution 3: Use a Different Port
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Prevention
Always stop the server with `Ctrl+C` instead of closing the terminal.

---

## 🔴 Database Connection Error

### Problem
```
sqlalchemy.exc.OperationalError: could not connect to server
```

### Cause
PostgreSQL is not running or connection settings are incorrect.

### Solution
```bash
# Check if PostgreSQL is running
docker-compose ps

# Start PostgreSQL
docker-compose up -d postgres

# Check connection
docker-compose logs postgres

# Verify .env file has correct DATABASE_URL
cat .env | grep DATABASE_URL
```

---

## 🔴 Redis Connection Error

### Problem
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

### Cause
Redis is not running.

### Solution
```bash
# Start Redis
docker-compose up -d redis

# Check Redis status
docker-compose ps redis

# Test Redis connection
redis-cli ping
```

---

## 🔴 Celery Worker Not Processing Tasks

### Problem
Tasks are queued but not being processed.

### Cause
Celery worker is not running or crashed.

### Solution
```bash
# Check if worker is running
ps aux | grep celery

# Start Celery worker
cd backend
celery -A app.workers.celery_app worker --loglevel=info

# For debugging, use debug level
celery -A app.workers.celery_app worker --loglevel=debug
```

---

## 🔴 macOS: Worker Crashes with objc_initializeAfterForkError / SIGABRT

### Problem
On macOS, Celery workers crash with:
```
objc[PID]: +[NSCharacterSet initialize] may have been in progress in another thread when fork() was called.
Process 'ForkPoolWorker-X' pid:XXXXX exited with 'signal 6 (SIGABRT)'
WorkerLostError: Worker exited prematurely
```

### Cause
Whisper (via PyTorch) loads Apple's Objective-C runtime. Celery's default prefork pool forks worker processes; forked children inherit a partially-initialized ObjC state and crash.

### Solution
The app automatically uses the **solo** pool on macOS (no forking). Restart the Celery worker—it should work without changes.

If you need prefork (e.g. on Linux, or for concurrency), the worker uses `prefork` on non-macOS platforms.

**Alternative:** To force prefork on macOS (not recommended):
```bash
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
celery -A app.workers.celery_app worker --loglevel=info --pool=prefork
```

---

## 🔴 OpenAI 429 Quota Exceeded / Rate Limit

### Problem
```
Error code: 429 - You exceeded your current quota, please check your plan and billing details.
openai.RateLimitError / insufficient_quota
```

### Cause
OpenAI account has exhausted its quota (free tier limit or billing issue).

### Solution
1. **Check billing:** [OpenAI Platform Billing](https://platform.openai.com/account/billing)
2. **Add payment method** if on free tier
3. **Fallback behavior:** The system automatically uses keyword-based classification when the API fails. The pipeline continues (intent + entity extraction use rule-based fallbacks), but results are less accurate than when using the API.

### Fallback Details
- **Intent classification:** Keyword matching (emergency, booking, pricing, etc.)
- **Entity extraction:** Minimal extraction (urgency from keywords, service description from transcript)
- Pipeline continues to scheduling; appointments are created with available data.

---

## 🔴 OpenAI API Key Error

### Problem
```
openai.error.AuthenticationError: Incorrect API key provided
```

### Cause
OpenAI API key is missing or invalid.

### Solution
```bash
# Check if API key is set
echo $OPENAI_API_KEY

# Or check .env file
cat .env | grep OPENAI_API_KEY

# Set the API key in .env
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

---

## 🔴 Whisper Model Download Error

### Problem
Whisper fails to download or load the model.

### Solution
```bash
# Manually download the model
python -c "import whisper; whisper.load_model('base')"

# If that fails, try with a smaller model
python -c "import whisper; whisper.load_model('tiny')"
```

---

## 🔴 Migration Errors

### Problem
```
alembic.util.exc.CommandError: Can't locate revision identified by 'xxxxx'
```

### Solution
```bash
cd backend

# Check current migration status
alembic current

# Reset to head
alembic upgrade head

# If that fails, drop all tables and recreate
# WARNING: This will delete all data!
alembic downgrade base
alembic upgrade head
```

---

## 🔴 Import Errors

### Problem
```
ModuleNotFoundError: No module named 'app'
```

### Cause
Running scripts from wrong directory or virtual environment not activated.

### Solution
```bash
# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Always run from backend directory
cd backend
python process_recording.py --file ../data/recordings/call_01.wav
```

---

## 🔴 Audio File Format Error

### Problem
```
Error: Unsupported audio format
```

### Solution
```bash
# Check file format
file data/recordings/call_01.wav

# Convert to WAV if needed (requires ffmpeg)
ffmpeg -i input.mp3 output.wav
```

---

## 🛠️ Useful Commands

### Check All Services
```bash
# PostgreSQL
docker-compose ps postgres

# Redis
docker-compose ps redis

# FastAPI
curl http://localhost:8000/health

# Celery
celery -A app.workers.celery_app status
```

### View Logs
```bash
# Application logs
tail -f logs/bizclone.log

# PostgreSQL logs
docker-compose logs -f postgres

# Redis logs
docker-compose logs -f redis
```

### Clean Restart
```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Start fresh
docker-compose up -d
cd backend
alembic upgrade head
```

---

## 📞 Still Having Issues?

1. Check the logs: `tail -f logs/bizclone.log`
2. Verify all services are running: `docker-compose ps`
3. Check environment variables: `cat .env`
4. Review the error message carefully
5. Search for the error in the documentation

---

**Last Updated:** 2026-03-03

