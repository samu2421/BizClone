"""
Test script for uploading voice recordings via n8n webhook.
"""
import requests
import sys
from pathlib import Path

# API endpoint
API_URL = "http://localhost:8000/webhooks/n8n/voice/upload"

def test_upload_recording(audio_file_path: str, from_number: str = "+1234567890"):
    """
    Test uploading a voice recording.
    
    Args:
        audio_file_path: Path to audio file
        from_number: Caller's phone number
    """
    audio_path = Path(audio_file_path)
    
    if not audio_path.exists():
        print(f"❌ Error: Audio file not found: {audio_file_path}")
        return False
    
    print(f"📤 Uploading audio file: {audio_path.name}")
    print(f"📞 From number: {from_number}")
    print(f"🌐 API endpoint: {API_URL}")
    print()
    
    try:
        # Prepare file upload
        with open(audio_path, 'rb') as f:
            files = {
                'audio_file': (audio_path.name, f, 'audio/wav')
            }
            data = {
                'from_number': from_number,
                'customer_name': 'Test Customer'
            }
            
            # Send request
            response = requests.post(API_URL, files=files, data=data)
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            print("✅ Upload successful!")
            print(f"   Call SID: {result['call_sid']}")
            print(f"   Call ID: {result['call_id']}")
            print(f"   Customer ID: {result['customer_id']}")
            print(f"   Recording path: {result['recording_path']}")
            print(f"   File size: {result['file_size']} bytes")
            print(f"   Message: {result['message']}")
            return True
        else:
            print(f"❌ Upload failed with status code: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API server")
        print("   Make sure the server is running: uvicorn app.main:app --reload")
        return False
    except Exception as exc:
        print(f"❌ Error: {exc}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_voice_upload.py <audio_file_path> [from_number]")
        print()
        print("Example:")
        print("  python test_voice_upload.py ../test.wav +1234567890")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    from_number = sys.argv[2] if len(sys.argv) > 2 else "+1234567890"
    
    success = test_upload_recording(audio_file, from_number)
    sys.exit(0 if success else 1)

