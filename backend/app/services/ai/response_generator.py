"""
Response Generator Service - Generates natural language responses based on conversation state.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
import json
from openai import OpenAI
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.logging import get_logger
from app.models.conversation_state import ConversationState, ConversationStatus
from app.core.business_data_loader import search_business_knowledge

logger = get_logger(__name__)


@dataclass
class ResponseResult:
    """Result from response generation."""
    response_text: str
    suggested_next_state: Optional[str] = None
    requires_human: bool = False
    confidence: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


class ResponseGenerator:
    """
    Generates natural language responses for the AI voice assistant.
    
    Uses GPT-4o-mini to create contextual, professional responses based on:
    - Current conversation state
    - Customer intent
    - Extracted entities
    - Business context
    """
    
    def __init__(self):
        """Initialize the response generator."""
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o-mini"
        self.business_name = "BizClone Plumbing Services"
        
    def generate_response(
        self,
        conversation_state: str,
        intent: str,
        transcript: str,
        extracted_entities: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[Dict[str, Any]] = None,
        is_emergency: bool = False,
        db: Optional[Session] = None
    ) -> ResponseResult:
        """
        Generate a natural language response.

        Args:
            conversation_state: Current conversation state
            intent: Classified customer intent
            transcript: Customer's message
            extracted_entities: Extracted appointment data
            conversation_context: Previous conversation context
            is_emergency: Whether this is an emergency situation
            db: Optional database session for business knowledge lookup

        Returns:
            ResponseResult with generated response and metadata
        """
        logger.info(
            "generating_response",
            state=conversation_state,
            intent=intent,
            is_emergency=is_emergency
        )

        # Get relevant business knowledge if db session provided
        business_knowledge = ""
        if db and transcript:
            business_knowledge = search_business_knowledge(db, transcript)

        try:
            # Build system prompt
            system_prompt = self._build_system_prompt(business_knowledge)

            # Build user prompt
            user_prompt = self._build_user_prompt(
                conversation_state=conversation_state,
                intent=intent,
                transcript=transcript,
                extracted_entities=extracted_entities,
                conversation_context=conversation_context,
                is_emergency=is_emergency
            )
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result_text = response.choices[0].message.content
            result_data = json.loads(result_text)
            
            logger.info(
                "response_generated",
                response_length=len(result_data.get("response", "")),
                suggested_state=result_data.get("suggested_next_state")
            )
            
            return ResponseResult(
                response_text=result_data.get("response", ""),
                suggested_next_state=result_data.get("suggested_next_state"),
                requires_human=result_data.get("requires_human", False),
                confidence=result_data.get("confidence", 0.8),
                metadata=result_data.get("metadata", {})
            )
            
        except json.JSONDecodeError as e:
            logger.error("response_json_decode_error", error=str(e))
            return self._fallback_response(conversation_state, intent, is_emergency)
        except Exception as e:
            logger.error("response_generation_error", error=str(e))
            return self._fallback_response(conversation_state, intent, is_emergency)
    
    def _build_system_prompt(self, business_knowledge: str = "") -> str:
        """Build the system prompt for response generation."""
        base_prompt = f"""You are an AI voice assistant for {self.business_name}, a professional plumbing company.

Your role is to:
1. Provide helpful, professional, and empathetic responses
2. Gather necessary information for appointments
3. Handle emergencies with urgency and care
4. Provide pricing and service information when asked
5. Schedule, reschedule, or cancel appointments

Guidelines:
- Be warm, professional, and concise
- For emergencies, prioritize immediate help
- Ask for missing information one question at a time
- Confirm details before finalizing appointments
- Use natural, conversational language
- Keep responses under 3 sentences when possible"""

        if business_knowledge:
            base_prompt += f"\n\n**Business Knowledge:**\n{business_knowledge}"

        base_prompt += """

