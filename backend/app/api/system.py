"""
System visibility API: list entities and trigger recording processing.
Reads from PostgreSQL; non-blocking; proper error handling.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.crud import (
    list_calls,
    list_transcripts,
    list_appointments,
    list_conversation_states,
    get_records_by_type,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["System"])


def _serialize_call(call) -> dict:
    """Serialize Call model to JSON-safe dict."""
    return {
        "id": call.id,
        "call_sid": call.call_sid,
        "customer_id": call.customer_id,
        "from_number": call.from_number,
        "to_number": call.to_number,
        "direction": getattr(call.direction, "value", str(call.direction)),
        "status": getattr(call.status, "value", str(call.status)),
        "recording_url": getattr(call, "recording_url", None),
        "summary": getattr(call, "summary", None),
        "created_at": call.created_at.isoformat() if call.created_at else None,
        "updated_at": call.updated_at.isoformat() if call.updated_at else None,
    }


def _serialize_transcript(t) -> dict:
    """Serialize Transcript model to JSON-safe dict."""
    return {
        "id": t.id,
        "call_id": t.call_id,
        "text": t.text,
        "language": t.language,
        "confidence": t.confidence,
        "model_used": t.model_used,
        "audio_file_path": t.audio_file_path,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _serialize_appointment(a) -> dict:
    """Serialize Appointment model to JSON-safe dict."""
    return {
        "id": a.id,
        "call_id": a.call_id,
        "customer_id": a.customer_id,
        "status": getattr(a.status, "value", str(a.status)),
        "urgency": getattr(a.urgency, "value", str(a.urgency)),
        "service_type": a.service_type,
        "requested_date": a.requested_date.isoformat() if a.requested_date else None,
        "scheduled_time_start": (
            a.scheduled_time_start.isoformat() if a.scheduled_time_start else None
        ),
        "scheduled_time_end": (
            a.scheduled_time_end.isoformat() if a.scheduled_time_end else None
        ),
        "address": a.address,
        "contact_name": a.contact_name,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


def _serialize_conversation_state(cs) -> dict:
    """Serialize ConversationState model to JSON-safe dict."""
    return {
        "id": cs.id,
        "call_id": cs.call_id,
        "customer_id": cs.customer_id,
        "appointment_id": cs.appointment_id,
        "status": getattr(cs.status, "value", str(cs.status)),
        "current_state": getattr(
            cs.current_state, "value", str(cs.current_state)
        ),
        "turn_count": cs.turn_count,
        "created_at": cs.created_at.isoformat() if cs.created_at else None,
        "updated_at": cs.updated_at.isoformat() if cs.updated_at else None,
    }


def _serialize_record(r) -> dict:
    """Serialize Record model to JSON-safe dict."""
    return {
        "id": r.id,
        "record_type": r.record_type,
        "entity_id": r.entity_id,
        "entity_type": r.entity_type,
        "payload": r.payload,
        "summary": r.summary,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.get("/calls", status_code=status.HTTP_200_OK)
def get_calls(
    limit: int = 100,
    db: Session = Depends(get_db),
) -> dict:
    """List recent calls from PostgreSQL. Fast, non-blocking."""
    try:
        calls = list_calls(db, limit=min(limit, 500))
        return {"calls": [_serialize_call(c) for c in calls], "count": len(calls)}
    except Exception as e:
        logger.exception("api_list_calls_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list calls",
        ) from e


@router.get("/transcripts", status_code=status.HTTP_200_OK)
def get_transcripts(
    limit: int = 100,
    db: Session = Depends(get_db),
) -> dict:
    """List recent transcripts from PostgreSQL."""
    try:
        items = list_transcripts(db, limit=min(limit, 500))
        return {
            "transcripts": [_serialize_transcript(t) for t in items],
            "count": len(items),
        }
    except Exception as e:
        logger.exception("api_list_transcripts_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list transcripts",
        ) from e


@router.get("/appointments", status_code=status.HTTP_200_OK)
def get_appointments(
    limit: int = 100,
    db: Session = Depends(get_db),
) -> dict:
    """List recent appointments from PostgreSQL."""
    try:
        items = list_appointments(db, limit=min(limit, 500))
        return {
            "appointments": [_serialize_appointment(a) for a in items],
            "count": len(items),
        }
    except Exception as e:
        logger.exception("api_list_appointments_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list appointments",
        ) from e


@router.get("/conversation-states", status_code=status.HTTP_200_OK)
def get_conversation_states(
    limit: int = 100,
    db: Session = Depends(get_db),
) -> dict:
    """List recent conversation states from PostgreSQL."""
    try:
        items = list_conversation_states(db, limit=min(limit, 500))
        return {
            "conversation_states": [
                _serialize_conversation_state(cs) for cs in items
            ],
            "count": len(items),
        }
    except Exception as e:
        logger.exception("api_list_conversation_states_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list conversation states",
        ) from e


@router.get("/records", status_code=status.HTTP_200_OK)
def get_records(
    record_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> dict:
    """List audit records (event log). Optional filter by record_type."""
    try:
        from app.models import Record
        from sqlalchemy import desc
        limit = min(limit, 500)
        if record_type:
            items = get_records_by_type(db, record_type=record_type, limit=limit)
        else:
            items = (
                db.query(Record)
                .order_by(desc(Record.created_at))
                .limit(limit)
                .all()
            )
        return {
            "records": [_serialize_record(r) for r in items],
            "count": len(items),
        }
    except Exception as e:
        logger.exception("api_list_records_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list records",
        ) from e


class ProcessRecordingBody(BaseModel):
    """Body for POST /api/process-recording (path-based)."""
    file_path: str
    customer_phone: Optional[str] = "+15551234567"
    business_phone: Optional[str] = "+15559876543"


@router.post("/process-recording", status_code=status.HTTP_202_ACCEPTED)
def post_process_recording(
    body: ProcessRecordingBody,
) -> dict:
    """
    Trigger processing of a recording by path.

    The file must exist on the server at the given path. The pipeline will
    copy it to backend/data/recordings with a timestamp name, create the call,
    and queue transcription → intent → entity extraction → scheduling.
    """
    try:
        from app.services.recording_processor import process_recording
        result = process_recording(
            file_path=body.file_path,
            customer_phone=body.customer_phone or "+15551234567",
            business_phone=body.business_phone or "+15559876543",
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("api_process_recording_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Processing failed",
        ) from e
