"""
Twilio webhook endpoints for handling inbound calls and status updates.
"""
from fastapi import APIRouter, Form, Request, Response, status, Depends
from fastapi.responses import PlainTextResponse
from typing import Optional
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_call_event
from app.core.exceptions import TwilioWebhookError
from app.config.settings import settings
from app.db import get_db
from app.db.crud import (
    get_or_create_customer,
    create_call,
    get_call_by_sid,
    update_call_by_sid,
    create_call_event,
)
from app.models import CallDirection
from app.models.call import CallStatus as CallStatusEnum
from app.services.voice import AudioHandler, RecordingDownloader
from app.workers.tasks import transcribe_audio_task

logger = get_logger(__name__)
router = APIRouter(prefix="/webhooks/twilio", tags=["Twilio Webhooks"])

# Initialize services
audio_handler = AudioHandler()
recording_downloader = RecordingDownloader()


def generate_twiml_response(message: str, record: bool = True) -> str:
    """
    Generate TwiML XML response.
    
    Args:
        message: Message to speak to the caller
        record: Whether to record the call
    
    Returns:
        str: TwiML XML string
    """
    twiml = '<?xml version="1.0" encoding="UTF-8"?>'
    twiml += '<Response>'
    twiml += f'<Say voice="Polly.Joanna">{message}</Say>'
    
    if record:
        # Record the call and send to status callback
        twiml += '<Record '
        twiml += 'maxLength="300" '  # 5 minutes max
        twiml += 'timeout="5" '
        twiml += 'transcribe="false" '
        twiml += f'action="{settings.twilio_webhook_base_url}/webhooks/twilio/recording" '
        twiml += 'method="POST" '
        twiml += '/>'
    
    twiml += '</Response>'
    return twiml


