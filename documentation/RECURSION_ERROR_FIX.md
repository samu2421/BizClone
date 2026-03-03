# 🔧 RecursionError Fix - Complete Solution

**Date:** 2026-03-03  
**Issue:** `RecursionError: maximum recursion depth exceeded while getting the repr of an object`  
**Status:** ✅ **RESOLVED**

---

## 🔴 The Problem

When starting the FastAPI server with `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`, the application crashed with:

```
RecursionError: maximum recursion depth exceeded while getting the repr of an object
```

This occurred during application startup when SQLAlchemy models were being loaded and represented.

---

## 🔍 Root Cause Analysis

The recursion error was caused by **circular references in SQLAlchemy model relationships**:

### The Circular Chain:
1. `Customer` has relationship to `Call` and `Appointment`
2. `Call` has relationship back to `Customer` and to `Appointment`
3. `Appointment` has relationship back to both `Call` and `Customer`

### Why It Failed:
When Python/Pydantic tried to represent these objects (via `__repr__`):
- Customer's `__repr__` → accesses `calls` relationship
- Call's `__repr__` → accesses `customer` relationship
- Customer's `__repr__` → accesses `calls` relationship (LOOP!)
- **Infinite recursion** → Stack overflow

---

## ✅ The Complete Solution

### Three-Part Fix:

#### 1. **Use `back_populates` instead of `backref`**
- `backref` creates implicit bidirectional relationships
- `back_populates` requires explicit definition on both sides
- This prevents hidden circular references

#### 2. **Add `repr=False` to all relationships**
- Prevents relationships from being included in `__repr__`
- Breaks the recursion chain
- Models can still be represented, but without loading related objects

#### 3. **Add `lazy="select"` for explicit loading**
- Defines when related objects are loaded
- `"select"` = load on access (default, but explicit is better)
- Prevents eager loading that could trigger recursion

---

## 📝 Files Modified

### 1. `backend/app/models/customer.py`
```python
# Relationships
calls = relationship("Call", back_populates="customer", cascade="all, delete-orphan", lazy="select", repr=False)
appointments = relationship("Appointment", back_populates="customer", cascade="all, delete-orphan", lazy="select", repr=False)
```

### 2. `backend/app/models/call.py`
```python
# Relationships
customer = relationship("Customer", back_populates="calls", lazy="select", repr=False)
transcripts = relationship("Transcript", back_populates="call", cascade="all, delete-orphan", lazy="select", repr=False)
events = relationship("CallEvent", back_populates="call", cascade="all, delete-orphan", lazy="select", repr=False)
appointments = relationship("Appointment", back_populates="call", cascade="all, delete-orphan", lazy="select", repr=False)
```

### 3. `backend/app/models/appointment.py`
```python
# Relationships
call = relationship("Call", back_populates="appointments", lazy="select", repr=False)
customer = relationship("Customer", back_populates="appointments", lazy="select", repr=False)
```

### 4. `backend/app/models/transcript.py`
```python
# Relationships
call = relationship("Call", back_populates="transcripts", lazy="select", repr=False)
```

### 5. `backend/app/models/call_event.py`
```python
# Relationships
call = relationship("Call", back_populates="events", lazy="select", repr=False)
```

---

## ✅ Verification

### Test 1: Import Models
```bash
cd backend
python -c "from app.models import Customer, Call, Appointment; print('✅ Models OK')"
```
**Result:** ✅ Success

### Test 2: Create Model Instance
```bash
cd backend
python -c "from app.models import Customer; c = Customer(phone_number='+1234567890', name='Test'); print(repr(c))"
```
**Result:** ✅ Success - No recursion

### Test 3: Start Server
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
**Result:** ✅ Server starts successfully

---

## 📚 Key Learnings

1. **Always use `back_populates` over `backref`** in bidirectional relationships
2. **Add `repr=False`** to relationships to prevent repr recursion
3. **Be explicit with `lazy` loading strategy** for clarity
4. **Test model imports** before starting the full application
5. **Circular relationships require careful handling** in ORMs

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

# Terminal 3: Process a recording
cd backend
python process_recording.py --file ../data/recordings/call_01.wav
```

---

**Issue Status:** ✅ **COMPLETELY RESOLVED**

