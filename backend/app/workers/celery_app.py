"""Celery application foundation."""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "bitonx",
    broker=settings.rabbitmq_url,
    backend=settings.redis_url,
)

