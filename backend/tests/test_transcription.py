"""
Tests for transcription service and Celery tasks.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from app.services.voice import WhisperTranscriptionService, TranscriptionResult
from app.core.exceptions import TranscriptionError
from app.workers.tasks import transcribe_audio_task


class TestWhisperTranscriptionService:
    """Test Whisper transcription service."""
    
    def test_service_initialization(self):
        """Test service initializes with correct settings."""
        service = WhisperTranscriptionService(model_name="tiny")
        assert service.model_name == "tiny"
        assert service.device == "cpu"
        assert service._model is None  # Lazy loading
    
    def test_service_initialization_default_model(self, monkeypatch):
        """Test service uses default model from settings."""
        monkeypatch.setattr("app.services.voice.transcription.settings.whisper_model", "base")
        service = WhisperTranscriptionService()
        assert service.model_name == "base"
    
    @patch('app.services.voice.transcription.whisper.load_model')
    def test_model_lazy_loading(self, mock_load_model):
        """Test model is loaded lazily on first use."""
        mock_model = Mock()
        mock_load_model.return_value = mock_model
        
        service = WhisperTranscriptionService(model_name="tiny")
        assert service._model is None
        
        # Load model
        model = service._load_model()
        assert model == mock_model
        assert service._model == mock_model
        mock_load_model.assert_called_once_with("tiny", device="cpu")
        
        # Second call should not reload
        model2 = service._load_model()
        assert model2 == mock_model
        assert mock_load_model.call_count == 1  # Still only called once
    
    @patch('app.services.voice.transcription.whisper.load_model')
    def test_model_load_failure(self, mock_load_model):
        """Test handling of model load failure."""
        mock_load_model.side_effect = Exception("Model not found")
        
        service = WhisperTranscriptionService(model_name="invalid")
        
        with pytest.raises(TranscriptionError, match="Failed to load Whisper model"):
            service._load_model()
    
    @patch('app.services.voice.transcription.whisper.load_model')
    def test_transcribe_file_success(self, mock_load_model, tmp_path):
        """Test successful transcription."""
        # Create a temporary audio file
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")
        
        # Mock Whisper model
        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "text": "Hello, this is a test transcription.",
            "language": "en",
            "duration": 5.0,
            "segments": [
                {"no_speech_prob": 0.1},
                {"no_speech_prob": 0.2},
            ]
        }
        mock_load_model.return_value = mock_model
        
        service = WhisperTranscriptionService(model_name="tiny")
        result = service.transcribe_file(str(audio_file))
        
        assert isinstance(result, TranscriptionResult)
        assert result.text == "Hello, this is a test transcription."
        assert result.language == "en"
        assert result.duration == 5.0
        assert result.confidence == 0.85  # 1.0 - ((0.1 + 0.2) / 2)
        assert result.model_name == "tiny"
        assert result.processing_time >= 0  # Can be 0 in mocked tests
        
        mock_model.transcribe.assert_called_once()
    
    def test_transcribe_file_not_found(self):
        """Test transcription with non-existent file."""
        service = WhisperTranscriptionService(model_name="tiny")
        
        with pytest.raises(TranscriptionError, match="Audio file not found"):
            service.transcribe_file("/nonexistent/file.wav")
    
    @patch('app.services.voice.transcription.whisper.load_model')
    def test_transcribe_file_with_language(self, mock_load_model, tmp_path):
        """Test transcription with specified language."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")
        
        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "text": "Hola, esto es una prueba.",
            "language": "es",
            "duration": 3.0,
            "segments": []
        }
        mock_load_model.return_value = mock_model
        
        service = WhisperTranscriptionService(model_name="tiny")
        result = service.transcribe_file(str(audio_file), language="es")
        
        assert result.text == "Hola, esto es una prueba."
        assert result.language == "es"
        
        # Verify language was passed to transcribe
        call_args = mock_model.transcribe.call_args
        assert call_args[1]["language"] == "es"
    
    @patch('app.services.voice.transcription.whisper.load_model')
    def test_transcribe_file_failure(self, mock_load_model, tmp_path):
        """Test handling of transcription failure."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")
        
        mock_model = Mock()
        mock_model.transcribe.side_effect = Exception("Transcription failed")
        mock_load_model.return_value = mock_model
        
        service = WhisperTranscriptionService(model_name="tiny")
        
        with pytest.raises(TranscriptionError, match="Transcription failed"):
            service.transcribe_file(str(audio_file))
    
    @patch('app.services.voice.transcription.whisper.load_model')
    def test_transcribe_file_no_segments(self, mock_load_model, tmp_path):
        """Test transcription with no segments (confidence = 0)."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")
        
        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "text": "Short text",
            "language": "en",
            "duration": 1.0,
            "segments": []  # No segments
        }
        mock_load_model.return_value = mock_model
        
        service = WhisperTranscriptionService(model_name="tiny")
        result = service.transcribe_file(str(audio_file))

        assert result.confidence == 0.0


class TestTranscriptionTask:
    """Test Celery transcription task."""

    @patch('app.workers.tasks.WhisperTranscriptionService')
    @patch('app.workers.tasks.SessionLocal')
    @patch('app.workers.tasks.get_call_by_id')
    @patch('app.workers.tasks.create_transcript')
    @patch('app.workers.tasks.update_call_by_sid')
    @patch('app.workers.tasks.create_call_event')
    def test_transcribe_audio_task_success(
        self,
        mock_create_event,
        mock_update_call,
        mock_create_transcript,
        mock_get_call,
        mock_session_local,
        mock_service_class
    ):
        """Test successful transcription task."""
        # Mock database session
        mock_db = Mock()
        mock_session_local.return_value = mock_db

        # Mock call
        mock_call = Mock()
        mock_call.id = "call-123"
        mock_call.call_sid = "CA123"
        mock_get_call.return_value = mock_call

        # Mock transcription service
        mock_service = Mock()
        mock_result = Mock()
        mock_result.text = "Test transcription"
        mock_result.language = "en"
        mock_result.confidence = 0.95
        mock_result.model_name = "base"
        mock_result.processing_time = 2.5
        mock_result.duration = 5.0
        mock_service.transcribe_file.return_value = mock_result
        mock_service_class.return_value = mock_service

        # Mock transcript
        mock_transcript = Mock()
        mock_transcript.id = "transcript-123"
        mock_create_transcript.return_value = mock_transcript

        # Call the task using apply() to bypass Celery
        result = transcribe_audio_task.apply(
            args=["call-123", "/path/to/audio.wav"]
        ).result

        # Verify result
        assert result["status"] == "success"
        assert result["call_id"] == "call-123"
        assert result["text"] == "Test transcription"
        assert result["language"] == "en"
        assert result["confidence"] == 0.95

        # Verify database calls
        mock_create_transcript.assert_called_once()
        mock_update_call.assert_called_once()
        assert mock_create_event.call_count == 2  # Started and completed

        # Verify session closed
        mock_db.close.assert_called_once()

    @patch('app.workers.tasks.SessionLocal')
    @patch('app.workers.tasks.get_call_by_id')
    def test_transcribe_audio_task_call_not_found(
        self,
        mock_get_call,
        mock_session_local
    ):
        """Test task with non-existent call."""
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        mock_get_call.return_value = None

        # Task will retry and eventually fail
        result = transcribe_audio_task.apply(
            args=["nonexistent", "/path/to/audio.wav"]
        )

        # Check that task failed
        assert result.failed()
        assert "Call not found" in str(result.traceback)

        # Session should be closed (called multiple times due to retries)
        assert mock_db.close.called

