"""
Entity extraction service using GPT-4o-mini for extracting structured data.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json

from openai import OpenAI

from app.config.settings import settings
from app.core.logging import get_logger
from app.core.exceptions import AIServiceError

logger = get_logger(__name__)


class ExtractedEntities:
    """Container for extracted entities."""
    
    def __init__(self, data: Dict[str, Any]):
        self.date_time_text = data.get("date_time_text")
        self.requested_date = data.get("requested_date")
        self.requested_time = data.get("requested_time")
        
        self.address = data.get("address")
        self.city = data.get("city")
        self.state = data.get("state")
        self.zip_code = data.get("zip_code")
        self.location_text = data.get("location_text")
        
        self.service_type = data.get("service_type")
        self.service_description = data.get("service_description")
        
        self.urgency = data.get("urgency", "medium")
        self.urgency_reason = data.get("urgency_reason")
        
        self.contact_phone = data.get("contact_phone")
        self.contact_email = data.get("contact_email")
        self.contact_name = data.get("contact_name")
        
        self.notes = data.get("notes")
        self.raw_response = data


class EntityExtractor:
    """Service for extracting entities from transcripts using GPT-4o-mini."""
    
    SYSTEM_PROMPT = """You are an AI assistant that extracts structured information from customer service calls for a plumbing business.

Extract the following information from the transcript:

1. **Date/Time Information:**
   - date_time_text: Original text mentioning date/time (e.g., "tomorrow at 2pm")
   - requested_date: ISO date if mentioned (YYYY-MM-DD)
   - requested_time: Time if mentioned (HH:MM format, 24-hour)

2. **Location Information:**
   - location_text: Original text mentioning location
   - address: Full street address if mentioned
   - city: City name
   - state: State abbreviation
   - zip_code: ZIP code

3. **Service Information:**
   - service_type: Type of service (e.g., "sink_repair", "drain_cleaning", "toilet_fix", "water_heater", "pipe_repair", "emergency_leak")
   - service_description: Description of the problem

4. **Urgency:**
   - urgency: One of: "low", "medium", "high", "urgent", "emergency"
   - urgency_reason: Why it's urgent (if mentioned)

5. **Contact Information:**
   - contact_phone: Phone number if mentioned
   - contact_email: Email if mentioned
   - contact_name: Name if mentioned

6. **Notes:**
   - notes: Any other important information

Respond with ONLY a JSON object. Use null for missing information.

Example:
{
  "date_time_text": "tomorrow at 2pm",
  "requested_date": "2026-02-28",
  "requested_time": "14:00",
  "location_text": "my house on 123 Main St",
  "address": "123 Main St",
  "city": "Springfield",
  "state": "IL",
  "zip_code": "62701",
  "service_type": "sink_repair",
  "service_description": "leaking kitchen sink",
  "urgency": "medium",
  "urgency_reason": null,
  "contact_phone": null,
  "contact_email": null,
  "contact_name": null,
  "notes": null
}
"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize entity extractor.
        
        Args:
            api_key: OpenAI API key (defaults to settings)
            model: Model to use (defaults to gpt-4o-mini)
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model or "gpt-4o-mini"
        self.client = OpenAI(api_key=self.api_key)
        
        logger.info(
            "entity_extractor_initialized",
            model=self.model
        )
    
    def extract(self, text: str, context: Optional[Dict[str, Any]] = None) -> ExtractedEntities:
        """
        Extract entities from text.
        
        Args:
            text: Customer message or transcript
            context: Optional context (e.g., current date, customer info)
        
        Returns:
            ExtractedEntities: Extracted entities
        
        Raises:
            AIServiceError: If extraction fails
        """
        if not text or not text.strip():
            raise AIServiceError("Cannot extract entities from empty text")
        
        logger.info(
            "entity_extraction_started",
            text_length=len(text),
            text_preview=text[:100]
        )
        
        # Build user message with context
        user_message = f"Extract entities from this transcript:\n\n{text}"
        if context:
            user_message += f"\n\nContext: {json.dumps(context)}"
        
        try:
            # Call GPT-4o-mini
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            content = response.choices[0].message.content
            result_data = json.loads(content)
            
            result = ExtractedEntities(result_data)
            
            logger.info(
                "entity_extraction_completed",
                service_type=result.service_type,
                urgency=result.urgency,
                has_date=result.requested_date is not None,
                has_location=result.address is not None
            )
            
            return result
            
        except json.JSONDecodeError as exc:
            logger.error(
                "entity_extraction_json_error",
                error=str(exc),
                response_content=content if 'content' in locals() else None,
                exc_info=True
            )
            raise AIServiceError(f"Failed to parse extraction response: {str(exc)}")
            
        except Exception as exc:
            logger.error(
                "entity_extraction_failed",
                error=str(exc),
                exc_info=True
            )
            raise AIServiceError(f"Entity extraction failed: {str(exc)}")

