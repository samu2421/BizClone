"""
Tests for conversation state manager.
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

from app.services.ai.conversation_manager import ConversationManager
from app.models import (
    ConversationStateModel,
    ConversationStatus,
    ConversationState,
)


class TestConversationManager:
    """Test conversation state manager."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()
    
    @pytest.fixture
    def manager(self, mock_db):
        """Create conversation manager."""
        return ConversationManager(mock_db)
    
    @pytest.fixture
    def mock_conversation(self):
        """Create mock conversation state."""
        conversation = Mock(spec=ConversationStateModel)
        conversation.id = "conv-123"
        conversation.call_id = "call-456"
        conversation.customer_id = "customer-789"
        conversation.status = ConversationStatus.ACTIVE
        conversation.current_state = ConversationState.INITIAL
        conversation.previous_state = None
        conversation.context = {}
        conversation.turn_count = 0
        conversation.needs_human = False
        conversation.is_emergency = False
        return conversation
    
    def test_manager_initialization(self, manager, mock_db):
        """Test manager initializes correctly."""
        assert manager.db == mock_db
    
    def test_create_conversation(self, manager, mock_db):
        """Test creating a new conversation."""
        # Setup
        mock_conversation = Mock(spec=ConversationStateModel)
        mock_conversation.id = "conv-123"
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock(side_effect=lambda x: setattr(x, 'id', 'conv-123'))
        
        # Execute
        result = manager.create_conversation(
            call_id="call-456",
            customer_id="customer-789",
            initial_state=ConversationState.INITIAL,
            context={"test": "data"}
        )
        
        # Verify
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    def test_transition_state_valid(self, manager, mock_db, mock_conversation):
        """Test valid state transition."""
        # Execute
        result = manager.transition_state(
            mock_conversation,
            ConversationState.GREETING,
            message="Hello",
            response="Hi there!",
            context_updates={"greeted": True}
        )
        
        # Verify
        assert mock_conversation.previous_state == ConversationState.INITIAL
        assert mock_conversation.current_state == ConversationState.GREETING
        assert mock_conversation.turn_count == 1
        assert mock_conversation.last_message == "Hello"
        assert mock_conversation.last_response == "Hi there!"
        assert mock_conversation.context["greeted"] is True
        mock_db.commit.assert_called_once()
    
    def test_transition_to_completed(self, manager, mock_db, mock_conversation):
        """Test transition to completed state."""
        # Execute
        result = manager.transition_state(
            mock_conversation,
            ConversationState.COMPLETED
        )
        
        # Verify
        assert mock_conversation.current_state == ConversationState.COMPLETED
        assert mock_conversation.status == ConversationStatus.COMPLETED
        assert mock_conversation.completed_at is not None
    
    def test_transition_to_escalation(self, manager, mock_db, mock_conversation):
        """Test transition to escalation state."""
        # Execute
        result = manager.transition_state(
            mock_conversation,
            ConversationState.ESCALATION_NEEDED
        )
        
        # Verify
        assert mock_conversation.current_state == ConversationState.ESCALATION_NEEDED
        assert mock_conversation.status == ConversationStatus.ESCALATED
        assert mock_conversation.needs_human is True
    
    def test_transition_to_awaiting_response(self, manager, mock_db, mock_conversation):
        """Test transition to awaiting response state."""
        # Execute
        result = manager.transition_state(
            mock_conversation,
            ConversationState.AWAITING_DATE
        )
        
        # Verify
        assert mock_conversation.current_state == ConversationState.AWAITING_DATE
        assert mock_conversation.status == ConversationStatus.AWAITING_RESPONSE
    
    def test_update_context(self, manager, mock_db, mock_conversation):
        """Test updating conversation context."""
        # Execute
        result = manager.update_context(
            mock_conversation,
            {"new_field": "value", "count": 42}
        )
        
        # Verify
        assert mock_conversation.context["new_field"] == "value"
        assert mock_conversation.context["count"] == 42
        mock_db.commit.assert_called_once()
    
    def test_mark_emergency(self, manager, mock_db, mock_conversation):
        """Test marking conversation as emergency."""
        # Execute
        result = manager.mark_emergency(mock_conversation)

        # Verify
        assert mock_conversation.is_emergency is True
        assert mock_conversation.current_state == ConversationState.EMERGENCY_HANDLING
        mock_db.commit.assert_called_once()

    def test_determine_next_state_emergency(self, manager, mock_conversation):
        """Test determining next state for emergency."""
        # Execute
        next_state = manager.determine_next_state(
            mock_conversation,
            intent="emergency"
        )

        # Verify
        assert next_state == ConversationState.EMERGENCY_HANDLING

    def test_determine_next_state_from_initial(self, manager, mock_conversation):
        """Test determining next state from initial."""
        # Execute
        next_state = manager.determine_next_state(
            mock_conversation,
            intent="booking"
        )

        # Verify
        assert next_state == ConversationState.INTENT_IDENTIFIED

    def test_determine_next_state_booking(self, manager, mock_conversation):
        """Test determining next state for booking intent."""
        mock_conversation.current_state = ConversationState.INTENT_IDENTIFIED

        # Execute
        next_state = manager.determine_next_state(
            mock_conversation,
            intent="booking"
        )

        # Verify
        assert next_state == ConversationState.COLLECTING_INFO

    def test_determine_next_state_with_all_info(self, manager, mock_conversation):
        """Test determining next state when all info collected."""
        mock_conversation.current_state = ConversationState.COLLECTING_INFO

        # Execute
        next_state = manager.determine_next_state(
            mock_conversation,
            intent="booking",
            extracted_entities={
                "requested_date": "2026-02-28",
                "address": "123 Main St",
                "service_type": "sink_repair"
            }
        )

        # Verify
        assert next_state == ConversationState.AWAITING_CONFIRMATION

    def test_determine_next_state_missing_date(self, manager, mock_conversation):
        """Test determining next state when date is missing."""
        mock_conversation.current_state = ConversationState.COLLECTING_INFO

        # Execute
        next_state = manager.determine_next_state(
            mock_conversation,
            intent="booking",
            extracted_entities={
                "address": "123 Main St",
                "service_type": "sink_repair"
            }
        )

        # Verify
        assert next_state == ConversationState.AWAITING_DATE

    def test_determine_next_state_missing_location(self, manager, mock_conversation):
        """Test determining next state when location is missing."""
        mock_conversation.current_state = ConversationState.COLLECTING_INFO

        # Execute
        next_state = manager.determine_next_state(
            mock_conversation,
            intent="booking",
            extracted_entities={
                "requested_date": "2026-02-28",
                "service_type": "sink_repair"
            }
        )

        # Verify
        assert next_state == ConversationState.AWAITING_LOCATION

    def test_determine_next_state_pricing_intent(self, manager, mock_conversation):
        """Test determining next state for pricing intent."""
        mock_conversation.current_state = ConversationState.INTENT_IDENTIFIED

        # Execute
        next_state = manager.determine_next_state(
            mock_conversation,
            intent="pricing"
        )

        # Verify
        assert next_state == ConversationState.PROVIDING_INFO

    def test_get_missing_fields_all_present(self, manager):
        """Test getting missing fields when all present."""
        entities = {
            "requested_date": "2026-02-28",
            "address": "123 Main St",
            "service_type": "sink_repair"
        }

        missing = manager._get_missing_fields(entities)

        assert missing == []

    def test_get_missing_fields_none_present(self, manager):
        """Test getting missing fields when none present."""
        missing = manager._get_missing_fields({})

        assert "date" in missing
        assert "location" in missing
        assert "service_type" in missing

    def test_get_missing_fields_partial(self, manager):
        """Test getting missing fields when partially present."""
        entities = {
            "requested_date": "2026-02-28"
        }

        missing = manager._get_missing_fields(entities)

        assert "date" not in missing
        assert "location" in missing
        assert "service_type" in missing

