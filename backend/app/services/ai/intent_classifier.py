"""
Intent classification service using Groq API (low-cost) for understanding customer needs.
Falls back to keyword-based classification when Groq API is unavailable.
"""
import re
import json
from typing import Dict, Any, Optional
from enum import Enum

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


# Keywords for fallback when Groq API is unavailable
_FALLBACK_INTENT_PATTERNS = [
    (IntentType.EMERGENCY, re.compile(
        r"\b(flooding|flooded|flood|burst\s*pipe|water\s*everywhere|"
        r"gas\s*leak|sewage|emergency|urgent|asap|immediately|"
        r"right\s*now|disaster|water\s*pouring)\b", re.I
    )),
    (IntentType.CANCEL, re.compile(
        r"\b(cancel|cancellation|cancelled|need\s*to\s*cancel|"
        r"won't\s*make\s*it|can't\s*come)\b", re.I
    )),
    (IntentType.RESCHEDULE, re.compile(
        r"\b(reschedule|rescheduling|change\s*appointment|"
        r"move\s*appointment|different\s*time|different\s*day)\b", re.I
    )),
    (IntentType.PRICING, re.compile(
        r"\b(how\s*much|price|cost|costs|charge|charging|"
        r"rate|rates|fee|fees|estimate|quote|pricing)\b", re.I
    )),
    (IntentType.AVAILABILITY, re.compile(
        r"\b(available|availability|when\s*are\s*you|open\s*today|"
        r"hours|hours\s*of\s*operation|this\s*weekend|weekend)\b", re.I
    )),
    (IntentType.SERVICE_QUESTION, re.compile(
        r"\b(what\s*services|do\s*you\s*offer|offer|types\s*of|"
        r"kind\s*of\s*work|plumbing\s*services)\b", re.I
    )),
    (IntentType.BOOKING, re.compile(
        r"\b(book|booking|schedule|scheduled|appointment|"
        r"come\s*out|send\s*someone|fix\s*my|repair|"
        r"need\s*a\s*plumber|plumber\s*to)\b", re.I
    )),
]

SYSTEM_PROMPT = """You are an AI assistant that classifies customer intent for a plumbing business.

Classify the customer's message into ONE of these categories:
- booking: Customer wants to schedule a new appointment
- reschedule: Customer wants to change an existing appointment
- cancel: Customer wants to cancel an appointment
- pricing: Customer is asking about costs or pricing
- availability: Customer is asking about availability or hours
- service_question: Customer has questions about services offered
- emergency: Customer has an urgent plumbing emergency (leak, flood, burst pipe, etc.)
- other: Anything else (greetings, thanks, complaints, etc.)

Respond with ONLY a JSON object in this exact format:
{"intent": "category_name", "confidence": 0.95, "reasoning": "brief explanation"}

Be concise and accurate. Confidence should be 0.0-1.0."""


class IntentClassifier:
    """Service for classifying customer intent using Groq API (low-cost)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model
        self._client = None
        logger.info(
            "intent_classifier_initialized",
            model=self.model,
            provider="groq"
        )

    def _get_client(self):
        """Lazy-initialize Groq client."""
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError as exc:
                raise AIServiceError(
                    "Groq SDK not installed. Run: pip install groq"
                ) from exc
        return self._client

    def _classify_fallback(self, text: str) -> IntentClassificationResult:
        """Keyword-based fallback when Groq API is unavailable."""
        text_lower = text.lower().strip()
        for intent, pattern in _FALLBACK_INTENT_PATTERNS:
            if pattern.search(text_lower):
                logger.info(
                    "intent_classification_fallback_used",
                    intent=intent.value,
                    reason="Groq API unavailable"
                )
                return IntentClassificationResult(
                    intent=intent,
                    confidence=0.75,
                    reasoning="Fallback: keyword match (Groq API unavailable)",
                    raw_response={"source": "fallback", "intent": intent.value}
                )
        return IntentClassificationResult(
            intent=IntentType.OTHER,
            confidence=0.5,
            reasoning="Fallback: no keyword match (Groq API unavailable)",
            raw_response={"source": "fallback", "intent": "other"}
        )

    def classify(self, text: str) -> IntentClassificationResult:
        """
        Classify customer intent from text using Groq API.

        Args:
            text: Customer message or transcript

        Returns:
            IntentClassificationResult: Classification result with confidence
        """
        if not text or not text.strip():
            raise AIServiceError("Cannot classify empty text")

        logger.info(
            "intent_classification_started",
            text_length=len(text),
            text_preview=text[:100]
        )

        # Use keyword fallback if no Groq API key
        if not self.api_key or not self.api_key.strip():
            logger.warning("groq_api_key_not_configured_using_fallback")
            return self._classify_fallback(text)

        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Classify this message:\n\n{text}"}
                ],
                temperature=0.3,
                max_tokens=150,
            )

            content = response.choices[0].message.content
            result_data = json.loads(content)

            intent_str = result_data.get("intent", "other")
            confidence = float(result_data.get("confidence", 0.5))
            reasoning = result_data.get("reasoning", "")

            try:
                intent = IntentType(intent_str)
            except ValueError:
                logger.warning(
                    "invalid_intent_returned",
                    intent=intent_str,
                    defaulting_to="other"
                )
                intent = IntentType.OTHER

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
            logger.warning(
                "groq_api_error_using_fallback",
                error=str(exc),
                error_type=type(exc).__name__
            )
            return self._classify_fallback(text)
