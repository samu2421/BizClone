"""
Conversation state manager for tracking multi-turn dialogues.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import (
    ConversationStateModel,
    ConversationStatus,
    ConversationState,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConversationManager:
    """Manages conversation state and dialogue flow."""
    
    # State transition rules
    STATE_TRANSITIONS = {
        ConversationState.INITIAL: [
            ConversationState.GREETING,
            ConversationState.INTENT_IDENTIFIED,
            ConversationState.EMERGENCY_HANDLING,
        ],
        ConversationState.GREETING: [
            ConversationState.INTENT_IDENTIFIED,
            ConversationState.EMERGENCY_HANDLING,
        ],
        ConversationState.INTENT_IDENTIFIED: [
            ConversationState.COLLECTING_INFO,
            ConversationState.PROVIDING_INFO,
            ConversationState.SCHEDULING,
            ConversationState.RESCHEDULING,
            ConversationState.CANCELING,
            ConversationState.EMERGENCY_HANDLING,
            ConversationState.COMPLETED,
        ],
        ConversationState.COLLECTING_INFO: [
            ConversationState.AWAITING_DATE,
            ConversationState.AWAITING_LOCATION,
            ConversationState.AWAITING_SERVICE_DETAILS,
            ConversationState.AWAITING_CONFIRMATION,
            ConversationState.SCHEDULING,
            ConversationState.ESCALATION_NEEDED,
        ],
        ConversationState.AWAITING_DATE: [
            ConversationState.COLLECTING_INFO,
            ConversationState.AWAITING_CONFIRMATION,
            ConversationState.ESCALATION_NEEDED,
        ],
        ConversationState.AWAITING_LOCATION: [
            ConversationState.COLLECTING_INFO,
            ConversationState.AWAITING_CONFIRMATION,
            ConversationState.ESCALATION_NEEDED,
        ],
        ConversationState.AWAITING_SERVICE_DETAILS: [
            ConversationState.COLLECTING_INFO,
            ConversationState.AWAITING_CONFIRMATION,
            ConversationState.ESCALATION_NEEDED,
        ],
        ConversationState.AWAITING_CONFIRMATION: [
            ConversationState.CONFIRMED,
            ConversationState.COLLECTING_INFO,
            ConversationState.SCHEDULING,
            ConversationState.ESCALATION_NEEDED,
        ],
        ConversationState.CONFIRMED: [
            ConversationState.SCHEDULING,
            ConversationState.COMPLETED,
        ],
        ConversationState.SCHEDULING: [
            ConversationState.COMPLETED,
            ConversationState.ESCALATION_NEEDED,
        ],
        ConversationState.RESCHEDULING: [
            ConversationState.COMPLETED,
            ConversationState.ESCALATION_NEEDED,
        ],
        ConversationState.CANCELING: [
            ConversationState.COMPLETED,
        ],
        ConversationState.EMERGENCY_HANDLING: [
            ConversationState.ESCALATION_NEEDED,
            ConversationState.SCHEDULING,
            ConversationState.COMPLETED,
        ],
        ConversationState.PROVIDING_INFO: [
            ConversationState.COMPLETED,
            ConversationState.COLLECTING_INFO,
        ],
        ConversationState.ESCALATION_NEEDED: [
            ConversationState.COMPLETED,
        ],
    }
    
    def __init__(self, db: Session):
        """Initialize conversation manager."""
        self.db = db
    
    def create_conversation(
        self,
        call_id: str,
        customer_id: str,
        initial_state: ConversationState = ConversationState.INITIAL,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConversationStateModel:
        """
        Create a new conversation state.
        
        Args:
            call_id: Call ID
            customer_id: Customer ID
            initial_state: Initial conversation state
            context: Initial context data
        
        Returns:
            ConversationStateModel: Created conversation state
        """
        conversation = ConversationStateModel(
            call_id=call_id,
            customer_id=customer_id,
            status=ConversationStatus.ACTIVE,
            current_state=initial_state,
            context=context or {},
            turn_count=0,
            needs_human=False,
            is_emergency=False,
        )
        
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        
        logger.info(
            "conversation_created",
            conversation_id=conversation.id,
            call_id=call_id,
            initial_state=initial_state.value
        )
        
        return conversation
    
    def get_conversation_by_call_id(
        self,
        call_id: str
    ) -> Optional[ConversationStateModel]:
        """Get conversation state by call ID."""
        return self.db.query(ConversationStateModel).filter(
            ConversationStateModel.call_id == call_id
        ).first()

    def transition_state(
        self,
        conversation: ConversationStateModel,
        new_state: ConversationState,
        message: Optional[str] = None,
        response: Optional[str] = None,
        context_updates: Optional[Dict[str, Any]] = None,
    ) -> ConversationStateModel:
        """
        Transition conversation to a new state.

        Args:
            conversation: Conversation state object
            new_state: New state to transition to
            message: Customer message
            response: System response
            context_updates: Updates to context data

        Returns:
            ConversationStateModel: Updated conversation state
        """
        # Validate transition
        current_state = conversation.current_state
        allowed_transitions = self.STATE_TRANSITIONS.get(current_state, [])

        if new_state not in allowed_transitions:
            logger.warning(
                "invalid_state_transition",
                conversation_id=conversation.id,
                from_state=current_state.value,
                to_state=new_state.value,
                allowed=[s.value for s in allowed_transitions]
            )

        # Update state
        conversation.previous_state = current_state
        conversation.current_state = new_state
        conversation.turn_count += 1
        conversation.last_interaction_at = datetime.now(timezone.utc)

        if message:
            conversation.last_message = message
        if response:
            conversation.last_response = response

        # Update context
        if context_updates:
            if conversation.context is None:
                conversation.context = {}
            conversation.context.update(context_updates)

        # Update status based on state
        if new_state == ConversationState.COMPLETED:
            conversation.status = ConversationStatus.COMPLETED
            conversation.completed_at = datetime.now(timezone.utc)
        elif new_state == ConversationState.ESCALATION_NEEDED:
            conversation.status = ConversationStatus.ESCALATED
            conversation.needs_human = True
        elif new_state in [
            ConversationState.AWAITING_DATE,
            ConversationState.AWAITING_LOCATION,
            ConversationState.AWAITING_SERVICE_DETAILS,
            ConversationState.AWAITING_CONFIRMATION,
        ]:
            conversation.status = ConversationStatus.AWAITING_RESPONSE
        else:
            conversation.status = ConversationStatus.ACTIVE

        self.db.commit()
        self.db.refresh(conversation)

        logger.info(
            "conversation_state_transitioned",
            conversation_id=conversation.id,
            from_state=current_state.value,
            to_state=new_state.value,
            turn_count=conversation.turn_count
        )

        return conversation

    def update_context(
        self,
        conversation: ConversationStateModel,
        updates: Dict[str, Any]
    ) -> ConversationStateModel:
        """
        Update conversation context.

        Args:
            conversation: Conversation state object
            updates: Context updates

        Returns:
            ConversationStateModel: Updated conversation state
        """
        if conversation.context is None:
            conversation.context = {}

        conversation.context.update(updates)
        conversation.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(conversation)

        logger.info(
            "conversation_context_updated",
            conversation_id=conversation.id,
            updates=list(updates.keys())
        )

        return conversation

    def mark_emergency(
        self,
        conversation: ConversationStateModel
    ) -> ConversationStateModel:
        """
        Mark conversation as emergency.

        Args:
            conversation: Conversation state object

        Returns:
            ConversationStateModel: Updated conversation state
        """
        conversation.is_emergency = True
        conversation.current_state = ConversationState.EMERGENCY_HANDLING
        conversation.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(conversation)

        logger.warning(
            "conversation_marked_emergency",
            conversation_id=conversation.id,
            call_id=conversation.call_id
        )

        return conversation

    def determine_next_state(
        self,
        conversation: ConversationStateModel,
        intent: str,
        extracted_entities: Optional[Dict[str, Any]] = None
    ) -> ConversationState:
        """
        Determine next conversation state based on intent and entities.

        Args:
            conversation: Current conversation state
            intent: Classified intent
            extracted_entities: Extracted entity data

        Returns:
            ConversationState: Recommended next state
        """
        current_state = conversation.current_state

        # Emergency always goes to emergency handling
        if intent == "emergency":
            return ConversationState.EMERGENCY_HANDLING

        # From initial/greeting, identify intent
        if current_state in [ConversationState.INITIAL, ConversationState.GREETING]:
            return ConversationState.INTENT_IDENTIFIED

        # From intent identified, determine action
        if current_state == ConversationState.INTENT_IDENTIFIED:
            if intent == "booking":
                return ConversationState.COLLECTING_INFO
            elif intent == "reschedule":
                return ConversationState.RESCHEDULING
            elif intent == "cancel":
                return ConversationState.CANCELING
            elif intent in ["pricing", "availability", "service_question"]:
                return ConversationState.PROVIDING_INFO
            else:
                return ConversationState.COMPLETED

        # Check if we have all required info
        if current_state == ConversationState.COLLECTING_INFO:
            missing_fields = self._get_missing_fields(extracted_entities)

            if not missing_fields:
                return ConversationState.AWAITING_CONFIRMATION
            elif "date" in missing_fields or "time" in missing_fields:
                return ConversationState.AWAITING_DATE
            elif "address" in missing_fields or "location" in missing_fields:
                return ConversationState.AWAITING_LOCATION
            elif "service_type" in missing_fields:
                return ConversationState.AWAITING_SERVICE_DETAILS
            else:
                return ConversationState.COLLECTING_INFO

        # From awaiting states, go back to collecting
        if current_state in [
            ConversationState.AWAITING_DATE,
            ConversationState.AWAITING_LOCATION,
            ConversationState.AWAITING_SERVICE_DETAILS,
        ]:
            return ConversationState.COLLECTING_INFO

        # From confirmation, schedule
        if current_state == ConversationState.AWAITING_CONFIRMATION:
            return ConversationState.SCHEDULING

        # Default to completed
        return ConversationState.COMPLETED

    def _get_missing_fields(
        self,
        extracted_entities: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Get list of missing required fields."""
        if not extracted_entities:
            return ["date", "location", "service_type"]

        missing = []

        if not extracted_entities.get("requested_date"):
            missing.append("date")
        if not extracted_entities.get("address"):
            missing.append("location")
        if not extracted_entities.get("service_type"):
            missing.append("service_type")

        return missing

