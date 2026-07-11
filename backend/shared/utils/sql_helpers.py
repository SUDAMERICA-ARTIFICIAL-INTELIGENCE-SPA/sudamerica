"""SQL utility helpers shared across services."""


def escape_like(value: str) -> str:
    """Escape SQL LIKE special characters."""
    return value.replace("%", "\\%").replace("_", "\\_")
