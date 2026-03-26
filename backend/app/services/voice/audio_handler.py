"""
Audio file handler for storing and managing voice recordings.
"""
import os
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import mimetypes

from app.config.settings import settings
from app.core.logging import get_logger
from app.core.exceptions import ValidationError

logger = get_logger(__name__)

# Supported audio formats
SUPPORTED_FORMATS = {
    'audio/wav': '.wav',
    'audio/x-wav': '.wav',
    'audio/mpeg': '.mp3',
    'audio/mp3': '.mp3',
    'audio/ogg': '.ogg',
    'audio/webm': '.webm',
    'audio/flac': '.flac',
    'audio/x-m4a': '.m4a',
    'audio/raw': '.raw',
    'application/octet-stream': '.raw',  # Fallback for raw/binary uploads
}

# Maximum file size: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024


@dataclass
class AudioMetadata:
    """Metadata for an audio recording."""
    file_path: str
    file_size: int
    duration_seconds: Optional[float]
    format: str
    sample_rate: Optional[int]
    channels: Optional[int]


class AudioHandler:
    """Handles audio file storage and validation."""
    
    def __init__(self):
        """Initialize audio handler."""
        self.recordings_dir = Path(settings.recordings_dir)
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "audio_handler_initialized",
            recordings_dir=str(self.recordings_dir)
        )
    
    def generate_filename(
        self,
        call_sid: str,
        extension: str = '.wav'
    ) -> str:
        """
        Generate a unique timestamp-based filename for a recording.

        Format: YYYYMMDD_HHMMSS_microseconds.wav
        Example: 20260314_234011_823491.wav
        (microseconds prevent collisions when multiple recordings in same second)

        Args:
            call_sid: Call session ID (unused in filename; kept for API compatibility)
            extension: File extension (e.g., '.wav')

        Returns:
            str: Generated filename
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
        return f"{timestamp}{extension}"
    
    def validate_audio_file(
        self,
        content: bytes,
        content_type: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate audio file content.
        
        Args:
            content: File content bytes
            content_type: MIME type of the file
        
        Returns:
            Tuple of (is_valid, error_message, extension)
        """
        # Check file size
        if len(content) == 0:
            return False, "Audio file is empty", None
        
        if len(content) > MAX_FILE_SIZE:
            return False, f"Audio file exceeds maximum size of {MAX_FILE_SIZE / 1024 / 1024}MB", None
        
        # Check content type
        if content_type and content_type not in SUPPORTED_FORMATS:
            return False, f"Unsupported audio format: {content_type}", None
        
        # Get extension
        extension = SUPPORTED_FORMATS.get(content_type, '.wav')
        
        return True, None, extension
    
    async def save_recording(
        self,
        call_sid: str,
        content: bytes,
        content_type: Optional[str] = None,
        filename: Optional[str] = None
    ) -> AudioMetadata:
        """
        Save audio recording to local storage.
        
        Args:
            call_sid: Call session ID
            content: Audio file content
            content_type: MIME type of the audio
            filename: Optional custom filename
        
        Returns:
            AudioMetadata: Metadata about the saved recording
        
        Raises:
            ValidationError: If audio file is invalid
        """
        # Validate audio file
        is_valid, error_msg, extension = self.validate_audio_file(content, content_type)
        if not is_valid:
            logger.error(
                "audio_validation_failed",
                call_sid=call_sid,
                error=error_msg
            )
            raise ValidationError(error_msg)
        
        # Generate filename if not provided
        if not filename:
            filename = self.generate_filename(call_sid, extension)
        
        # Save file
        file_path = self.recordings_dir / filename
        
        try:
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.info(
                "recording_saved",
                call_sid=call_sid,
                file_path=str(file_path),
                file_size=len(content)
            )
            
            # Create metadata
            metadata = AudioMetadata(
                file_path=str(file_path),
                file_size=len(content),
                duration_seconds=None,  # Will be populated by transcription service
                format=content_type or 'audio/wav',
                sample_rate=None,
                channels=None
            )
            
            return metadata
            
        except Exception as exc:
            logger.error(
                "recording_save_failed",
                call_sid=call_sid,
                error=str(exc),
                exc_info=True
            )
            raise ValidationError(f"Failed to save recording: {str(exc)}")

