#!/usr/bin/env python3
"""
CLI script for controlled processing of call recordings.

This script processes a single recording file by:
1. Creating a database entry in the calls table
2. Triggering the transcription pipeline via Celery

Usage:
    python process_recording.py --file recordings/my_recording.wav
    python process_recording.py --file recordings/my_recording.wav --customer-phone "+15551234567"
"""
import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.db.session import SessionLocal
from app.db.crud import create_call, get_call_by_sid, create_customer, get_customer_by_phone
from app.models.call import CallDirection
from app.workers.tasks import transcribe_audio_task
from app.core.logging import get_logger

logger = get_logger(__name__)


def generate_call_sid_from_filename(filename: str) -> str:
    """Generate a unique call_sid from the filename."""
    # Use filename without extension as base
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
            name=f"Customer {phone_number}"
        )
        logger.info("customer_created", customer_id=customer.id, phone_number=phone_number)
    
    return customer.id


def process_recording(file_path: str, customer_phone: str = "+15551234567", business_phone: str = "+15559876543") -> dict:
    """
    Process a single recording file.
    
    Args:
        file_path: Path to the recording file
        customer_phone: Customer phone number (default: +15551234567)
        business_phone: Business phone number (default: +15559876543)
    
    Returns:
        dict: Processing result with call_id and task_id
    """
    # Validate file exists
    if not os.path.exists(file_path):
        logger.error("file_not_found", file_path=file_path)
        raise FileNotFoundError(f"Recording file not found: {file_path}")
    
    # Get absolute path
    abs_file_path = os.path.abspath(file_path)
    
    # Generate call_sid from filename
    call_sid = generate_call_sid_from_filename(file_path)
    
    logger.info(
        "processing_recording_started",
        file_path=abs_file_path,
        call_sid=call_sid,
        customer_phone=customer_phone
    )
    
    db = SessionLocal()
    
    try:
        # Check if call already exists
        existing_call = get_call_by_sid(db, call_sid)
        if existing_call:
            logger.warning(
                "call_already_exists",
                call_sid=call_sid,
                call_id=str(existing_call.id),
                file_path=abs_file_path
            )
            return {
                "status": "skipped",
                "reason": "Call already processed",
                "call_id": str(existing_call.id),
                "call_sid": call_sid,
                "file_path": abs_file_path
            }
        
        # Ensure customer exists
        customer_id = ensure_customer_exists(db, customer_phone)
        
        # Create call record
        call = create_call(
            db,
            call_sid=call_sid,
            customer_id=customer_id,
            from_number=customer_phone,
            to_number=business_phone,
            direction=CallDirection.INBOUND,
            recording_url=abs_file_path,
            created_at=datetime.utcnow()
        )
        
        logger.info(
            "call_record_created",
            call_id=str(call.id),
            call_sid=call_sid,
            customer_id=customer_id
        )
        
        # Trigger transcription task
        task = transcribe_audio_task.delay(
            call_id=str(call.id),
            audio_file_path=abs_file_path
        )
        
        logger.info(
            "transcription_task_queued",
            call_id=str(call.id),
            call_sid=call_sid,
            task_id=task.id,
            file_path=abs_file_path
        )
        
        return {
            "status": "success",
            "call_id": str(call.id),
            "call_sid": call_sid,
            "task_id": task.id,
            "file_path": abs_file_path,
            "customer_id": customer_id
        }
        
    except Exception as exc:
        logger.error(
            "processing_recording_failed",
            file_path=abs_file_path,
            call_sid=call_sid,
            error=str(exc),
            exc_info=True
        )
        raise

    finally:
        db.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Process a single call recording file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python process_recording.py --file recordings/call_001.wav
  python process_recording.py --file recordings/call_001.wav --customer-phone "+15551234567"
  python process_recording.py --file data/recordings/emergency_call.wav --customer-phone "+15559998888"
        """
    )

    parser.add_argument(
        "--file",
        required=True,
        help="Path to the recording file to process"
    )

    parser.add_argument(
        "--customer-phone",
        default="+15551234567",
        help="Customer phone number (default: +15551234567)"
    )

    parser.add_argument(
        "--business-phone",
        default="+15559876543",
        help="Business phone number (default: +15559876543)"
    )

    args = parser.parse_args()

    try:
        result = process_recording(
            file_path=args.file,
            customer_phone=args.customer_phone,
            business_phone=args.business_phone
        )

        print("\n" + "="*60)
        if result["status"] == "success":
            print("✅ Recording processing initiated successfully!")
            print(f"   Call ID: {result['call_id']}")
            print(f"   Call SID: {result['call_sid']}")
            print(f"   Task ID: {result['task_id']}")
            print(f"   File: {result['file_path']}")
            print(f"   Customer ID: {result['customer_id']}")
            print("\n   The transcription pipeline has been triggered.")
            print("   Check logs for processing status.")
        elif result["status"] == "skipped":
            print("⚠️  Recording already processed!")
            print(f"   Call ID: {result['call_id']}")
            print(f"   Call SID: {result['call_sid']}")
            print(f"   File: {result['file_path']}")
            print(f"   Reason: {result['reason']}")
        print("="*60 + "\n")

        sys.exit(0)

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}\n", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n", file=sys.stderr)
        logger.exception("cli_error")
        sys.exit(1)


if __name__ == "__main__":
    main()

