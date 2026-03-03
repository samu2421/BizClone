"""
Tests for response generator service.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from app.services.ai.response_generator import ResponseGenerator, ResponseResult
from app.models.conversation_state import ConversationState


class TestResponseGenerator:
    """Test response generator service."""

    @pytest.fixture
    def generator(self):
        """Create a response generator instance."""
        return ResponseGenerator()

    def test_initialization(self, generator):
        """Test response generator initialization."""
        assert generator.model == "gpt-4o-mini"
        assert generator.business_name == "BizClone Plumbing Services"
        assert generator.client is not None

    @patch("app.services.ai.response_generator.OpenAI")
    def test_generate_response_booking_intent(self, mock_openai_class, generator):
        """Test response generation for booking intent."""
        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "response": "I'd be happy to help you schedule an appointment. When would you like us to come out?",
            "suggested_next_state": "awaiting_date",
            "requires_human": False,
            "confidence": 0.9,
            "metadata": {}
        })
        mock_client.chat.completions.create.return_value = mock_response
        generator.client = mock_client

        # Generate response
        result = generator.generate_response(
            conversation_state=ConversationState.INTENT_IDENTIFIED.value,
            intent="booking",
            transcript="I need a plumber to fix my sink",
            extracted_entities={"service_type": "sink repair"},
            is_emergency=False
        )

        # Verify
        assert isinstance(result, ResponseResult)
        assert "appointment" in result.response_text.lower()
        assert result.suggested_next_state == "awaiting_date"
        assert result.requires_human is False
        assert result.confidence > 0.5

    @patch("app.services.ai.response_generator.OpenAI")
    def test_generate_response_emergency(self, mock_openai_class, generator):
        """Test response generation for emergency."""
        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "response": "I understand this is an emergency. We're dispatching a plumber immediately. What's your address?",
            "suggested_next_state": "emergency_handling",
            "requires_human": True,
            "confidence": 1.0,
            "metadata": {"priority": "emergency"}
        })
        mock_client.chat.completions.create.return_value = mock_response
        generator.client = mock_client

        # Generate response
        result = generator.generate_response(
            conversation_state=ConversationState.EMERGENCY_HANDLING.value,
            intent="emergency",
            transcript="My basement is flooding!",
            is_emergency=True
        )

        # Verify
        assert isinstance(result, ResponseResult)
        assert "emergency" in result.response_text.lower() or "immediately" in result.response_text.lower()
        assert result.suggested_next_state == "emergency_handling"
        assert result.confidence >= 0.8

    @patch("app.services.ai.response_generator.OpenAI")
    def test_generate_response_with_entities(self, mock_openai_class, generator):
        """Test response generation with extracted entities."""
        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "response": "Perfect! I have you scheduled for tomorrow at 2 PM at 123 Main St. Can you confirm this is correct?",
            "suggested_next_state": "awaiting_confirmation",
            "requires_human": False,
            "confidence": 0.95,
            "metadata": {}
        })
        mock_client.chat.completions.create.return_value = mock_response
        generator.client = mock_client

        # Generate response
        result = generator.generate_response(
            conversation_state=ConversationState.COLLECTING_INFO.value,
            intent="booking",
            transcript="Tomorrow at 2 PM works for me",
            extracted_entities={
                "date_time_text": "tomorrow at 2 PM",
                "location_text": "123 Main St",
                "service_type": "sink repair"
            }
        )

        # Verify
        assert isinstance(result, ResponseResult)
        assert len(result.response_text) > 0
        assert result.confidence > 0.5

    @patch("app.services.ai.response_generator.OpenAI")
    def test_generate_response_pricing_inquiry(self, mock_openai_class, generator):
        """Test response generation for pricing inquiry."""
        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "response": "I can help you with pricing. What service are you interested in?",
            "suggested_next_state": "providing_info",
            "requires_human": False,
            "confidence": 0.85,
            "metadata": {}
        })
        mock_client.chat.completions.create.return_value = mock_response
        generator.client = mock_client

        # Generate response
        result = generator.generate_response(
            conversation_state=ConversationState.INTENT_IDENTIFIED.value,
            intent="pricing",
            transcript="How much do you charge for water heater installation?"
        )

        # Verify
        assert isinstance(result, ResponseResult)
        assert len(result.response_text) > 0

    @patch("app.services.ai.response_generator.OpenAI")
    def test_generate_response_json_decode_error(self, mock_openai_class, generator):
        """Test fallback when JSON decode fails."""
        # Mock OpenAI response with invalid JSON
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Invalid JSON response"
        mock_client.chat.completions.create.return_value = mock_response
        generator.client = mock_client

        # Generate response
        result = generator.generate_response(
            conversation_state=ConversationState.INTENT_IDENTIFIED.value,
            intent="booking",
            transcript="I need a plumber"
        )

        # Verify fallback response
        assert isinstance(result, ResponseResult)
        assert len(result.response_text) > 0
        assert result.confidence == 0.5

    @patch("app.services.ai.response_generator.OpenAI")
    def test_generate_response_api_error(self, mock_openai_class, generator):
        """Test fallback when API call fails."""
        # Mock OpenAI to raise exception
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        generator.client = mock_client

        # Generate response
        result = generator.generate_response(
            conversation_state=ConversationState.INTENT_IDENTIFIED.value,
            intent="booking",
            transcript="I need a plumber"
        )

        # Verify fallback response
        assert isinstance(result, ResponseResult)
        assert len(result.response_text) > 0

    def test_fallback_response_emergency(self, generator):
        """Test fallback response for emergency."""
        result = generator._fallback_response(
            state=ConversationState.EMERGENCY_HANDLING.value,
            intent="emergency",
            is_emergency=True
        )

        assert isinstance(result, ResponseResult)
        assert "emergency" in result.response_text.lower()
        assert result.requires_human is True
        assert result.confidence == 1.0

    def test_fallback_response_booking(self, generator):
        """Test fallback response for booking."""
        result = generator._fallback_response(
            state=ConversationState.INTENT_IDENTIFIED.value,
            intent="booking",
            is_emergency=False
        )

        assert isinstance(result, ResponseResult)
        assert "appointment" in result.response_text.lower()
        assert result.confidence == 0.5

    def test_get_state_instructions_emergency(self, generator):
        """Test state instructions for emergency."""
        instructions = generator._get_state_instructions(
            state=ConversationState.EMERGENCY_HANDLING.value,
            intent="emergency",
            is_emergency=True
        )

        assert "EMERGENCY" in instructions
        assert "location" in instructions.lower()

    def test_get_state_instructions_awaiting_date(self, generator):
        """Test state instructions for awaiting date."""
        instructions = generator._get_state_instructions(
            state=ConversationState.AWAITING_DATE.value,
            intent="booking",
            is_emergency=False
        )

        assert "appointment" in instructions.lower() or "when" in instructions.lower()

    def test_build_user_prompt(self, generator):
        """Test user prompt building."""
        prompt = generator._build_user_prompt(
            conversation_state=ConversationState.INTENT_IDENTIFIED.value,
            intent="booking",
            transcript="I need a plumber",
            extracted_entities={"service_type": "sink repair"},
            conversation_context={"previous_intent": "greeting"},
            is_emergency=False
        )

        assert "booking" in prompt
        assert "I need a plumber" in prompt
        assert "sink repair" in prompt
        assert "previous_intent" in prompt

    def test_build_system_prompt(self, generator):
        """Test system prompt building."""
        prompt = generator._build_system_prompt()

        assert "BizClone Plumbing Services" in prompt
        assert "professional" in prompt.lower()
        assert "JSON" in prompt or "json" in prompt

