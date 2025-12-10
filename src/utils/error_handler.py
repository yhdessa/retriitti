import re
from aiogram import html


def sanitize_error_message(error: Exception, max_length: int = 200) -> str:
    error_str = str(error)

    error_clean = re.sub(r'<[^>]+>', '', error_str)

    error_clean = ' '.join(error_clean.split())

    if len(error_clean) > max_length:
        error_clean = error_clean[:max_length - 3] + "..."

    return html.quote(error_clean)


def get_safe_error_text(error: Exception, context: str = "operation") -> str:
    error_clean = sanitize_error_message(error, max_length=150)

    return (
        f"❌ <b>Error during {context}</b>\n\n"
        f"<code>{error_clean}</code>\n\n"
        "Please try again or contact support if the issue persists."
    )


def get_database_error_text(error: Exception) -> str:
    error_str = str(error)
    error_lower = error_str.lower()

    if 'connection' in error_lower or 'timeout' in error_lower:
        return (
            "❌ <b>Database connection error</b>\n\n"
            "Could not connect to the database.\n"
            "Please try again in a moment."
        )

    elif 'unique' in error_lower or 'duplicate' in error_lower:
        return (
            "⚠️ <b>Duplicate entry</b>\n\n"
            "This item already exists in the database."
        )

    elif 'foreign key' in error_lower:
        return (
            "❌ <b>Database constraint error</b>\n\n"
            "Cannot complete operation due to related data."
        )

    else:
        error_clean = sanitize_error_message(error, max_length=100)
        return (
            "❌ <b>Database error</b>\n\n"
            f"<code>{error_clean}</code>\n\n"
            "Please contact support."
        )


def log_and_notify_error(logger, error: Exception, context: str, user_id: int = None) -> str:
    if user_id:
        logger.error(f"Error for user {user_id} during {context}: {error}", exc_info=True)
    else:
        logger.error(f"Error during {context}: {error}", exc_info=True)

    return get_safe_error_text(error, context)
