#!/usr/bin/env python3
"""
CLI script for controlled processing of call recordings.

This script processes a single recording file by:
1. Copying the file to backend/data/recordings with a timestamp-based unique name
2. Creating a database entry in the calls table
3. Triggering the transcription pipeline via Celery

Usage:
    python process_recording.py --file recordings/my_recording.wav
    python process_recording.py --file recordings/my_recording.wav --customer-phone "+15551234567"
"""
import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.services.recording_processor import process_recording
from app.core.logging import get_logger

logger = get_logger(__name__)


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
        """,
    )

    parser.add_argument(
        "--file",
        required=True,
        help="Path to the recording file to process",
    )

    parser.add_argument(
        "--customer-phone",
        default="+15551234567",
        help="Customer phone number (default: +15551234567)",
    )

    parser.add_argument(
        "--business-phone",
        default="+15559876543",
        help="Business phone number (default: +15559876543)",
    )

    args = parser.parse_args()

    try:
        result = process_recording(
            file_path=args.file,
            customer_phone=args.customer_phone,
            business_phone=args.business_phone,
        )

        print("\n" + "=" * 60)
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
        print("=" * 60 + "\n")

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
