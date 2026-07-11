"""Google Cloud Tasks client for async task dispatch.

Usage::

    from shared.utils.cloud_tasks import CloudTasksClient

    client = CloudTasksClient()
    task_name = await client.enqueue(
        url="https://tasks-.../api/v1/tasks/process-webhook",
        payload={"instance_name": "...", "message": "..."},
        headers={"X-Request-ID": "abc123"},
    )
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

logger = logging.getLogger(__name__)


class CloudTasksClient:
    """Enqueue HTTP tasks to a Google Cloud Tasks queue."""

    def __init__(self) -> None:
        self.project = os.getenv("GCP_PROJECT", "sudamerica-prod")
        self.location = os.getenv("GCP_LOCATION", "us-central1")
        self.queue = os.getenv("CLOUD_TASKS_QUEUE", "whatsapp-webhooks")
        self._client = tasks_v2.CloudTasksClient()
        self._parent = self._client.queue_path(
            self.project, self.location, self.queue
        )

    async def enqueue(
        self,
        url: str,
        payload: dict,
        *,
        task_id: str | None = None,
        delay_seconds: int = 0,
        headers: dict[str, str] | None = None,
    ) -> str:
        """Create a Cloud Task that POSTs JSON to *url*.

        Returns the fully-qualified task name.
        """
        task: dict = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": url,
                "headers": {
                    "Content-Type": "application/json",
                    **(headers or {}),
                },
                "body": json.dumps(payload).encode(),
                "oidc_token": {
                    "service_account_email": os.getenv(
                        "CLOUD_TASKS_SA",
                        "456595931835-compute@developer.gserviceaccount.com",
                    ),
                },
            }
        }

        if task_id:
            task["name"] = f"{self._parent}/tasks/{task_id}"

        if delay_seconds > 0:
            dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
                seconds=delay_seconds
            )
            ts = timestamp_pb2.Timestamp()
            ts.FromDatetime(dt)
            task["schedule_time"] = ts

        response = await asyncio.to_thread(
            self._client.create_task,
            parent=self._parent,
            task=task,
        )
        logger.info("Cloud Task enqueued: %s", response.name)
        return response.name