Output Format (JSON):
{{
  "response": "Your natural language response here",
  "suggested_next_state": "next_conversation_state",
  "requires_human": false,
  "confidence": 0.9,
  "metadata": {{"key": "value"}}
}}"""

        return base_prompt

    def _build_user_prompt(
        self,
        conversation_state: str,
        intent: str,
        transcript: str,
        extracted_entities: Optional[Dict[str, Any]],
        conversation_context: Optional[Dict[str, Any]],
        is_emergency: bool
    ) -> str:
        """Build the user prompt with conversation context."""
        prompt_parts = [
            f"**Current Conversation State:** {conversation_state}",
            f"**Customer Intent:** {intent}",
            f"**Customer Said:** \"{transcript}\"",
            f"**Is Emergency:** {is_emergency}"
        ]

        if extracted_entities:
            prompt_parts.append(f"**Extracted Information:** {json.dumps(extracted_entities, indent=2)}")

        if conversation_context:
            prompt_parts.append(f"**Previous Context:** {json.dumps(conversation_context, indent=2)}")

        # Add state-specific instructions
        state_instructions = self._get_state_instructions(conversation_state, intent, is_emergency)
        if state_instructions:
            prompt_parts.append(f"**Instructions:** {state_instructions}")

        return "\n\n".join(prompt_parts)

    def _get_state_instructions(self, state: str, intent: str, is_emergency: bool) -> str:
        """Get specific instructions based on conversation state."""
        if is_emergency:
            return "This is an EMERGENCY. Acknowledge urgency, confirm we're sending help immediately, and get their location if not provided."

        instructions = {
            ConversationState.INITIAL.value: "Greet the customer warmly and ask how you can help.",
            ConversationState.GREETING.value: "Acknowledge their greeting and ask what plumbing issue they need help with.",
            ConversationState.INTENT_IDENTIFIED.value: "Acknowledge their request and start gathering necessary information.",
            ConversationState.COLLECTING_INFO.value: "Ask for the next missing piece of information (date, time, location, or service details).",
            ConversationState.AWAITING_DATE.value: "Ask when they would like the appointment scheduled.",
            ConversationState.AWAITING_LOCATION.value: "Ask for their service address.",
            ConversationState.AWAITING_SERVICE_DETAILS.value: "Ask them to describe the plumbing issue in more detail.",
            ConversationState.AWAITING_CONFIRMATION.value: "Summarize the appointment details and ask for confirmation.",
            ConversationState.CONFIRMED.value: "Confirm the appointment is scheduled and provide next steps.",
            ConversationState.PROVIDING_INFO.value: "Provide the requested information clearly and ask if they need anything else.",
            ConversationState.SCHEDULING.value: "Confirm available time slots and finalize the appointment.",
            ConversationState.RESCHEDULING.value: "Acknowledge the reschedule request and ask for the new preferred date/time.",
            ConversationState.CANCELING.value: "Acknowledge the cancellation request and confirm it's been processed.",
            ConversationState.EMERGENCY_HANDLING.value: "Prioritize immediate assistance, confirm location, and assure help is on the way.",
            ConversationState.ESCALATION_NEEDED.value: "Politely inform them you're connecting them with a specialist who can better assist.",
            ConversationState.COMPLETED.value: "Thank them for calling and wish them a great day.",
        }

        return instructions.get(state, "Respond appropriately to the customer's message.")

    def _fallback_response(self, state: str, intent: str, is_emergency: bool) -> ResponseResult:
        """Generate a fallback response when AI generation fails."""
        if is_emergency:
            return ResponseResult(
                response_text="I understand this is an emergency. We're dispatching a plumber to your location immediately. Please stay on the line.",
                suggested_next_state=ConversationState.EMERGENCY_HANDLING.value,
                requires_human=True,
                confidence=1.0
            )

        fallback_responses = {
            "booking": "I'd be happy to help you schedule an appointment. Could you please tell me when you'd like us to come out?",
            "pricing": "I can help you with pricing information. What service are you interested in?",
            "emergency": "This sounds urgent. We'll get someone to you right away. What's your address?",
            "reschedule": "I can help you reschedule your appointment. What date and time works better for you?",
            "cancel": "I can help you cancel your appointment. Can you confirm which appointment you'd like to cancel?",
        }

        response_text = fallback_responses.get(
            intent,
            "Thank you for calling BizClone Plumbing Services. How can I help you today?"
        )

        return ResponseResult(
            response_text=response_text,
            suggested_next_state=ConversationState.COLLECTING_INFO.value,
            requires_human=False,
            confidence=0.5
        )

