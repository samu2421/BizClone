"""
Celery tasks for background processing.
"""
from typing import Optional
from celery import Task
from celery.exceptions import Retry

from app.workers.celery_app import celery_app
from app.core.logging import get_logger
from app.core.exceptions import TranscriptionError
from app.services.voice import WhisperTranscriptionService
from app.services.ai import (
    IntentClassifier,
    EntityExtractor,
    ConversationManager,
    PriorityDetector,
    ResponseGenerator,
)
from app.services.scheduling import SchedulingService
from app.db.session import SessionLocal
from app.db.crud import (
    get_call_by_id,
    create_transcript,
    update_call,
    update_call_by_sid,
    create_call_event,
    create_appointment,
    update_appointment,
    get_appointment_by_id,
    create_conversation_state,
    get_conversation_state_by_call_id,
)
from app.models import ConversationState, AppointmentStatus

logger = get_logger(__name__)


class TranscriptionTask(Task):
    """Base task for transcription with retry logic."""
    
    autoretry_for = (TranscriptionError, Exception)
    retry_kwargs = {"max_retries": 3, "countdown": 5}
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes max backoff
    retry_jitter = True


@celery_app.task(
    bind=True,
    base=TranscriptionTask,
    name="app.workers.tasks.transcribe_audio_task"
)
def transcribe_audio_task(
    self,
    call_id: str,
    audio_file_path: str,
    language: Optional[str] = None
) -> dict:
    """
    Transcribe an audio file and store the result in the database.
    
    Args:
        call_id: UUID of the call
        audio_file_path: Path to the audio file
        language: Optional language code
    
    Returns:
        dict: Transcription result metadata
    """
    logger.info(
        "transcription_task_started",
        task_id=self.request.id,
        call_id=call_id,
        audio_file_path=audio_file_path,
        retry_count=self.request.retries
    )
    
    db = SessionLocal()
    
    try:
        # Get call from database
        call = get_call_by_id(db, call_id=call_id)
        if not call:
            logger.error("call_not_found", call_id=call_id)
            raise ValueError(f"Call not found: {call_id}")
        
        # Create transcription event
        create_call_event(
            db,
            call_id=call_id,
            event_type="transcription_started",
            description="Audio transcription started",
            event_data={
                "task_id": self.request.id,
                "audio_file_path": audio_file_path,
                "retry_count": self.request.retries
            }
        )
        
        # Initialize transcription service
        transcription_service = WhisperTranscriptionService()
        
        # Transcribe audio
        result = transcription_service.transcribe_file(
            audio_file_path=audio_file_path,
            language=language
        )
        
        # Store transcript in database
        transcript = create_transcript(
            db,
            call_id=call_id,
            text=result.text,
            language=result.language,
            confidence=result.confidence,
            model_used=result.model_name,
            processing_time_seconds=result.processing_time,
            audio_duration=result.duration,
            audio_file_path=audio_file_path
        )
        
        # Update call with transcript summary
        update_call_by_sid(
            db,
            call_sid=call.call_sid,
            summary=result.text[:500] if len(result.text) > 500 else result.text
        )
        
        # Create completion event
        create_call_event(
            db,
            call_id=call_id,
            event_type="transcription_completed",
            description="Audio transcription completed successfully",
            event_data={
                "task_id": self.request.id,
                "transcript_id": str(transcript.id),
                "text_length": len(result.text),
                "language": result.language,
                "confidence": result.confidence,
                "processing_time_seconds": result.processing_time
            }
        )
        
        logger.info(
            "transcription_task_completed",
            task_id=self.request.id,
            call_id=call_id,
            transcript_id=str(transcript.id),
            text_length=len(result.text),
            language=result.language,
            confidence=result.confidence
        )

        # Queue intent classification task
        try:
            classify_intent_task.delay(call_id, result.text)
            logger.info(
                "intent_classification_queued",
                call_id=call_id,
                task_id=self.request.id
            )
        except Exception as queue_exc:
            logger.warning(
                "intent_classification_queue_failed",
                call_id=call_id,
                error=str(queue_exc)
            )
            # Don't fail transcription if queuing fails

        return {
            "status": "success",
            "call_id": call_id,
            "transcript_id": str(transcript.id),
            "text": result.text,
            "language": result.language,
            "confidence": result.confidence,
            "processing_time_seconds": result.processing_time
        }
        
    except Exception as exc:
        logger.error(
            "transcription_task_failed",
            task_id=self.request.id,
            call_id=call_id,
            audio_file_path=audio_file_path,
            retry_count=self.request.retries,
            error=str(exc),
            exc_info=True
        )
        
        # Create failure event
        try:
            create_call_event(
                db,
                call_id=call_id,
                event_type="transcription_failed",
                description=f"Transcription failed: {str(exc)}",
                event_data={
                    "task_id": self.request.id,
                    "error": str(exc),
                    "retry_count": self.request.retries
                }
            )
        except Exception:
            pass  # Don't fail if event creation fails
        
        # Retry the task
        raise self.retry(exc=exc)
        
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.classify_intent")
def classify_intent_task(
    self,
    call_id: str,
    transcript_text: str
) -> dict:
    """
    Classify customer intent from transcript using GPT-4o-mini.

    Args:
        call_id: UUID of the call
        transcript_text: Transcribed text to classify

    Returns:
        dict: Classification result with intent and confidence
    """
    logger.info(
        "intent_classification_task_started",
        call_id=call_id,
        task_id=self.request.id,
        text_length=len(transcript_text)
    )

    db = SessionLocal()

    try:
        # Get call from database
        call = get_call_by_id(db, call_id)
        if not call:
            logger.error(
                "intent_classification_call_not_found",
                call_id=call_id
            )
            return {"error": "Call not found", "call_id": call_id}

        # Create event for classification started
        try:
            create_call_event(
                db,
                call_id=call_id,
                event_type="intent_classification_started",
                metadata={"task_id": self.request.id}
            )
        except Exception:
            pass  # Don't fail if event creation fails

        # Initialize classifier
        classifier = IntentClassifier()

        # Classify intent
        result = classifier.classify(transcript_text)

        # Update call with intent and confidence
        update_call(
            db,
            call_id=call_id,
            intent=result.intent.value,
            intent_confidence=result.confidence
        )

        # Create event for classification completed
        try:
            create_call_event(
                db,
                call_id=call_id,
                event_type="intent_classification_completed",
                metadata={
                    "task_id": self.request.id,
                    "intent": result.intent.value,
                    "confidence": result.confidence,
                    "reasoning": result.reasoning
                }
            )
        except Exception:
            pass  # Don't fail if event creation fails

        logger.info(
            "intent_classification_task_completed",
            call_id=call_id,
            task_id=self.request.id,
            intent=result.intent.value,
            confidence=result.confidence
        )

        # Queue entity extraction task
        try:
            extract_entities_task.delay(call_id, transcript_text)
            logger.info(
                "entity_extraction_queued",
                call_id=call_id,
                task_id=self.request.id
            )
        except Exception as queue_exc:
            logger.warning(
                "entity_extraction_queue_failed",
                call_id=call_id,
                error=str(queue_exc)
            )
            # Don't fail intent classification if queuing fails

        return {
            "call_id": call_id,
            "intent": result.intent.value,
            "confidence": result.confidence,
            "reasoning": result.reasoning
        }

    except Exception as exc:
        logger.error(
            "intent_classification_task_failed",
            call_id=call_id,
            task_id=self.request.id,
            error=str(exc),
            exc_info=True
        )

        # Create event for classification failed
        try:
            create_call_event(
                db,
                call_id=call_id,
                event_type="intent_classification_failed",
                metadata={
                    "task_id": self.request.id,
                    "error": str(exc)
                }
            )
        except Exception:
            pass  # Don't fail if event creation fails

        return {
            "error": str(exc),
            "call_id": call_id
        }

    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.extract_entities")
