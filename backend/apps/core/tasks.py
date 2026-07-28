from celery import shared_task


@shared_task
def platform_heartbeat() -> dict[str, str]:
    return {"status": "ok"}
