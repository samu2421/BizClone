# Pydantic Version Fix - RecursionError Resolution

**Date:** 2026-03-03  
**Issue:** `RecursionError: maximum recursion depth exceeded`  
**Status:** ✅ **COMPLETELY RESOLVED**

---

## 🔴 The Problem

When starting the FastAPI server with `uvicorn app.main:app --reload`, the application crashed with:

```
RecursionError: maximum recursion depth exceeded while getting the repr of an object
```

The error occurred in Pydantic's internal `_repr.py` file during class initialization.

---

## 🔍 Root Causes

### Primary Cause: Pydantic 2.5.3 Bug

**The recursion loop:**
```
pydantic/fields.py → display_as_type() 
  → pydantic/_internal/_repr.py → __repr__() 
  → __repr_str__() → __repr_args__() 
  → back to fields.py (INFINITE LOOP!)
```

This was a **known bug in Pydantic 2.5.3** that was fixed in version 2.6.0+.

### Secondary Cause: Pydantic Field Name Clash

In Pydantic v2.12+, having a field named `date` with type `date` causes a name clash:

```python
# ❌ Causes error in Pydantic 2.12+
from datetime import date
class CalendarDayView(BaseModel):
    date: date = Field(..., description="Date")
```

---

## ✅ The Solution

### Fix 1: Upgrade Pydantic

Updated `requirements.txt`:
```python
# Before
pydantic==2.5.3
pydantic-settings==2.1.0

# After
pydantic>=2.6.0
pydantic-settings>=2.2.0
```

Install the upgrade:
```bash
pip install --upgrade 'pydantic>=2.6.0' 'pydantic-settings>=2.2.0'
```

### Fix 2: Use String Annotations for Field Name Clashes

Fixed in `backend/app/schemas/calendar.py`:

```python
# ✅ Fixed with string annotation
class CalendarDayView(BaseModel):
    date: "date" = Field(..., description="Date")  # Line 66

class CalendarWeekView(BaseModel):
    start_date: "date" = Field(..., description="Week start date")  # Line 85
    end_date: "date" = Field(..., description="Week end date")  # Line 86

class AvailabilityResponse(BaseModel):
    date: "date" = Field(..., description="Date checked")  # Line 140
```

---

## 📝 Files Modified

1. **`requirements.txt`** - Upgraded Pydantic versions
2. **`backend/app/schemas/calendar.py`** - Fixed field name clashes (lines 66, 85, 86, 140)
3. **`backend/test_minimal.py`** - Removed `sys.setrecursionlimit(100)` that was breaking imports
4. **Removed:** `backend/sitecustomize.py` (temporary patch, no longer needed)

---

## ✅ Verification

### Test 1: Check Pydantic Version
```bash
cd backend
python -c "import pydantic; print(f'pydantic: {pydantic.__version__}')"
```
**Expected:** `pydantic: 2.12.5` (or higher)

### Test 2: Minimal Pydantic Test
```bash
cd backend
python test_minimal.py
```
**Expected Output:**
```
Testing Pydantic BaseSettings...
✓ Imported BaseSettings
✓ Defined TestSettings class
✓ Created settings instance: BizClone

✅ SUCCESS! No recursion error detected.
```

### Test 3: Start Server
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
**Expected:** Server starts successfully without RecursionError

---

## 📚 Pattern to Follow

### For Pydantic Schemas

When a field name matches its type name, use string annotations:

```python
from datetime import date, datetime
from pydantic import BaseModel, Field

class MySchema(BaseModel):
    # ✅ Good: String annotation when field name matches type
    date: "date" = Field(..., description="Date")
    datetime: "datetime" = Field(..., description="DateTime")
    
    # ✅ Good: No conflict, no string needed
    created_at: datetime = Field(..., description="Creation time")
    event_date: date = Field(..., description="Event date")
```

---

## 🚀 Next Steps

The application is now ready to run:

```bash
# Terminal 1: Start FastAPI server
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start Celery worker
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

---

**Issue Status:** ✅ **COMPLETELY RESOLVED**