def extract_entities_task(
    self,
    call_id: str,
    transcript_text: str
) -> dict:
    """
    Extract entities from transcript using GPT-4o-mini.

    Args:
        call_id: UUID of the call
        transcript_text: Transcribed text to extract entities from

    Returns:
        dict: Extraction result with entities
    """
    logger.info(
        "entity_extraction_task_started",
        call_id=call_id,
        task_id=self.request.id,
        text_length=len(transcript_text)
    )

    db = SessionLocal()

    try:
        # Get call from database
        call = get_call_by_id(db, call_id)
        if not call:
            logger.error(
                "entity_extraction_call_not_found",
                call_id=call_id
            )
            return {"error": "Call not found", "call_id": call_id}

        # Create event for extraction started
        try:
            create_call_event(
                db,
                call_id=call_id,
                event_type="entity_extraction_started",
                metadata={"task_id": self.request.id}
            )
        except Exception:
            pass  # Don't fail if event creation fails

        # Initialize extractor
        extractor = EntityExtractor()

        # Extract entities
        result = extractor.extract(transcript_text)

        # Create appointment record with extracted data
        appointment = create_appointment(
            db,
            call_id=call_id,
            customer_id=call.customer_id,
            date_time_text=result.date_time_text,
            requested_date=result.requested_date,
            location_text=result.location_text,
            address=result.address,
            city=result.city,
            state=result.state,
            zip_code=result.zip_code,
            service_type=result.service_type,
            service_description=result.service_description,
            urgency=result.urgency or "medium",
            urgency_reason=result.urgency_reason,
            contact_phone=result.contact_phone,
            contact_email=result.contact_email,
            contact_name=result.contact_name,
            notes=result.notes
        )

        # Create or update conversation state
        try:
            conversation = get_conversation_state_by_call_id(db, call_id)
            if not conversation:
                conversation = create_conversation_state(
                    db,
                    call_id=call_id,
                    customer_id=call.customer_id,
                    current_state=ConversationState.COLLECTING_INFO,
                    appointment_id=appointment.id,
                    context={
                        "extracted_entities": {
                            "service_type": result.service_type,
                            "urgency": result.urgency,
                            "has_date": result.requested_date is not None,
                            "has_location": result.address is not None,
                        }
                    }
                )
            else:
                # Update existing conversation with appointment
                manager = ConversationManager(db)
                manager.update_context(
                    conversation,
                    {
                        "appointment_id": appointment.id,
                        "extracted_entities": {
                            "service_type": result.service_type,
                            "urgency": result.urgency,
                            "has_date": result.requested_date is not None,
                            "has_location": result.address is not None,
                        }
                    }
                )
        except Exception as conv_exc:
            logger.warning(
                "conversation_state_update_failed",
                call_id=call_id,
                error=str(conv_exc)
            )
            # Don't fail extraction if conversation update fails

        # Create event for extraction completed
        try:
            create_call_event(
                db,
                call_id=call_id,
                event_type="entity_extraction_completed",
                metadata={
                    "task_id": self.request.id,
                    "appointment_id": appointment.id,
                    "service_type": result.service_type,
                    "urgency": result.urgency
                }
            )
        except Exception:
            pass  # Don't fail if event creation fails

        logger.info(
            "entity_extraction_task_completed",
            call_id=call_id,
            task_id=self.request.id,
            appointment_id=appointment.id,
            service_type=result.service_type,
            urgency=result.urgency
        )

        # Queue scheduling task to find and assign a time slot
        try:
            # Get intent from call record
            intent = call.intent or "booking"
            schedule_appointment_task.delay(
                call_id,
                str(appointment.id),
                intent
            )
            logger.info(
                "scheduling_task_queued",
                call_id=call_id,
                appointment_id=appointment.id,
                intent=intent,
                task_id=self.request.id
            )
        except Exception as queue_exc:
            logger.warning(
                "scheduling_task_queue_failed",
                call_id=call_id,
                appointment_id=appointment.id,
                error=str(queue_exc)
            )
            # Don't fail entity extraction if queuing fails

        return {
            "call_id": call_id,
            "appointment_id": appointment.id,
            "service_type": result.service_type,
            "urgency": result.urgency,
            "has_date": result.requested_date is not None,
            "has_location": result.address is not None
        }

    except Exception as exc:
        logger.error(
            "entity_extraction_task_failed",
            call_id=call_id,
            task_id=self.request.id,
            error=str(exc),
            exc_info=True
        )

        # Create event for extraction failed
        try:
            create_call_event(
                db,
                call_id=call_id,
                event_type="entity_extraction_failed",
                metadata={
                    "task_id": self.request.id,
                    "error": str(exc)
                }
            )
        except Exception:
            pass  # Don't fail if event creation fails

        return {
            "error": str(exc),
            "call_id": call_id
        }

    finally:
        db.close()


