"""
Core logic for processing a single recording: copy to storage, create call, queue pipeline.
Used by process_recording.py CLI and by POST /api/process-recording.
"""
import os
import shutil
from pathlib import Path
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.db.crud import (
    create_call,
    get_call_by_sid,
    create_customer,
    get_customer_by_phone,
)
from app.models.call import CallDirection
from app.workers.tasks import transcribe_audio_task
from app.core.logging import get_logger
from app.config.settings import settings

logger = get_logger(__name__)


def generate_timestamp_recording_filename(extension: str = ".wav") -> str:
    """Generate a unique timestamp-based recording filename.

    Format: YYYYMMDD_HHMMSS_microseconds.wav
    Example: 20260314_234011_823491.wav
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    return f"{timestamp}{extension}"


def copy_recording_to_storage(source_path: str) -> str:
    """Copy recording to backend/data/recordings with timestamp filename.

    Returns:
        Absolute path of the copied file.
    """
    path = Path(source_path)
    if path.suffix.lower() not in (".wav", ".mp3", ".ogg", ".webm", ".flac", ".m4a"):
        ext = ".wav"
    else:
        ext = path.suffix.lower()
    filename = generate_timestamp_recording_filename(ext)
    recordings_dir = Path(settings.recordings_dir)
    recordings_dir.mkdir(parents=True, exist_ok=True)
    dest_path = recordings_dir / filename
    shutil.copy2(source_path, dest_path)
    return str(dest_path.resolve())


def generate_call_sid_from_filename(filename: str) -> str:
    """Generate a unique call_sid from the filename (stem only)."""
    base = Path(filename).stem
    return f"CLI_{base}"


def ensure_customer_exists(db, phone_number: str) -> str:
    """Ensure customer exists in database, create if not."""
    customer = get_customer_by_phone(db, phone_number)
    if not customer:
        logger.info("creating_new_customer", phone_number=phone_number)
        customer = create_customer(
            db,
            phone_number=phone_number,
            name=f"Customer {phone_number}",
        )
        logger.info(
            "customer_created",
            customer_id=customer.id,
            phone_number=phone_number,
        )
    return customer.id


def process_recording(
    file_path: str,
    customer_phone: str = "+15551234567",
    business_phone: str = "+15559876543",
) -> dict:
    """
    Process a single recording file.

    Copies the file to backend/data/recordings with a timestamp-based unique
    name, then creates the call and queues transcription.

    Args:
        file_path: Path to the recording file
        customer_phone: Customer phone number
        business_phone: Business phone number

    Returns:
        dict: Processing result with call_id and task_id
    """
    if not os.path.exists(file_path):
        logger.error("file_not_found", file_path=file_path)
        raise FileNotFoundError(f"Recording file not found: {file_path}")

    abs_file_path = copy_recording_to_storage(file_path)
    call_sid = generate_call_sid_from_filename(abs_file_path)

    logger.info(
        "processing_recording_started",
        file_path=abs_file_path,
        call_sid=call_sid,
        customer_phone=customer_phone,
    )

    db = SessionLocal()
    try:
        existing_call = get_call_by_sid(db, call_sid)
        if existing_call:
            logger.warning(
                "call_already_exists",
                call_sid=call_sid,
                call_id=str(existing_call.id),
                file_path=abs_file_path,
            )
            return {
                "status": "skipped",
                "reason": "Call already processed",
                "call_id": str(existing_call.id),
                "call_sid": call_sid,
                "file_path": abs_file_path,
            }

        customer_id = ensure_customer_exists(db, customer_phone)
        call = create_call(
            db,
            call_sid=call_sid,
            customer_id=customer_id,
            from_number=customer_phone,
            to_number=business_phone,
            direction=CallDirection.INBOUND,
            recording_url=abs_file_path,
            created_at=datetime.now(timezone.utc),
        )

        logger.info(
            "call_record_created",
            call_id=str(call.id),
            call_sid=call_sid,
            customer_id=customer_id,
        )

        task = transcribe_audio_task.delay(
            call_id=str(call.id),
            audio_file_path=abs_file_path,
        )

        logger.info(
            "transcription_task_queued",
            call_id=str(call.id),
            call_sid=call_sid,
            task_id=task.id,
            file_path=abs_file_path,
        )

        return {
            "status": "success",
            "call_id": str(call.id),
            "call_sid": call_sid,
            "task_id": task.id,
            "file_path": abs_file_path,
            "customer_id": customer_id,
        }

    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        logger.error(
            "processing_recording_failed",
            file_path=abs_file_path,
            call_sid=call_sid,
            error=str(exc),
            exc_info=True,
        )
        raise
    finally:
        db.close()
