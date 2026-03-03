"""
Pydantic v2 recursion fix for uvicorn --reload mode.

This module patches Pydantic's FieldInfo.__repr_args__ to prevent
RecursionError when using uvicorn with --reload flag.

MUST BE IMPORTED BEFORE ANY PYDANTIC MODELS!
"""
import sys


def patch_pydantic_fieldinfo():
    """
    Patch Pydantic's FieldInfo.__repr_args__ to skip annotation field.

    This is a workaround for a known issue in Pydantic v2 where
    field annotations can cause infinite recursion during repr.
    """
    try:
        from pydantic.fields import FieldInfo

        # Store original method
        original_repr_args = FieldInfo.__repr_args__

        def safe_repr_args(self):
            """Safe wrapper that skips the annotation field to prevent recursion."""
            for key, value in original_repr_args(self):
                # Skip the 'annotation' field entirely to prevent recursion
                if key == 'annotation':
                    yield key, '<annotation>'
                else:
                    yield key, value

        # Apply the patch
        FieldInfo.__repr_args__ = safe_repr_args

        print("✅ Pydantic FieldInfo patch applied successfully", file=sys.stderr)

    except Exception as e:
        print(f"⚠️  Warning: Could not patch Pydantic FieldInfo: {e}", file=sys.stderr)


# Apply patch immediately when this module is imported
patch_pydantic_fieldinfo()

