"""
Intent classification service using GPT-4o-mini for understanding customer needs.
"""
from typing import Dict, Any, Optional
from enum import Enum
import json

from openai import OpenAI

from app.config.settings import settings
from app.core.logging import get_logger
from app.core.exceptions import AIServiceError

logger = get_logger(__name__)


class IntentType(str, Enum):
    """Supported intent types for customer calls."""
    BOOKING = "booking"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"
    PRICING = "pricing"
    AVAILABILITY = "availability"
    SERVICE_QUESTION = "service_question"
    EMERGENCY = "emergency"
    OTHER = "other"


class IntentClassificationResult:
    """Result of intent classification."""
    
    def __init__(
        self,
        intent: IntentType,
        confidence: float,
        reasoning: Optional[str] = None,
        raw_response: Optional[Dict[str, Any]] = None
    ):
        self.intent = intent
        self.confidence = confidence
        self.reasoning = reasoning
        self.raw_response = raw_response


class IntentClassifier:
    """Service for classifying customer intent using GPT-4o-mini."""
    
    # Few-shot examples for better classification
    FEW_SHOT_EXAMPLES = """
Examples:

1. "Hi, I need to schedule a plumber to fix my sink" -> booking (confidence: 0.95)
2. "Can I reschedule my appointment from tomorrow to next week?" -> reschedule (confidence: 0.98)
3. "I need to cancel my appointment for Friday" -> cancel (confidence: 0.97)
4. "How much do you charge for fixing a leaky faucet?" -> pricing (confidence: 0.92)
5. "Are you available this weekend?" -> availability (confidence: 0.90)
6. "What kind of plumbing services do you offer?" -> service_question (confidence: 0.93)
7. "HELP! My basement is flooding! Water everywhere!" -> emergency (confidence: 0.99)
8. "Just calling to say thanks for the great service" -> other (confidence: 0.85)
"""
    
    SYSTEM_PROMPT = f"""You are an AI assistant that classifies customer intent for a plumbing business.

Classify the customer's message into ONE of these categories:
- booking: Customer wants to schedule a new appointment
- reschedule: Customer wants to change an existing appointment
- cancel: Customer wants to cancel an appointment
- pricing: Customer is asking about costs or pricing
- availability: Customer is asking about availability or hours
- service_question: Customer has questions about services offered
- emergency: Customer has an urgent plumbing emergency (leak, flood, burst pipe, etc.)
- other: Anything else (greetings, thanks, complaints, etc.)

{FEW_SHOT_EXAMPLES}

Respond with ONLY a JSON object in this exact format:
{{"intent": "category_name", "confidence": 0.95, "reasoning": "brief explanation"}}

Be concise and accurate. Confidence should be 0.0-1.0."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize intent classifier.
        
        Args:
            api_key: OpenAI API key (defaults to settings)
            model: Model to use (defaults to gpt-4o-mini)
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model or "gpt-4o-mini"
        self.client = OpenAI(api_key=self.api_key)
        
        logger.info(
            "intent_classifier_initialized",
            model=self.model
        )
    
    def classify(self, text: str) -> IntentClassificationResult:
        """
        Classify customer intent from text.
        
        Args:
            text: Customer message or transcript
        
        Returns:
            IntentClassificationResult: Classification result with confidence
        
        Raises:
            AIServiceError: If classification fails
        """
        if not text or not text.strip():
            raise AIServiceError("Cannot classify empty text")
        
        logger.info(
            "intent_classification_started",
            text_length=len(text),
            text_preview=text[:100]
        )
        
        try:
            # Call GPT-4o-mini
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Classify this message:\n\n{text}"}
                ],
                temperature=0.3,  # Lower temperature for more consistent results
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            content = response.choices[0].message.content
            result_data = json.loads(content)
            
            # Extract intent and confidence
            intent_str = result_data.get("intent", "other")
            confidence = float(result_data.get("confidence", 0.5))
            reasoning = result_data.get("reasoning", "")
            
            # Validate intent
            try:
                intent = IntentType(intent_str)
            except ValueError:
                logger.warning(
                    "invalid_intent_returned",
                    intent=intent_str,
                    defaulting_to="other"
                )
                intent = IntentType.OTHER
            
            # Clamp confidence to 0-1
            confidence = max(0.0, min(1.0, confidence))
            
            result = IntentClassificationResult(
                intent=intent,
                confidence=confidence,
                reasoning=reasoning,
                raw_response=result_data
            )
            
            logger.info(
                "intent_classification_completed",
                intent=intent.value,
                confidence=confidence,
                reasoning=reasoning
            )
            
            return result
            
        except json.JSONDecodeError as exc:
            logger.error(
                "intent_classification_json_error",
                error=str(exc),
                response_content=content if 'content' in locals() else None,
                exc_info=True
            )
            raise AIServiceError(f"Failed to parse classification response: {str(exc)}")
            
        except Exception as exc:
            logger.error(
                "intent_classification_failed",
                error=str(exc),
                exc_info=True
            )
            raise AIServiceError(f"Intent classification failed: {str(exc)}")

