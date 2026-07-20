from celery import shared_task

from apps.sources.models import CrawlRun, Source
from apps.sources.services.collector import collect_source


@shared_task(
    bind=True,
    autoretry_for=(OSError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def collect_source_task(
    self,
    source_id: str,
    url: str | None = None,
    trigger: str = CrawlRun.Trigger.SCHEDULED,
) -> dict[str, object]:
    source = Source.objects.get(id=source_id, active=True)
    result = collect_source(source, url=url, trigger=trigger)
    return {
        "source_id": str(source.id),
        "document_id": str(result.document.id),
        "run_id": str(result.run.id),
        "created": result.created,
        "unchanged": result.unchanged,
        "version_number": result.document.version_number,
    }