@router.post(
    "/voice",
    response_class=PlainTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Inbound Call Handler",
    description="Handle inbound calls from Twilio"
)
async def handle_inbound_call(
    request: Request,
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    CallStatus: str = Form(...),
    Direction: str = Form(...),
    FromCity: Optional[str] = Form(None),
    FromState: Optional[str] = Form(None),
    FromCountry: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    """
    Handle inbound call from Twilio.
    
    This endpoint receives the initial webhook when a call comes in.
    It responds with TwiML to greet the caller and start recording.
    
    Args:
        CallSid: Unique call identifier
        From: Caller's phone number
        To: Called number (our Twilio number)
        CallStatus: Current call status
        Direction: Call direction (inbound/outbound)
        FromCity: Caller's city (optional)
        FromState: Caller's state (optional)
        FromCountry: Caller's country (optional)
    
    Returns:
        PlainTextResponse: TwiML XML response
    """
    try:
        # Log the incoming call
        log_call_event(
            logger,
            "call_received",
            CallSid,
            from_number=From,
            to_number=To,
            call_status=CallStatus,
            direction=Direction,
            from_city=FromCity,
            from_state=FromState,
            from_country=FromCountry,
        )

        # Get or create customer
        customer = get_or_create_customer(
            db,
            phone_number=From,
            name=None,  # Will be updated later if we get it
        )

        # Create call record
        call = create_call(
            db,
            call_sid=CallSid,
            customer_id=customer.id,
            from_number=From,
            to_number=To,
            direction=CallDirection.INBOUND if Direction == "inbound" else CallDirection.OUTBOUND,
            status=CallStatusEnum.RINGING,
            from_city=FromCity,
            from_state=FromState,
            from_country=FromCountry,
        )

        # Create call event
        create_call_event(
            db,
            call_id=call.id,
            event_type="call_received",
            description=f"Inbound call from {From}",
            event_data={
                "call_status": CallStatus,
                "from_city": FromCity,
                "from_state": FromState,
                "from_country": FromCountry,
            }
        )
        
        # Generate greeting message
        greeting = (
            f"Thank you for calling {settings.business_name}. "
            "Your call is important to us. "
            "Please describe your plumbing issue and we'll assist you shortly."
        )
        
        # Generate TwiML response with recording
        twiml = generate_twiml_response(greeting, record=True)
        
        logger.info(
            "twiml_response_generated",
            call_sid=CallSid,
            recording_enabled=True
        )
        
        return PlainTextResponse(content=twiml, media_type="application/xml")
        
    except Exception as exc:
        logger.error(
            "inbound_call_error",
            call_sid=CallSid,
            error=str(exc),
            exc_info=True
        )
        
        # Return error TwiML
        error_twiml = generate_twiml_response(
            "We're sorry, but we're experiencing technical difficulties. Please try again later.",
            record=False
        )
        return PlainTextResponse(content=error_twiml, media_type="application/xml")


@router.post(
    "/recording",
    response_class=PlainTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Recording Handler",
    description="Handle recording completion callback from Twilio"
)
async def handle_recording(
    request: Request,
    CallSid: str = Form(...),
    RecordingUrl: str = Form(...),
    RecordingSid: str = Form(...),
    RecordingDuration: str = Form(...),
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    """
    Handle recording completion callback.
    
    This endpoint is called when the recording is complete.
    It will trigger the transcription process.
    
    Args:
        CallSid: Unique call identifier
        RecordingUrl: URL of the recording
        RecordingSid: Unique recording identifier
        RecordingDuration: Duration of recording in seconds
    
    Returns:
        PlainTextResponse: TwiML response
    """
    try:
        log_call_event(
            logger,
            "recording_received",
            CallSid,
            recording_url=RecordingUrl,
            recording_sid=RecordingSid,
            duration_seconds=RecordingDuration,
        )

        # Download recording from Twilio to local storage
        try:
            audio_content, content_type = await recording_downloader.download_twilio_recording(
                recording_url=RecordingUrl,
                call_sid=CallSid
            )

            # Save to local storage
            audio_metadata = await audio_handler.save_recording(
                call_sid=CallSid,
                content=audio_content,
                content_type=content_type
            )

            local_file_path = audio_metadata.file_path

            logger.info(
                "recording_downloaded_and_saved",
                call_sid=CallSid,
                recording_sid=RecordingSid,
                local_path=local_file_path
            )
        except Exception as download_exc:
            logger.error(
                "recording_download_failed",
                call_sid=CallSid,
                recording_sid=RecordingSid,
                error=str(download_exc),
                exc_info=True
            )
            # Continue even if download fails - we still have the URL
            local_file_path = None

        # Update call with recording information
        update_data = {
            "recording_url": RecordingUrl,
            "recording_sid": RecordingSid,
            "recording_duration": int(RecordingDuration),
        }
        if local_file_path:
            update_data["recording_url"] = local_file_path  # Store local path instead

        call = update_call_by_sid(db, call_sid=CallSid, **update_data)

        if call:
            # Create call event for recording completion
            create_call_event(
                db,
                call_id=call.id,
                event_type="recording_completed",
                description=f"Recording completed: {RecordingDuration}s",
                event_data={
                    "recording_url": RecordingUrl,
                    "recording_sid": RecordingSid,
                    "duration_seconds": RecordingDuration,
                    "local_file_path": local_file_path,
                }
            )

        # Queue transcription task only when we have local audio file
        try:
            if local_file_path:
                call = get_call_by_sid(db, call_sid=CallSid)
                if call:
                    task = transcribe_audio_task.delay(
                        call_id=str(call.id),
                        audio_file_path=local_file_path
                    )

                    logger.info(
                        "transcription_task_queued",
                        call_sid=CallSid,
                        call_id=str(call.id),
                        task_id=task.id,
                        local_file_path=local_file_path
                    )

                    # Create event for task queued
                    create_call_event(
                        db,
                        call_id=call.id,
                        event_type="transcription_queued",
                        description="Transcription task queued for processing",
                        event_data={
                            "task_id": task.id,
                            "audio_file_path": local_file_path,
                            "recording_sid": RecordingSid
                        }
                    )
            else:
                logger.warning(
                    "transcription_skipped_no_local_file",
                    call_sid=CallSid,
                    recording_sid=RecordingSid,
                    reason="Recording download failed, no local file to transcribe"
                )
        except Exception as queue_exc:
            logger.error(
                "transcription_queue_failed",
                call_sid=CallSid,
                recording_sid=RecordingSid,
                error=str(queue_exc),
                exc_info=True
            )
            # Don't fail the recording callback if queuing fails
        
        # Thank the caller and end the call
        twiml = generate_twiml_response(
            "Thank you for your call. We have recorded your message and will get back to you soon. Goodbye!",
            record=False
        )
        
        return PlainTextResponse(content=twiml, media_type="application/xml")
        
    except Exception as exc:
        logger.error(
            "recording_handler_error",
            call_sid=CallSid,
            recording_sid=RecordingSid,
            error=str(exc),
            exc_info=True
        )
        raise TwilioWebhookError(f"Failed to process recording: {str(exc)}")


@router.post(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Call Status Handler",
    description="Handle call status updates from Twilio"
)
async def handle_call_status(
    request: Request,
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    CallDuration: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> dict:
    """
    Handle call status updates.
    
    This endpoint receives status updates throughout the call lifecycle.
    
    Args:
        CallSid: Unique call identifier
        CallStatus: Current call status
        CallDuration: Duration of call (when completed)
    
    Returns:
        dict: Acknowledgment response
    """
    log_call_event(
        logger,
        "call_status_update",
        CallSid,
        call_status=CallStatus,
        call_duration=CallDuration,
    )

    # Update call status in database
    update_data = {"status": CallStatus}
    if CallDuration:
        update_data["duration_seconds"] = int(CallDuration)

    call = update_call_by_sid(db, call_sid=CallSid, **update_data)

    if call:
        # Create call event for status update
        create_call_event(
            db,
            call_id=call.id,
            event_type=f"call_status_{CallStatus.lower().replace('-', '_')}",
            description=f"Call status updated to {CallStatus}",
            event_data={
                "call_status": CallStatus,
                "call_duration": CallDuration,
            }
        )

    return {"status": "received", "call_sid": CallSid}

