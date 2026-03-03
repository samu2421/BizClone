"""
Recording downloader for fetching audio from external sources (Twilio, etc.).
"""
import httpx
from typing import Optional, Tuple
from pathlib import Path

from app.config.settings import settings
from app.core.logging import get_logger
from app.core.exceptions import TwilioWebhookError

logger = get_logger(__name__)


class RecordingDownloader:
    """Downloads recordings from external sources."""
    
    def __init__(self):
        """Initialize recording downloader."""
        self.timeout = httpx.Timeout(30.0, connect=10.0)
    
    async def download_twilio_recording(
        self,
        recording_url: str,
        call_sid: str
    ) -> Tuple[bytes, str]:
        """
        Download recording from Twilio.
        
        Args:
            recording_url: URL of the Twilio recording
            call_sid: Call session ID
        
        Returns:
            Tuple of (audio_content, content_type)
        
        Raises:
            TwilioWebhookError: If download fails
        """
        try:
            # Add .wav extension to get WAV format
            if not recording_url.endswith('.wav'):
                recording_url = f"{recording_url}.wav"
            
            logger.info(
                "downloading_twilio_recording",
                call_sid=call_sid,
                recording_url=recording_url
            )
            
            # Download with authentication
            auth = (settings.twilio_account_sid, settings.twilio_auth_token)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(recording_url, auth=auth)
                response.raise_for_status()
                
                content = response.content
                content_type = response.headers.get('content-type', 'audio/wav')
                
                logger.info(
                    "twilio_recording_downloaded",
                    call_sid=call_sid,
                    size_bytes=len(content),
                    content_type=content_type
                )
                
                return content, content_type
                
        except httpx.HTTPStatusError as exc:
            logger.error(
                "twilio_download_http_error",
                call_sid=call_sid,
                status_code=exc.response.status_code,
                error=str(exc),
                exc_info=True
            )
            raise TwilioWebhookError(
                f"Failed to download recording: HTTP {exc.response.status_code}"
            )
        except httpx.RequestError as exc:
            logger.error(
                "twilio_download_request_error",
                call_sid=call_sid,
                error=str(exc),
                exc_info=True
            )
            raise TwilioWebhookError(f"Failed to download recording: {str(exc)}")
        except Exception as exc:
            logger.error(
                "twilio_download_unexpected_error",
                call_sid=call_sid,
                error=str(exc),
                exc_info=True
            )
            raise TwilioWebhookError(f"Unexpected error downloading recording: {str(exc)}")
    
    async def download_from_url(
        self,
        url: str,
        call_sid: str,
        auth: Optional[Tuple[str, str]] = None
    ) -> Tuple[bytes, str]:
        """
        Download recording from any URL.
        
        Args:
            url: URL of the recording
            call_sid: Call session ID
            auth: Optional tuple of (username, password) for authentication
        
        Returns:
            Tuple of (audio_content, content_type)
        
        Raises:
            TwilioWebhookError: If download fails
        """
        try:
            logger.info(
                "downloading_recording_from_url",
                call_sid=call_sid,
                url=url
            )
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, auth=auth)
                response.raise_for_status()
                
                content = response.content
                content_type = response.headers.get('content-type', 'audio/wav')
                
                logger.info(
                    "recording_downloaded_from_url",
                    call_sid=call_sid,
                    size_bytes=len(content),
                    content_type=content_type
                )
                
                return content, content_type
                
        except Exception as exc:
            logger.error(
                "url_download_error",
                call_sid=call_sid,
                url=url,
                error=str(exc),
                exc_info=True
            )
            raise TwilioWebhookError(f"Failed to download recording from URL: {str(exc)}")

