"""
Tests for voice recording integration (n8n webhooks and audio handling).
"""
import pytest
import os
import tempfile
from pathlib import Path
from io import BytesIO
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db import get_db
from app.services.voice import AudioHandler, AudioMetadata


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def test_db():
    """Create test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create test client."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def temp_recordings_dir():
    """Create temporary recordings directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_audio_wav():
    """Create a sample WAV audio file."""
    # Minimal WAV file header (44 bytes) + some data
    wav_header = (
        b'RIFF'
        b'\x24\x00\x00\x00'  # File size - 8
        b'WAVE'
        b'fmt '
        b'\x10\x00\x00\x00'  # Subchunk1Size (16 for PCM)
        b'\x01\x00'  # AudioFormat (1 for PCM)
        b'\x01\x00'  # NumChannels (1 = mono)
        b'\x44\xAC\x00\x00'  # SampleRate (44100)
        b'\x88\x58\x01\x00'  # ByteRate
        b'\x02\x00'  # BlockAlign
        b'\x10\x00'  # BitsPerSample (16)
        b'data'
        b'\x00\x00\x00\x00'  # Subchunk2Size
    )
    # Add some sample data
    sample_data = b'\x00\x00' * 100  # 100 samples of silence
    return wav_header + sample_data


class TestAudioHandler:
    """Test AudioHandler service."""
    
    def test_generate_filename(self):
        """Test filename generation."""
        handler = AudioHandler()
        call_sid = "test_call_123"
        
        filename = handler.generate_filename(call_sid, ".wav")
        
        assert call_sid in filename
        assert filename.endswith(".wav")
    
    def test_validate_audio_file_valid(self, sample_audio_wav):
        """Test audio file validation with valid file."""
        handler = AudioHandler()
        
        is_valid, error, ext = handler.validate_audio_file(
            sample_audio_wav,
            "audio/wav"
        )
        
        assert is_valid is True
        assert error is None
        assert ext == ".wav"
    
    def test_validate_audio_file_empty(self):
        """Test audio file validation with empty file."""
        handler = AudioHandler()
        
        is_valid, error, ext = handler.validate_audio_file(b"", "audio/wav")
        
        assert is_valid is False
        assert "empty" in error.lower()
        assert ext is None
    
    def test_validate_audio_file_too_large(self):
        """Test audio file validation with oversized file."""
        handler = AudioHandler()
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        
        is_valid, error, ext = handler.validate_audio_file(
            large_content,
            "audio/wav"
        )
        
        assert is_valid is False
        assert "exceeds maximum size" in error
        assert ext is None
    
    def test_validate_audio_file_unsupported_format(self):
        """Test audio file validation with unsupported format."""
        handler = AudioHandler()
        
        is_valid, error, ext = handler.validate_audio_file(
            b"test content",
            "video/mp4"
        )
        
        assert is_valid is False
        assert "Unsupported audio format" in error
        assert ext is None
    
    @pytest.mark.asyncio
    async def test_save_recording(self, temp_recordings_dir, sample_audio_wav, monkeypatch):
        """Test saving audio recording."""
        # Patch settings to use temp directory
        from app.config.settings import settings
        monkeypatch.setattr(settings, "recordings_dir", temp_recordings_dir)

        handler = AudioHandler()
        call_sid = "test_call_save"

        metadata = await handler.save_recording(
            call_sid=call_sid,
            content=sample_audio_wav,
            content_type="audio/wav"
        )

        assert isinstance(metadata, AudioMetadata)
        assert os.path.exists(metadata.file_path)
        assert metadata.file_size == len(sample_audio_wav)
        assert metadata.format == "audio/wav"


class TestN8NWebhooks:
    """Test n8n webhook endpoints."""

    def test_upload_voice_recording_success(self, client, sample_audio_wav, monkeypatch):
        """Test successful voice recording upload."""
        # Patch settings to use temp directory
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            from app.config.settings import settings
            monkeypatch.setattr(settings, "recordings_dir", tmpdir)

            # Create file upload
            files = {
                "audio_file": ("test.wav", BytesIO(sample_audio_wav), "audio/wav")
            }
            data = {
                "from_number": "+1234567890",
                "customer_name": "Test Customer"
            }

            response = client.post(
                "/webhooks/n8n/voice/upload",
                files=files,
                data=data
            )

            assert response.status_code == 200
            result = response.json()

            assert result["status"] == "success"
            assert "call_sid" in result
            assert result["call_sid"].startswith("n8n_")
            assert "call_id" in result
            assert "customer_id" in result
            assert "recording_path" in result
            assert result["file_size"] > 0

    def test_upload_voice_recording_invalid_audio(self, client):
        """Test voice recording upload with invalid audio."""
        # Create invalid file upload (empty file)
        files = {
            "audio_file": ("test.wav", BytesIO(b""), "audio/wav")
        }
        data = {
            "from_number": "+1234567890"
        }

        response = client.post(
            "/webhooks/n8n/voice/upload",
            files=files,
            data=data
        )

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_upload_voice_recording_missing_phone(self, client, sample_audio_wav):
        """Test voice recording upload without phone number."""
        files = {
            "audio_file": ("test.wav", BytesIO(sample_audio_wav), "audio/wav")
        }

        response = client.post(
            "/webhooks/n8n/voice/upload",
            files=files
        )

        assert response.status_code == 422  # Validation error

    def test_get_call_info_success(self, client, sample_audio_wav, monkeypatch):
        """Test retrieving call information."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            from app.config.settings import settings
            monkeypatch.setattr(settings, "recordings_dir", tmpdir)

            # First upload a recording
            files = {
                "audio_file": ("test.wav", BytesIO(sample_audio_wav), "audio/wav")
            }
            data = {
                "from_number": "+1234567890",
                "call_sid": "test_call_info_123"
            }

            upload_response = client.post(
                "/webhooks/n8n/voice/upload",
                files=files,
                data=data
            )
            assert upload_response.status_code == 200

            # Now retrieve call info
            call_sid = upload_response.json()["call_sid"]
            response = client.get(f"/webhooks/n8n/call/{call_sid}")

            assert response.status_code == 200
            result = response.json()

            assert result["call_sid"] == call_sid
            assert result["from_number"] == "+1234567890"
            assert result["status"] == "completed"

    def test_get_call_info_not_found(self, client):
        """Test retrieving non-existent call."""
        response = client.get("/webhooks/n8n/call/nonexistent_call_sid")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


