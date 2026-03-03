"""
Tests for priority detection service.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch

from app.services.ai.priority_detector import PriorityDetector, PriorityResult


class TestPriorityDetector:
    """Test priority detection service."""

    @pytest.fixture
    def detector(self):
        """Create priority detector."""
        return PriorityDetector()

    def test_detector_initialization(self, detector):
        """Test detector initializes correctly."""
        assert detector is not None
        assert len(detector.EMERGENCY_KEYWORDS) > 0
        assert len(detector.HIGH_URGENCY_KEYWORDS) > 0

    def test_detect_emergency_flooding(self, detector):
        """Test detecting flooding emergency."""
        text = "Help! My basement is flooding with water everywhere!"

        result = detector.detect(text)

        assert result.is_emergency is True
        assert result.urgency_level == "emergency"
        assert result.confidence >= 0.7
        assert "flooding" in result.detected_keywords
        assert len(result.reason) > 0

    def test_detect_emergency_burst_pipe(self, detector):
        """Test detecting burst pipe emergency."""
        text = "I have a burst pipe in my kitchen, water is pouring out!"

        result = detector.detect(text)

        assert result.is_emergency is True
        assert result.urgency_level == "emergency"
        assert "burst pipe" in result.detected_keywords or "burst" in result.detected_keywords

    def test_detect_emergency_gas_leak(self, detector):
        """Test detecting gas leak emergency."""
        text = "I smell gas in my house, I think there's a gas leak"

        result = detector.detect(text)

        assert result.is_emergency is True
        assert result.urgency_level == "emergency"
        assert any(k in result.detected_keywords for k in ["gas leak", "smell gas"])

    def test_detect_emergency_with_intent(self, detector):
        """Test emergency detection with intent classification."""
        text = "I need help right away"

        result = detector.detect(text, intent="emergency")

        assert result.is_emergency is True
        assert result.urgency_level == "emergency"

    def test_detect_high_urgency_leak(self, detector):
        """Test detecting high urgency leak."""
        text = "I have a leaking pipe under my sink"

        result = detector.detect(text)

        assert result.is_emergency is False
        assert result.urgency_level in ["high", "urgent"]
        assert "leak" in result.detected_keywords or "leaking" in result.detected_keywords

    def test_detect_high_urgency_clogged(self, detector):
        """Test detecting high urgency clog."""
        text = "My toilet is clogged and overflowing"

        result = detector.detect(text)

        assert result.is_emergency is False
        assert result.urgency_level in ["high", "urgent"]
        assert any(k in result.detected_keywords for k in ["clogged", "overflow", "overflowing"])

    def test_detect_medium_urgency_slow_drain(self, detector):
        """Test detecting medium urgency slow drain."""
        text = "My kitchen sink has a slow drain, can you take a look this week?"

        result = detector.detect(text)

        assert result.is_emergency is False
        assert result.urgency_level == "medium"
        assert "slow drain" in result.detected_keywords or "slow" in result.detected_keywords

    def test_detect_low_urgency_question(self, detector):
        """Test detecting low urgency question."""
        text = "I was wondering how much it would cost to install a new faucet?"

        result = detector.detect(text)

        assert result.is_emergency is False
        assert result.urgency_level == "low"
        assert any(k in result.detected_keywords for k in ["wondering", "cost", "question"])

    def test_detect_low_urgency_estimate(self, detector):
        """Test detecting low urgency estimate request."""
        text = "Can you give me a price quote for water heater installation?"

        result = detector.detect(text)

        assert result.is_emergency is False
        assert result.urgency_level == "low"
        assert any(k in result.detected_keywords for k in ["price", "quote"])

    def test_detect_empty_text_raises_error(self, detector):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            detector.detect("")

    def test_detect_whitespace_only_raises_error(self, detector):
        """Test that whitespace-only text raises ValueError."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            detector.detect("   ")

    def test_detect_no_keywords_defaults_medium(self, detector):
        """Test that text with no keywords defaults to medium."""
        text = "Hello, I would like to talk about plumbing."

        result = detector.detect(text)

        assert result.urgency_level == "medium"
        assert result.confidence <= 0.5
        assert len(result.detected_keywords) == 0

    def test_multiple_emergency_keywords_increase_confidence(self, detector):
        """Test that multiple emergency keywords increase confidence."""
        text = "Emergency! Flooding! Water everywhere! Help immediately!"

        result = detector.detect(text)

        assert result.is_emergency is True
        assert result.confidence > 0.8
        assert len(result.detected_keywords) >= 3

    def test_should_escalate_emergency(self, detector):
        """Test escalation for emergency."""
        result = PriorityResult(
            is_emergency=True,
            urgency_level="emergency",
            confidence=0.9,
            detected_keywords=["flooding"],
            reason="Emergency detected"
        )

        assert detector.should_escalate(result) is True

    def test_should_escalate_urgent_high_confidence(self, detector):
        """Test escalation for urgent with high confidence."""
        result = PriorityResult(
            is_emergency=False,
            urgency_level="urgent",
            confidence=0.8,
            detected_keywords=["leak", "today"],
            reason="Urgent situation"
        )

        assert detector.should_escalate(result) is True

    def test_should_not_escalate_urgent_low_confidence(self, detector):
        """Test no escalation for urgent with low confidence."""
        result = PriorityResult(
            is_emergency=False,
            urgency_level="urgent",
            confidence=0.5,
            detected_keywords=["leak"],
            reason="Possible urgent"
        )

        assert detector.should_escalate(result) is False

    def test_case_insensitive_matching(self, detector):
        """Test that keyword matching is case insensitive."""
        text = "FLOODING IN MY BASEMENT!"

        result = detector.detect(text)

        assert result.is_emergency is True
        assert "flooding" in result.detected_keywords

    def test_word_boundary_matching(self, detector):
        """Test that keywords match on word boundaries."""
        # "leak" should match but not in "leakage" context
        text = "I have a leak in my pipe"

        result = detector.detect(text)

        assert "leak" in result.detected_keywords

    def test_reason_single_keyword(self, detector):
        """Test reason generation for single keyword."""
        text = "My basement is flooding"

        result = detector.detect(text)

        assert "flooding" in result.reason.lower()
        assert "emergency" in result.reason.lower()

    def test_reason_multiple_keywords(self, detector):
        """Test reason generation for multiple keywords."""
        text = "Emergency! Flooding and burst pipe!"

        result = detector.detect(text)

        assert len(result.detected_keywords) >= 2
        assert "keywords" in result.reason.lower()


