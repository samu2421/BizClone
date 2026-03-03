#!/usr/bin/env python3
"""
Verify that all dependencies are installed correctly.
"""
import sys
import importlib

def check_import(module_name, package_name=None):
    """Check if a module can be imported."""
    display_name = package_name or module_name
    try:
        importlib.import_module(module_name)
        print(f"✓ {display_name}")
        return True
    except ImportError as e:
        print(f"✗ {display_name}: {e}")
        return False

def main():
    """Main verification function."""
    print("=" * 60)
    print("BizClone Environment Verification")
    print("=" * 60)
    print()
    
    # Check Python version
    print(f"Python Version: {sys.version}")
    print()
    
    print("Checking Core Dependencies:")
    print("-" * 60)
    
    checks = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("pydantic", "Pydantic"),
        ("pydantic_settings", "Pydantic Settings"),
        ("sqlalchemy", "SQLAlchemy"),
        ("psycopg2", "Psycopg2"),
        ("alembic", "Alembic"),
        ("redis", "Redis"),
        ("celery", "Celery"),
        ("openai", "OpenAI"),
        ("chromadb", "ChromaDB"),
        ("sentence_transformers", "Sentence Transformers"),
        ("tiktoken", "Tiktoken"),
        ("whisper", "OpenAI Whisper"),
        ("elevenlabs", "ElevenLabs"),
        ("pydub", "Pydub"),
        ("soundfile", "SoundFile"),
        ("twilio", "Twilio"),
        ("httpx", "HTTPX"),
        ("aiofiles", "AIOFiles"),
        ("dotenv", "Python Dotenv"),
        ("structlog", "Structlog"),
        ("pytest", "Pytest"),
    ]
    
    results = []
    for module, name in checks:
        results.append(check_import(module, name))
    
    print()
    print("=" * 60)
    success_count = sum(results)
    total_count = len(results)
    print(f"Results: {success_count}/{total_count} dependencies verified")
    
    if success_count == total_count:
        print("✓ All dependencies installed successfully!")
        return 0
    else:
        print("✗ Some dependencies are missing. Please install them.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

