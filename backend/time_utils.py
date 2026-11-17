"""API timestamp presentation.

The existing database has UTC timestamps stored as timezone-naive DateTime columns.
Do not migrate/shift those stored values: serialize them as explicit UTC for browsers.
"""

from datetime import datetime, timezone


def utc_datetime(value: datetime) -> datetime:
    """Interpret legacy naive DB values as UTC; convert aware values to UTC."""
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None
            else value.astimezone(timezone.utc))


def utc_isoformat(value: datetime) -> str:
    """ISO 8601 with Z, so JavaScript never assumes the server's local timezone."""
    return utc_datetime(value).isoformat().replace('+00:00', 'Z')
