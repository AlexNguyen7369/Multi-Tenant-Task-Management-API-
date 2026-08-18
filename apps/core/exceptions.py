from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Wraps DRF's default exception handler. Placeholder for a consistent error
    response envelope once the API's error contract is decided — not doing
    anything beyond the default yet.
    """
    return exception_handler(exc, context)
