from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import settings


def agora() -> datetime:
    """Relógio do servidor, no fuso dos horários comerciais dos parceiros."""
    return datetime.now(ZoneInfo(settings.TIMEZONE))
