from __future__ import annotations

import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


class CancellationToken:
    def __init__(self) -> None:
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()


@dataclass
class JobError:
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass
class Job:
    id: str
    kind: str
    token: CancellationToken = field(default_factory=CancellationToken)
    status: str = "queued"
    phase: str = "queued"
    progress: int = 0
    result: dict[str, Any] | None = None
    error: JobError | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    condition: threading.Condition = field(default_factory=threading.Condition)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schemaVersion": "job.v1",
            "jobId": self.id,
            "kind": self.kind,
            "status": self.status,
            "phase": self.phase,
            "progress": self.progress,
        }
        if self.result is not None:
            payload["result"] = self.result
        if self.error is not None:
            payload["error"] = self.error.to_dict()
        return payload


ProgressCallable = Callable[[str, int, str], None]
ParseCallable = Callable[[str, CancellationToken], dict[str, Any]]
ExportCallable = Callable[[str, CancellationToken, ProgressCallable], dict[str, Any]]


class JobManager:
    def __init__(self, max_parse_workers: int = 2, max_export_workers: int = 1) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._parse_executor = ThreadPoolExecutor(max_workers=max_parse_workers, thread_name_prefix="parse-job")
        self._export_executor = ThreadPoolExecutor(max_workers=max_export_workers, thread_name_prefix="export-job")

    def submit_parse(self, path: str, work: ParseCallable) -> Job:
        job = Job(id=uuid.uuid4().hex, kind="parse")
        with self._lock:
            self._jobs[job.id] = job
        self._emit(job, "queued", 0, "queued")
        self._parse_executor.submit(self._run_parse, job, path, work)
        return job

    def submit_export(self, work: ExportCallable) -> Job:
        job = Job(id=uuid.uuid4().hex, kind="export")
        with self._lock:
            self._jobs[job.id] = job
        self._emit(job, "queued", 0, "queued")
        self._export_executor.submit(self._run_export, job, work)
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> Job | None:
        job = self.get(job_id)
        if job is None:
            return None
        with job.condition:
            if job.status in TERMINAL_STATUSES:
                return job
            job.token.cancel()
            self._set_state(job, "cancelling", "cancelling", max(job.progress, 1))
        return job

    def iter_sse_events(self, job_id: str) -> Iterable[str]:
        job = self.get(job_id)
        if job is None:
            yield _sse("error", {"code": "JOB_NOT_FOUND", "message": f"Job not found: {job_id}"})
            return

        next_index = 0
        while True:
            with job.condition:
                while next_index >= len(job.events) and job.status not in TERMINAL_STATUSES:
                    job.condition.wait(timeout=0.25)

                events = job.events[next_index:]
                next_index = len(job.events)
                terminal = job.status in TERMINAL_STATUSES

            for event in events:
                yield _sse("progress", event)
            if terminal:
                break

    def shutdown(self) -> None:
        self._parse_executor.shutdown(wait=False, cancel_futures=True)
        self._export_executor.shutdown(wait=False, cancel_futures=True)

    def _run_parse(self, job: Job, path: str, work: ParseCallable) -> None:
        with job.condition:
            if job.token.is_cancelled():
                self._mark_cancelled(job)
                return
            self._set_state(job, "running", "parsing", 5)

        try:
            result = work(path, job.token)
        except Exception as exc:
            with job.condition:
                if job.token.is_cancelled():
                    self._mark_cancelled(job)
                else:
                    self._mark_failed(job, "PARSE_FAILED", str(exc))
            return

        with job.condition:
            if job.token.is_cancelled():
                self._mark_cancelled(job)
                return
            job.result = result
            self._set_state(job, "completed", "completed", 100)

    def _run_export(self, job: Job, work: ExportCallable) -> None:
        with job.condition:
            if job.token.is_cancelled():
                self._mark_cancelled(job)
                return
            self._set_state(job, "running", "preparing", 1, "Preparing export")

        def progress(phase: str, percent: int, message: str) -> None:
            with job.condition:
                if job.status in TERMINAL_STATUSES:
                    return
                self._set_state(job, "running", phase, percent, message)

        try:
            result = work(job.id, job.token, progress)
        except Exception as exc:
            with job.condition:
                if job.token.is_cancelled():
                    self._mark_cancelled(job)
                else:
                    self._mark_failed(job, "EXPORT_FAILED", str(exc))
            return

        with job.condition:
            if job.token.is_cancelled():
                self._mark_cancelled(job)
                return
            job.result = result
            self._set_state(job, "completed", "completed", 100, "Export completed")

    def _set_state(self, job: Job, status: str, phase: str, progress: int, message: str | None = None) -> None:
        job.status = status
        job.phase = phase
        job.progress = max(0, min(100, int(progress)))
        self._emit_locked(job, phase, job.progress, status, message)

    def _mark_cancelled(self, job: Job) -> None:
        job.error = JobError(code="CANCELLED", message="Job cancelled")
        self._set_state(job, "cancelled", "cancelled", job.progress)

    def _mark_failed(self, job: Job, code: str, message: str) -> None:
        job.error = JobError(code=code, message=message)
        self._set_state(job, "failed", "failed", job.progress)

    def _emit(self, job: Job, phase: str, progress: int, status: str) -> None:
        with job.condition:
            self._emit_locked(job, phase, progress, status)

    def _emit_locked(self, job: Job, phase: str, progress: int, status: str, message: str | None = None) -> None:
        event = {"schemaVersion": "job-event.v1", "jobId": job.id, "phase": phase, "progress": progress, "status": status}
        if message:
            event["message"] = message
        job.events.append(event)
        job.condition.notify_all()


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"
