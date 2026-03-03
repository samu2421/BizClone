"""
Tests for entity extraction service.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from app.services.ai.entity_extractor import (
    EntityExtractor,
    ExtractedEntities,
)
from app.core.exceptions import AIServiceError


class TestEntityExtractor:
    """Test entity extraction service."""
    
    @pytest.fixture
    def mock_openai_response(self):
        """Create a mock OpenAI response."""
        def create_response(data: dict):
            mock_response = Mock()
            mock_choice = Mock()
            mock_message = Mock()
            mock_message.content = json.dumps(data)
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            return mock_response
        return create_response
    
    @pytest.fixture
    def extractor(self):
        """Create entity extractor with mock API key."""
        with patch('app.services.ai.entity_extractor.OpenAI'):
            return EntityExtractor(api_key="test-key")
    
    def test_extractor_initialization(self, extractor):
        """Test extractor initializes correctly."""
        assert extractor.api_key == "test-key"
        assert extractor.model == "gpt-4o-mini"
    
    def test_extract_appointment_with_date_time(
        self, extractor, mock_openai_response
    ):
        """Test extraction of appointment with date and time."""
        extractor.client.chat.completions.create = Mock(
            return_value=mock_openai_response({
                "date_time_text": "tomorrow at 2pm",
                "requested_date": "2026-02-28",
                "requested_time": "14:00",
                "location_text": None,
                "address": None,
                "city": None,
                "state": None,
                "zip_code": None,
                "service_type": "sink_repair",
                "service_description": "leaking kitchen sink",
                "urgency": "medium",
                "urgency_reason": None,
                "contact_phone": None,
                "contact_email": None,
                "contact_name": None,
                "notes": None
            })
        )
        
        result = extractor.extract(
            "I need someone to fix my leaking kitchen sink tomorrow at 2pm"
        )
        
        assert result.date_time_text == "tomorrow at 2pm"
        assert result.requested_date == "2026-02-28"
        assert result.requested_time == "14:00"
        assert result.service_type == "sink_repair"
        assert result.urgency == "medium"
    
    def test_extract_emergency_with_location(
        self, extractor, mock_openai_response
    ):
        """Test extraction of emergency with location."""
        extractor.client.chat.completions.create = Mock(
            return_value=mock_openai_response({
                "date_time_text": None,
                "requested_date": None,
                "requested_time": None,
                "location_text": "123 Main St, Springfield, IL 62701",
                "address": "123 Main St",
                "city": "Springfield",
                "state": "IL",
                "zip_code": "62701",
                "service_type": "emergency_leak",
                "service_description": "basement flooding",
                "urgency": "emergency",
                "urgency_reason": "water everywhere",
                "contact_phone": None,
                "contact_email": None,
                "contact_name": None,
                "notes": None
            })
        )
        
        result = extractor.extract(
            "HELP! My basement is flooding! I'm at 123 Main St, Springfield, IL 62701"
        )
        
        assert result.address == "123 Main St"
        assert result.city == "Springfield"
        assert result.state == "IL"
        assert result.zip_code == "62701"
        assert result.service_type == "emergency_leak"
        assert result.urgency == "emergency"
        assert result.urgency_reason == "water everywhere"
    
    def test_extract_with_contact_info(
        self, extractor, mock_openai_response
    ):
        """Test extraction with contact information."""
        extractor.client.chat.completions.create = Mock(
            return_value=mock_openai_response({
                "date_time_text": None,
                "requested_date": None,
                "requested_time": None,
                "location_text": None,
                "address": None,
                "city": None,
                "state": None,
                "zip_code": None,
                "service_type": "drain_cleaning",
                "service_description": "clogged drain",
                "urgency": "low",
                "urgency_reason": None,
                "contact_phone": "+1-555-1234",
                "contact_email": "john@example.com",
                "contact_name": "John Doe",
                "notes": None
            })
        )
        
        result = extractor.extract(
            "Hi, this is John Doe. My drain is clogged. "
            "You can reach me at 555-1234 or john@example.com"
        )
        
        assert result.contact_name == "John Doe"
        assert result.contact_phone == "+1-555-1234"
        assert result.contact_email == "john@example.com"
        assert result.service_type == "drain_cleaning"
        assert result.urgency == "low"
    
    def test_extract_empty_text_raises_error(self, extractor):
        """Test that empty text raises error."""
        with pytest.raises(AIServiceError, match="Cannot extract entities"):
            extractor.extract("")
        
        with pytest.raises(AIServiceError, match="Cannot extract entities"):
            extractor.extract("   ")
    
    def test_extract_json_decode_error(self, extractor):
        """Test handling of JSON decode error."""
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Not valid JSON"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        extractor.client.chat.completions.create = Mock(
            return_value=mock_response
        )
        
        with pytest.raises(AIServiceError, match="Failed to parse"):
            extractor.extract("Some text")

    def test_extract_with_context(self, extractor, mock_openai_response):
        """Test extraction with additional context."""
        extractor.client.chat.completions.create = Mock(
            return_value=mock_openai_response({
                "date_time_text": "tomorrow",
                "requested_date": "2026-02-28",
                "requested_time": None,
                "location_text": None,
                "address": None,
                "city": None,
                "state": None,
                "zip_code": None,
                "service_type": "toilet_fix",
                "service_description": "running toilet",
                "urgency": "medium",
                "urgency_reason": None,
                "contact_phone": None,
                "contact_email": None,
                "contact_name": None,
                "notes": None
            })
        )

        result = extractor.extract(
            "My toilet won't stop running. Can you come tomorrow?",
            context={"current_date": "2026-02-27"}
        )

        assert result.requested_date == "2026-02-28"
        assert result.service_type == "toilet_fix"


class TestEntityExtractionTask:
    """Test entity extraction Celery task."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_call(self):
        """Create mock call object."""
        call = Mock()
        call.id = "call-123"
        call.customer_id = "customer-456"
        return call

    @pytest.fixture
    def mock_appointment(self):
        """Create mock appointment object."""
        appointment = Mock()
        appointment.id = "appointment-789"
        return appointment

    @patch('app.workers.tasks.SessionLocal')
    @patch('app.workers.tasks.get_call_by_id')
    @patch('app.workers.tasks.create_call_event')
    @patch('app.workers.tasks.create_appointment')
    @patch('app.workers.tasks.EntityExtractor')
    def test_extract_entities_task_success(
        self,
        mock_extractor_class,
        mock_create_appointment,
        mock_create_event,
        mock_get_call,
        mock_session_local,
        mock_db,
        mock_call,
        mock_appointment
    ):
        """Test successful entity extraction task."""
        from app.workers.tasks import extract_entities_task

        # Setup mocks
        mock_session_local.return_value = mock_db
        mock_get_call.return_value = mock_call
        mock_create_appointment.return_value = mock_appointment

        # Mock extractor
        mock_extractor = Mock()
        mock_result = Mock()
        mock_result.date_time_text = "tomorrow at 2pm"
        mock_result.requested_date = "2026-02-28"
        mock_result.location_text = None
        mock_result.address = "123 Main St"
        mock_result.city = "Springfield"
        mock_result.state = "IL"
        mock_result.zip_code = "62701"
        mock_result.service_type = "sink_repair"
        mock_result.service_description = "leaking sink"
        mock_result.urgency = "medium"
        mock_result.urgency_reason = None
        mock_result.contact_phone = None
        mock_result.contact_email = None
        mock_result.contact_name = None
        mock_result.notes = None
        mock_extractor.extract.return_value = mock_result
        mock_extractor_class.return_value = mock_extractor

        # Execute task
        result = extract_entities_task(
            "call-123",
            "I need someone to fix my leaking sink tomorrow at 2pm"
        )

        # Verify
        assert result["call_id"] == "call-123"
        assert result["appointment_id"] == "appointment-789"
        assert result["service_type"] == "sink_repair"
        assert result["urgency"] == "medium"
        assert result["has_date"] is True
        assert result["has_location"] is True

        mock_get_call.assert_called_once_with(mock_db, "call-123")
        mock_create_appointment.assert_called_once()
        mock_db.close.assert_called_once()

    @patch('app.workers.tasks.SessionLocal')
    @patch('app.workers.tasks.get_call_by_id')
    def test_extract_entities_task_call_not_found(
        self,
        mock_get_call,
        mock_session_local,
        mock_db
    ):
        """Test entity extraction when call not found."""
        from app.workers.tasks import extract_entities_task

        # Setup mocks
        mock_session_local.return_value = mock_db
        mock_get_call.return_value = None

        # Execute task
        result = extract_entities_task("call-123", "Some text")

        # Verify
        assert "error" in result
        assert result["call_id"] == "call-123"
        mock_db.close.assert_called_once()

