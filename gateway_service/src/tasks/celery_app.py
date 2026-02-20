from celery import Celery

from src.config import settings

# Gateway only sends tasks — it never runs them
# broker= and backend= must point to the same Redis as the workers
celery_app = Celery(
    "gateway",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)