@celery_app.task(name="detect_priority", bind=True)
def detect_priority_task(self, call_id: str) -> dict:
    """
    Detect priority level and emergency status from transcript.

    Args:
        call_id: UUID of the call

    Returns:
        dict: Priority detection result
    """
    db = SessionLocal()

    try:
        # Get call
        call = get_call_by_id(db, call_id)
        if not call:
            logger.error("priority_detection_call_not_found", call_id=call_id)
            return {"error": "Call not found", "call_id": call_id}

        # Get transcript
        if not call.transcript or not call.transcript.text:
            logger.warning(
                "priority_detection_no_transcript",
                call_id=call_id
            )
            return {
                "call_id": call_id,
                "skipped": True,
                "reason": "No transcript available"
            }

        transcript_text = call.transcript.text

        # Initialize detector
        detector = PriorityDetector()

        # Detect priority
        result = detector.detect(
            transcript_text,
            intent=call.intent
        )

        # Update call with emergency flag
        if result.is_emergency:
            update_call(
                db,
                call.id,
                is_emergency="yes"
            )

        # Update appointment urgency if exists
        if call.appointments:
            appointment = call.appointments[0]
            update_appointment(
                db,
                appointment.id,
                urgency=result.urgency_level,
                urgency_reason=result.reason
            )

        # Update conversation state if emergency
        if result.is_emergency:
            conversation = get_conversation_state_by_call_id(db, call_id)
            if conversation:
                manager = ConversationManager(db)
                manager.mark_emergency(conversation)

        # Create event for priority detection
        try:
            create_call_event(
                db,
                call_id=call_id,
                event_type="priority_detected",
                metadata={
                    "task_id": self.request.id,
                    "is_emergency": result.is_emergency,
                    "urgency_level": result.urgency_level,
                    "confidence": result.confidence,
                    "detected_keywords": result.detected_keywords,
                    "reason": result.reason,
                    "should_escalate": detector.should_escalate(result)
                }
            )
        except Exception:
            pass  # Don't fail if event creation fails

        logger.info(
            "priority_detection_task_completed",
            call_id=call_id,
            task_id=self.request.id,
            is_emergency=result.is_emergency,
            urgency_level=result.urgency_level,
            confidence=result.confidence
        )

        return {
            "call_id": call_id,
            "is_emergency": result.is_emergency,
            "urgency_level": result.urgency_level,
            "confidence": result.confidence,
            "detected_keywords": result.detected_keywords,
            "reason": result.reason,
            "should_escalate": detector.should_escalate(result)
        }

    except Exception as exc:
        logger.error(
            "priority_detection_task_failed",
            call_id=call_id,
            task_id=self.request.id,
            error=str(exc),
            exc_info=True
        )

        # Create event for detection failed
        try:
            create_call_event(
                db,
                call_id=call_id,
                event_type="priority_detection_failed",
                metadata={
                    "task_id": self.request.id,
                    "error": str(exc)
                }
            )
        except Exception:
            pass  # Don't fail if event creation fails

        return {
            "error": str(exc),
            "call_id": call_id
        }

    finally:
        db.close()


