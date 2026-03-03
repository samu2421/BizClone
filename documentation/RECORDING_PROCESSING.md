# Recording Processing Guide

## Overview

The BizClone system uses a **controlled processing mechanism** for call recordings. Recordings are **NOT** automatically processed when placed in the `recordings/` directory. Instead, each recording must be explicitly triggered for processing using the CLI script.

## Architecture

### No Automatic Processing
- ✅ No background folder scanning
- ✅ No automatic processing of all files
- ✅ Each file processed exactly once (unless explicitly re-triggered)
- ✅ Proper logging and error handling
- ✅ Duplicate prevention via database checks

### Processing Flow

```
1. User runs CLI script with --file argument
2. Script validates file exists
3. Script generates unique call_sid from filename
4. Script checks if call_sid already exists in database
5. If exists: Skip processing (prevent duplicates)
6. If new: Create customer record (if needed)
7. Create call record in database
8. Trigger Celery transcription task
9. Celery pipeline processes:
   - Transcription (Whisper)
   - Intent Classification (GPT-4o-mini)
   - Entity Extraction (GPT-4o-mini)
   - Priority Detection
   - Conversation State Management
```

## Usage

### Basic Usage

```bash
# Process a single recording
python process_recording.py --file recordings/call_001.wav
```

### With Custom Customer Phone

```bash
# Process with specific customer phone number
python process_recording.py --file recordings/emergency_call.wav --customer-phone "+15559998888"
```

### Full Options

```bash
python process_recording.py \
  --file data/recordings/my_call.wav \
  --customer-phone "+15551234567" \
  --business-phone "+15559876543"
```

## CLI Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--file` | Yes | - | Path to the recording file to process |
| `--customer-phone` | No | `+15551234567` | Customer phone number |
| `--business-phone` | No | `+15559876543` | Business phone number |

## Output Examples

### Successful Processing

```
============================================================
✅ Recording processing initiated successfully!
   Call ID: 550e8400-e29b-41d4-a716-446655440000
   Call SID: CLI_call_001
   Task ID: 7c9e6679-7425-40de-944b-e07fc1f90ae7
   File: /path/to/recordings/call_001.wav
   Customer ID: 123e4567-e89b-12d3-a456-426614174000

   The transcription pipeline has been triggered.
   Check logs for processing status.
============================================================
```

### Duplicate Detection

```
============================================================
⚠️  Recording already processed!
   Call ID: 550e8400-e29b-41d4-a716-446655440000
   Call SID: CLI_call_001
   File: /path/to/recordings/call_001.wav
   Reason: Call already processed
============================================================
```

### File Not Found

```
❌ Error: Recording file not found: recordings/nonexistent.wav
```

## How It Works

### 1. Call SID Generation
The script generates a unique `call_sid` from the filename:
- Filename: `call_001.wav` → Call SID: `CLI_call_001`
- Filename: `emergency_20260227.wav` → Call SID: `CLI_emergency_20260227`

### 2. Duplicate Prevention
Before processing, the script checks if a call with the same `call_sid` already exists in the database. If it does, processing is skipped.

### 3. Customer Management
If the customer phone number doesn't exist in the database, a new customer record is automatically created.

### 4. Database Entry
A new call record is created with:
- Unique call_sid
- Customer ID
- Phone numbers (from/to)
- Direction (inbound)
- Recording URL (absolute file path)
- Timestamp

### 5. Celery Task Trigger
The `transcribe_audio_task` is queued via Celery, which triggers the full AI processing pipeline.

## Safeguards

✅ **File Validation**: Checks if file exists before processing  
✅ **Duplicate Prevention**: Checks database for existing call_sid  
✅ **Customer Creation**: Automatically creates customer if needed  
✅ **Error Logging**: Comprehensive logging for debugging  
✅ **Transaction Safety**: Database transactions with proper cleanup  
✅ **Graceful Failures**: Clean error messages and exit codes  

## Integration with Existing System

This CLI script integrates seamlessly with the existing FastAPI + Celery architecture:

- **Database**: Uses existing SQLAlchemy models and CRUD operations
- **Celery**: Triggers existing `transcribe_audio_task` from `app.workers.tasks`
- **Logging**: Uses existing structured logging system
- **Models**: Uses existing Call, Customer, and related models

## Monitoring

### Check Processing Status

```bash
# View logs
tail -f logs/bizclone.log

# Check Celery worker
celery -A app.workers.celery_app worker --loglevel=info

# Check database
psql -d bizclone -c "SELECT id, call_sid, status FROM calls ORDER BY created_at DESC LIMIT 10;"
```

## Best Practices

1. **Always use absolute or relative paths** from the backend directory
2. **Check logs** after triggering processing to monitor progress
3. **Don't re-process** the same file unless you have a specific reason
4. **Use meaningful filenames** for easier tracking
5. **Keep recordings organized** in the `recordings/` directory

## Troubleshooting

### Issue: "File not found"
- **Solution**: Check the file path is correct relative to the backend directory

### Issue: "Call already processed"
- **Solution**: This is expected behavior. The file was already processed. Check the database for the existing call record.

### Issue: "Celery task not running"
- **Solution**: Ensure Celery worker is running: `celery -A app.workers.celery_app worker --loglevel=info`

### Issue: "Database connection error"
- **Solution**: Ensure PostgreSQL is running and environment variables are set correctly

## Example Workflow

```bash
# 1. Navigate to backend directory
cd backend

# 2. Activate virtual environment
source ../venv/bin/activate

# 3. Ensure Celery worker is running (in separate terminal)
celery -A app.workers.celery_app worker --loglevel=info

# 4. Process a recording
python process_recording.py --file recordings/call_001.wav

# 5. Monitor logs
tail -f logs/bizclone.log

# 6. Check database for results
# (after processing completes)
```

---

**Created**: 2026-03-02  
**Version**: 1.0  
**Part of**: BizClone Week 3 - Controlled Recording Processing

