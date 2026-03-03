"""
Whisper-based transcription service for converting audio to text.
Uses OpenAI Whisper (CPU version) for speech-to-text conversion.
"""
import time
from pathlib import Path
from typing import Optional, Dict, Any
import whisper
from whisper.utils import get_writer

from app.config.settings import settings
from app.core.logging import get_logger
from app.core.exceptions import TranscriptionError

logger = get_logger(__name__)


class TranscriptionResult:
    """Result of a transcription operation."""
    
    def __init__(
        self,
        text: str,
        language: str,
        confidence: float,
        duration: float,
        processing_time: float,
        segments: list,
        model_name: str
    ):
        self.text = text
        self.language = language
        self.confidence = confidence
        self.duration = duration
        self.processing_time = processing_time
        self.segments = segments
        self.model_name = model_name


class WhisperTranscriptionService:
    """Service for transcribing audio files using Whisper."""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize Whisper transcription service.
        
        Args:
            model_name: Whisper model to use (tiny, base, small, medium, large)
                       Defaults to settings.whisper_model
        """
        self.model_name = model_name or settings.whisper_model
        self.device = settings.whisper_device
        self.language = settings.whisper_language
        self._model = None
        
        logger.info(
            "whisper_service_initialized",
            model_name=self.model_name,
            device=self.device,
            language=self.language
        )
    
    def _load_model(self):
        """Load Whisper model (lazy loading)."""
        if self._model is None:
            logger.info("loading_whisper_model", model=self.model_name)
            start_time = time.time()
            
            try:
                self._model = whisper.load_model(
                    self.model_name,
                    device=self.device
                )
                load_time = time.time() - start_time
                
                logger.info(
                    "whisper_model_loaded",
                    model=self.model_name,
                    load_time_seconds=round(load_time, 2)
                )
            except Exception as exc:
                logger.error(
                    "whisper_model_load_failed",
                    model=self.model_name,
                    error=str(exc),
                    exc_info=True
                )
                raise TranscriptionError(f"Failed to load Whisper model: {str(exc)}")
        
        return self._model
    
    def transcribe_file(
        self,
        audio_file_path: str,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe an audio file to text.
        
        Args:
            audio_file_path: Path to audio file
            language: Language code (e.g., 'en', 'es'). Auto-detect if None.
        
        Returns:
            TranscriptionResult: Transcription result with metadata
        
        Raises:
            TranscriptionError: If transcription fails
        """
        audio_path = Path(audio_file_path)
        
        if not audio_path.exists():
            raise TranscriptionError(f"Audio file not found: {audio_file_path}")
        
        logger.info(
            "transcription_started",
            file_path=str(audio_path),
            file_size=audio_path.stat().st_size,
            language=language or "auto-detect"
        )
        
        start_time = time.time()
        
        try:
            # Load model
            model = self._load_model()
            
            # Transcribe
            result = model.transcribe(
                str(audio_path),
                language=language or self.language if self.language != "auto" else None,
                fp16=False,  # Use FP32 for CPU
                verbose=False
            )
            
            processing_time = time.time() - start_time
            
            # Calculate average confidence from segments
            segments = result.get("segments", [])
            if segments:
                avg_confidence = sum(
                    seg.get("no_speech_prob", 0.0) for seg in segments
                ) / len(segments)
                confidence = 1.0 - avg_confidence  # Invert no_speech_prob
            else:
                confidence = 0.0
            
            transcription_result = TranscriptionResult(
                text=result["text"].strip(),
                language=result.get("language", language or "unknown"),
                confidence=round(confidence, 3),
                duration=result.get("duration", 0.0),
                processing_time=round(processing_time, 2),
                segments=segments,
                model_name=self.model_name
            )
            
            logger.info(
                "transcription_completed",
                file_path=str(audio_path),
                text_length=len(transcription_result.text),
                language=transcription_result.language,
                confidence=transcription_result.confidence,
                duration_seconds=transcription_result.duration,
                processing_time_seconds=transcription_result.processing_time
            )
            
            return transcription_result
            
        except Exception as exc:
            processing_time = time.time() - start_time
            logger.error(
                "transcription_failed",
                file_path=str(audio_path),
                processing_time_seconds=round(processing_time, 2),
                error=str(exc),
                exc_info=True
            )
            raise TranscriptionError(f"Transcription failed: {str(exc)}")

