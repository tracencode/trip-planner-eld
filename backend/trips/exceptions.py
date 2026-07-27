"""Custom DRF exception handler for cleaner error payloads."""
from __future__ import annotations

from typing import Any

from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = exception_handler(exc, context)
    if response is None:
        return None

    # Flatten validation errors into a consistent shape
    data = response.data
    if isinstance(data, dict):
        if "detail" in data:
            return response
        # Collect field errors
        messages: list[str] = []
        for field, errors in data.items():
            if isinstance(errors, list):
                for err in errors:
                    messages.append(f"{field}: {err}")
            else:
                messages.append(f"{field}: {errors}")
        response.data = {
            "detail": messages[0] if len(messages) == 1 else "Validation failed.",
            "errors": data,
        }
    return response
