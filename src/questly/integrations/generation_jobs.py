"""The in-process GenerationJobStore (ADR-0010).

Jobs live in this process only: a restart loses them and a second worker
cannot see them. The PoC runs one process; a database store replaces this
class without touching GenerationService.
"""

import itertools
import threading
import time
from collections.abc import Callable
from dataclasses import replace

from questly.core.generation.models import GenerationJob, JobStatus, StartedJob


class InMemoryGenerationJobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[int, GenerationJob] = {}
        # Start at the clock so an id from before a restart is never reused
        # for a different job.
        self._ids = itertools.count(int(time.time() * 1000))

    def create_unless_running(self, job: GenerationJob) -> StartedJob:
        with self._lock:
            running = self._running_for(job.actor.user_id, job.classroom_id)
            if running is not None:
                return StartedJob(running, created=False)
            created = replace(job, id=next(self._ids))
            self._jobs[created.id] = created
            return StartedJob(created, created=True)

    def get(self, job_id: int) -> GenerationJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(
        self, job_id: int, change: Callable[[GenerationJob], GenerationJob]
    ) -> GenerationJob:
        with self._lock:
            changed = change(self._jobs[job_id])
            self._jobs[job_id] = changed
            return changed

    def running_for(self, user_id: int, classroom_id: int) -> GenerationJob | None:
        with self._lock:
            return self._running_for(user_id, classroom_id)

    def _running_for(self, user_id: int, classroom_id: int) -> GenerationJob | None:
        for job in self._jobs.values():
            if (
                job.status is JobStatus.RUNNING
                and job.actor.user_id == user_id
                and job.classroom_id == classroom_id
            ):
                return job
        return None