@celery_app.task(name="schedule_appointment", bind=True)
def schedule_appointment_task(
    self,
    call_id: str,
    appointment_id: str,
    intent: str
) -> dict:
    """
    Schedule an appointment using the SchedulingService.

    This task is called after entity extraction to find and assign
    a specific time slot for the appointment.

    Args:
        call_id: UUID of the call
        appointment_id: UUID of the appointment
        intent: Customer intent (booking, emergency, etc.)

    Returns:
        dict: Scheduling result
    """
    logger.info(
        "schedule_appointment_task_started",
        call_id=call_id,
        appointment_id=appointment_id,
        intent=intent,
        task_id=self.request.id
    )

    db = SessionLocal()

    try:
        # Get appointment
        appointment = get_appointment_by_id(db, appointment_id)
        if not appointment:
            logger.error(
                "schedule_appointment_not_found",
                appointment_id=appointment_id
            )
            return {"error": "Appointment not found", "appointment_id": appointment_id}

        # Initialize scheduling service
        scheduler = SchedulingService(db)

        # Determine if this is an emergency
        is_emergency = (
            intent == "emergency" or
            appointment.urgency == "emergency"
        )

        # Schedule the appointment
        result = scheduler.schedule_appointment(
            customer_id=appointment.customer_id,
            service_type=appointment.service_type or "general_plumbing",
            requested_time=appointment.requested_date,
            duration_minutes=60,  # Default 1 hour
            is_emergency=is_emergency,
            notes=appointment.notes,
            location=appointment.address or appointment.location_text
        )

        if result.success:
            # Update appointment with scheduled time
            update_appointment(
                db,
                appointment_id=appointment_id,
                scheduled_time_start=result.scheduled_time,
                scheduled_time_end=result.end_time,
                status=AppointmentStatus.SCHEDULED.value
            )

            # Create event
            create_call_event(
                db,
                call_id=call_id,
                event_type="appointment_scheduled",
                metadata={
                    "task_id": self.request.id,
                    "appointment_id": appointment_id,
                    "scheduled_time": result.scheduled_time.isoformat(),
                    "is_emergency": is_emergency
                }
            )

            logger.info(
                "schedule_appointment_task_completed",
                call_id=call_id,
                appointment_id=appointment_id,
                scheduled_time=result.scheduled_time.isoformat(),
                task_id=self.request.id
            )

            return {
                "success": True,
                "call_id": call_id,
                "appointment_id": appointment_id,
                "scheduled_time": result.scheduled_time.isoformat(),
                "message": result.message
            }
        else:
            # Scheduling failed - mark as pending
            update_appointment(
                db,
                appointment_id=appointment_id,
                status=AppointmentStatus.PENDING.value
            )

            # Create event
            create_call_event(
                db,
                call_id=call_id,
                event_type="appointment_scheduling_failed",
                metadata={
                    "task_id": self.request.id,
                    "appointment_id": appointment_id,
                    "reason": result.message
                }
            )

            logger.warning(
                "schedule_appointment_task_failed_no_slots",
                call_id=call_id,
                appointment_id=appointment_id,
                reason=result.message,
                task_id=self.request.id
            )

            return {
                "success": False,
                "call_id": call_id,
                "appointment_id": appointment_id,
                "message": result.message
            }

    except Exception as exc:
        logger.error(
            "schedule_appointment_task_error",
            call_id=call_id,
            appointment_id=appointment_id,
            task_id=self.request.id,
            error=str(exc),
            exc_info=True
        )

        # Create event for scheduling error
        try:
            create_call_event(
                db,
                call_id=call_id,
                event_type="appointment_scheduling_error",
                metadata={
                    "task_id": self.request.id,
                    "appointment_id": appointment_id,
                    "error": str(exc)
                }
            )
        except Exception:
            pass

        return {
            "error": str(exc),
            "call_id": call_id,
            "appointment_id": appointment_id
        }

    finally:
        db.close()

