"""
Tests for intent classification service.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from app.services.ai.intent_classifier import (
    IntentClassifier,
    IntentType,
    IntentClassificationResult,
)
from app.core.exceptions import AIServiceError


class TestIntentClassifier:
    """Test intent classification service."""
    
    @pytest.fixture
    def mock_openai_response(self):
        """Create a mock OpenAI response."""
        def create_response(intent: str, confidence: float, reasoning: str):
            mock_response = Mock()
            mock_choice = Mock()
            mock_message = Mock()
            mock_message.content = json.dumps({
                "intent": intent,
                "confidence": confidence,
                "reasoning": reasoning
            })
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            return mock_response
        return create_response
    
    @pytest.fixture
    def classifier(self):
        """Create intent classifier with mock API key."""
        with patch('app.services.ai.intent_classifier.OpenAI'):
            return IntentClassifier(api_key="test-key")
    
    def test_classifier_initialization(self, classifier):
        """Test classifier initializes correctly."""
        assert classifier.api_key == "test-key"
        assert classifier.model == "gpt-4o-mini"
    
    def test_classify_booking_intent(self, classifier, mock_openai_response):
        """Test classification of booking intent."""
        # Mock OpenAI response
        classifier.client.chat.completions.create = Mock(
            return_value=mock_openai_response(
                "booking",
                0.95,
                "Customer wants to schedule a new appointment"
            )
        )
        
        result = classifier.classify("I need to schedule a plumber for tomorrow")
        
        assert result.intent == IntentType.BOOKING
        assert result.confidence == 0.95
        assert "schedule" in result.reasoning.lower()
    
    def test_classify_emergency_intent(self, classifier, mock_openai_response):
        """Test classification of emergency intent."""
        classifier.client.chat.completions.create = Mock(
            return_value=mock_openai_response(
                "emergency",
                0.99,
                "Customer has urgent flooding emergency"
            )
        )
        
        result = classifier.classify("HELP! My basement is flooding!")
        
        assert result.intent == IntentType.EMERGENCY
        assert result.confidence == 0.99
        assert result.confidence > 0.9
    
    def test_classify_pricing_intent(self, classifier, mock_openai_response):
        """Test classification of pricing intent."""
        classifier.client.chat.completions.create = Mock(
            return_value=mock_openai_response(
                "pricing",
                0.92,
                "Customer asking about costs"
            )
        )
        
        result = classifier.classify("How much do you charge for fixing a leak?")
        
        assert result.intent == IntentType.PRICING
        assert result.confidence == 0.92
    
    def test_classify_reschedule_intent(self, classifier, mock_openai_response):
        """Test classification of reschedule intent."""
        classifier.client.chat.completions.create = Mock(
            return_value=mock_openai_response(
                "reschedule",
                0.97,
                "Customer wants to change appointment time"
            )
        )
        
        result = classifier.classify("Can I move my appointment to next week?")
        
        assert result.intent == IntentType.RESCHEDULE
        assert result.confidence == 0.97
    
    def test_classify_cancel_intent(self, classifier, mock_openai_response):
        """Test classification of cancel intent."""
        classifier.client.chat.completions.create = Mock(
            return_value=mock_openai_response(
                "cancel",
                0.96,
                "Customer wants to cancel appointment"
            )
        )
        
        result = classifier.classify("I need to cancel my Friday appointment")
        
        assert result.intent == IntentType.CANCEL
        assert result.confidence == 0.96
    
    def test_classify_availability_intent(self, classifier, mock_openai_response):
        """Test classification of availability intent."""
        classifier.client.chat.completions.create = Mock(
            return_value=mock_openai_response(
                "availability",
                0.90,
                "Customer asking about availability"
            )
        )
        
        result = classifier.classify("Are you available this weekend?")
        
        assert result.intent == IntentType.AVAILABILITY
        assert result.confidence == 0.90
    
    def test_classify_service_question_intent(self, classifier, mock_openai_response):
        """Test classification of service question intent."""
        classifier.client.chat.completions.create = Mock(
            return_value=mock_openai_response(
                "service_question",
                0.93,
                "Customer asking about services offered"
            )
        )
        
        result = classifier.classify("What kind of plumbing services do you offer?")
        
        assert result.intent == IntentType.SERVICE_QUESTION
        assert result.confidence == 0.93
    
    def test_classify_other_intent(self, classifier, mock_openai_response):
        """Test classification of other intent."""
        classifier.client.chat.completions.create = Mock(
            return_value=mock_openai_response(
                "other",
                0.85,
                "General greeting or thanks"
            )
        )
        
        result = classifier.classify("Thanks for the great service!")

        assert result.intent == IntentType.OTHER
        assert result.confidence == 0.85

    def test_classify_empty_text_raises_error(self, classifier):
        """Test that empty text raises error."""
        with pytest.raises(AIServiceError, match="Cannot classify empty text"):
            classifier.classify("")

        with pytest.raises(AIServiceError, match="Cannot classify empty text"):
            classifier.classify("   ")

    def test_classify_invalid_intent_defaults_to_other(
        self, classifier, mock_openai_response
    ):
        """Test that invalid intent defaults to OTHER."""
        classifier.client.chat.completions.create = Mock(
            return_value=mock_openai_response(
                "invalid_intent",
                0.80,
                "Unknown intent"
            )
        )

        result = classifier.classify("Some text")

        assert result.intent == IntentType.OTHER

    def test_classify_confidence_clamped_to_range(
        self, classifier, mock_openai_response
    ):
        """Test that confidence is clamped to 0-1 range."""
        # Test confidence > 1
        classifier.client.chat.completions.create = Mock(
            return_value=mock_openai_response(
                "booking",
                1.5,
                "High confidence"
            )
        )

        result = classifier.classify("Book appointment")
        assert result.confidence == 1.0

        # Test confidence < 0
        classifier.client.chat.completions.create = Mock(
            return_value=mock_openai_response(
                "booking",
                -0.5,
                "Negative confidence"
            )
        )

        result = classifier.classify("Book appointment")
        assert result.confidence == 0.0

    def test_classify_json_decode_error(self, classifier):
        """Test handling of JSON decode error."""
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Not valid JSON"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        classifier.client.chat.completions.create = Mock(
            return_value=mock_response
        )

        with pytest.raises(AIServiceError, match="Failed to parse"):
            classifier.classify("Some text")

    def test_classify_api_error(self, classifier):
        """Test handling of API error."""
        classifier.client.chat.completions.create = Mock(
            side_effect=Exception("API Error")
        )

        with pytest.raises(AIServiceError, match="Intent classification failed"):
            classifier.classify("Some text")

    def test_all_intent_types_defined(self):
        """Test that all required intent types are defined."""
        expected_intents = {
            "booking", "reschedule", "cancel", "pricing",
            "availability", "service_question", "emergency", "other"
        }

        actual_intents = {intent.value for intent in IntentType}

        assert actual_intents == expected_intents

    def test_classification_result_attributes(self):
        """Test IntentClassificationResult attributes."""
        result = IntentClassificationResult(
            intent=IntentType.BOOKING,
            confidence=0.95,
            reasoning="Test reasoning",
            raw_response={"test": "data"}
        )

        assert result.intent == IntentType.BOOKING
        assert result.confidence == 0.95
        assert result.reasoning == "Test reasoning"
        assert result.raw_response == {"test": "data"}


class TestIntentClassificationTask:
    """Test intent classification Celery task."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_call(self):
        """Create mock call object."""
        call = Mock()
        call.id = "test-call-id"
        call.intent = None
        call.intent_confidence = None
        return call

    @patch('app.workers.tasks.SessionLocal')
    @patch('app.workers.tasks.get_call_by_id')
    @patch('app.workers.tasks.IntentClassifier')
    @patch('app.workers.tasks.update_call')
    @patch('app.workers.tasks.create_call_event')
    def test_classify_intent_task_success(
        self,
        mock_create_event,
        mock_update_call,
        mock_classifier_class,
        mock_get_call,
        mock_session_local,
        mock_call
    ):
        """Test successful intent classification task."""
        from app.workers.tasks import classify_intent_task

        # Setup mocks
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_get_call.return_value = mock_call

        # Mock classifier
        mock_classifier = Mock()
        mock_result = Mock()
        mock_result.intent.value = "booking"
        mock_result.confidence = 0.95
        mock_result.reasoning = "Customer wants to book"
        mock_classifier.classify.return_value = mock_result
        mock_classifier_class.return_value = mock_classifier

        # Execute task
        result = classify_intent_task.apply(
            args=["test-call-id", "I need to book a plumber"]
        ).get()

        # Verify
        assert result["call_id"] == "test-call-id"
        assert result["intent"] == "booking"
        assert result["confidence"] == 0.95

        # Verify update_call was called
        mock_update_call.assert_called_once_with(
            mock_db,
            call_id="test-call-id",
            intent="booking",
            intent_confidence=0.95
        )

    @patch('app.workers.tasks.SessionLocal')
    @patch('app.workers.tasks.get_call_by_id')
    def test_classify_intent_task_call_not_found(
        self,
        mock_get_call,
        mock_session_local
    ):
        """Test task when call is not found."""
        from app.workers.tasks import classify_intent_task

        # Setup mocks
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_get_call.return_value = None

        # Execute task
        result = classify_intent_task.apply(
            args=["nonexistent-call-id", "Some text"]
        ).get()

        # Verify error response
        assert "error" in result
        assert result["call_id"] == "nonexistent-call-id"

    @patch('app.workers.tasks.SessionLocal')
    @patch('app.workers.tasks.get_call_by_id')
    @patch('app.workers.tasks.IntentClassifier')
    def test_classify_intent_task_classification_error(
        self,
        mock_classifier_class,
        mock_get_call,
        mock_session_local,
        mock_call
    ):
        """Test task when classification fails."""
        from app.workers.tasks import classify_intent_task

        # Setup mocks
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_get_call.return_value = mock_call

        # Mock classifier to raise error
        mock_classifier = Mock()
        mock_classifier.classify.side_effect = Exception("API Error")
        mock_classifier_class.return_value = mock_classifier

        # Execute task
        result = classify_intent_task.apply(
            args=["test-call-id", "Some text"]
        ).get()

        # Verify error response
        assert "error" in result
        assert result["call_id"] == "test-call-id"