class TestPriorityDetectionTask:
    """Test priority detection Celery task."""

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
        call.intent = "booking"
        call.transcript = Mock()
        call.transcript.text = "I have a leaking pipe under my sink"
        call.appointments = []
        return call

    @patch("app.workers.tasks.SessionLocal")
    @patch("app.workers.tasks.get_call_by_id")
    @patch("app.workers.tasks.PriorityDetector")
    def test_detect_priority_task_success(
        self,
        mock_detector_class,
        mock_get_call,
        mock_session,
        mock_db,
        mock_call
    ):
        """Test successful priority detection task."""
        from app.workers.tasks import detect_priority_task

        # Setup mocks
        mock_session.return_value = mock_db
        mock_get_call.return_value = mock_call

        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector

        mock_result = PriorityResult(
            is_emergency=False,
            urgency_level="high",
            confidence=0.7,
            detected_keywords=["leak"],
            reason="Detected 'leak' indicating high priority"
        )
        mock_detector.detect.return_value = mock_result
        mock_detector.should_escalate.return_value = False

        # Execute
        result = detect_priority_task("call-123")

        # Verify
        assert result["call_id"] == "call-123"
        assert result["is_emergency"] is False
        assert result["urgency_level"] == "high"
        assert result["confidence"] == 0.7
        mock_detector.detect.assert_called_once()

    @patch("app.workers.tasks.SessionLocal")
    @patch("app.workers.tasks.get_call_by_id")
    def test_detect_priority_task_call_not_found(
        self,
        mock_get_call,
        mock_session,
        mock_db
    ):
        """Test priority detection when call not found."""
        from app.workers.tasks import detect_priority_task

        # Setup mocks
        mock_session.return_value = mock_db
        mock_get_call.return_value = None

        # Execute
        result = detect_priority_task("call-123")

        # Verify
        assert "error" in result
        assert result["call_id"] == "call-123"

    @patch("app.workers.tasks.SessionLocal")
    @patch("app.workers.tasks.get_call_by_id")
    def test_detect_priority_task_no_transcript(
        self,
        mock_get_call,
        mock_session,
        mock_db,
        mock_call
    ):
        """Test priority detection when no transcript available."""
        from app.workers.tasks import detect_priority_task

        # Setup mocks
        mock_session.return_value = mock_db
        mock_call.transcript = None
        mock_get_call.return_value = mock_call

        # Execute
        result = detect_priority_task("call-123")

        # Verify
        assert result["skipped"] is True
        assert "No transcript" in result["reason"]

