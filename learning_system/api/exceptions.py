"""
Centralized Exception Handling for REST API.
Formats error responses consistently with meaningful status codes and error keys.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError, PermissionDenied as DjangoPermissionDenied


def custom_exception_handler(exc, context):
    """
    Standardizes error responses across Django and DRF exceptions.
    """
    response = exception_handler(exc, context)

    if response is not None:
        custom_data = {
            "success": False,
            "status_code": response.status_code,
            "error_type": exc.__class__.__name__,
            "message": "Validation or processing error occurred.",
            "details": response.data
        }
        response.data = custom_data
        return response

    # Handle Django Core Validation Errors
    if isinstance(exc, DjangoValidationError):
        return Response(
            {
                "success": False,
                "status_code": status.HTTP_400_BAD_REQUEST,
                "error_type": "ValidationError",
                "message": exc.message if hasattr(exc, 'message') else str(exc),
                "details": getattr(exc, 'message_dict', [str(exc)])
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Handle Django Core Permission Denied
    if isinstance(exc, DjangoPermissionDenied):
        return Response(
            {
                "success": False,
                "status_code": status.HTTP_403_FORBIDDEN,
                "error_type": "PermissionDenied",
                "message": str(exc) or "You do not have permission to perform this action.",
                "details": []
            },
            status=status.HTTP_403_FORBIDDEN
        )

    # Unhandled server errors (in debug, let standard 500 handler report)
    return None
