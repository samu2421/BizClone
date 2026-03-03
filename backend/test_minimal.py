#!/usr/bin/env python3
"""
Minimal test to reproduce the Pydantic recursion error.
"""
print("Testing Pydantic BaseSettings...")

try:
    from pydantic_settings import BaseSettings
    print("✓ Imported BaseSettings")

    class TestSettings(BaseSettings):
        app_name: str = "test"

    print("✓ Defined TestSettings class")

    settings = TestSettings()
    print(f"✓ Created settings instance: {settings.app_name}")
    print("\n✅ SUCCESS! No recursion error detected.")

except RecursionError as e:
    print(f"❌ RecursionError: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

