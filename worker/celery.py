from celery import Celery
import os

worker = Celery(
    "worker",
    backend=os.getenv("CELERY_BACKEND_URL"),
    broker=os.getenv("CELERY_BROKER_URL"),
    include=["worker.tasks"],
)
# Optional configuration, see the application user guide.

if __name__ == "__main__":
    worker.start()