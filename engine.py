"""A tiny workflow engine.

It runs steps in order, retries failed steps (waiting a bit longer each time),
pauses for human approval, and keeps a history of what happened.
"""
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


class ToolError(Exception):
    """A tool failed (for example, an API timeout)."""


class Status(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"        # waiting for a human decision
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


@dataclass
class Step:
    name: str                                    # key where the result is stored
    label: str                                   # shown in the log
    fn: Optional[Callable[[dict], dict]] = None  # takes the context, returns a result
    success: str = "Done"                        # message logged on success
    pause_for_approval: bool = False             # True = stop here until a human decides


class WorkflowEngine:
    def __init__(self, workflow_id, steps, context=None, max_attempts=3, retry_delay=0.5, verbose=True):
        self.workflow_id = workflow_id
        self.steps = steps
        self.context = dict(context or {})  # results of finished steps live here
        self.max_attempts = max_attempts
        self.retry_delay = retry_delay      # seconds to wait before the 2nd attempt
        self.verbose = verbose
        self.status = Status.PENDING
        self.step_index = 0                 # which step is next
        self.history = []                   # list of (label, message)

    def run(self):
        """Run steps until the workflow pauses, finishes, or fails."""
        if self.status is Status.PENDING:
            self._log("START", f"Workflow {self.workflow_id}")
            self.status = Status.RUNNING
        if self.status is not Status.RUNNING:
            return  # paused (waiting for a human) or already finished

        while self.step_index < len(self.steps):
            step = self.steps[self.step_index]

            if step.pause_for_approval:
                self.status = Status.PAUSED
                self._log("PAUSED", "Waiting for human approval")
                return  # stop here; only approve() can move past this step

            if not self._run_step(step):
                self.status = Status.FAILED
                return
            self.step_index += 1

        self.status = Status.COMPLETED
        self._log("COMPLETE", "Workflow finished")

    def approve(self):
        self._require_paused()
        self._log("APPROVED", "Human approves draft")
        self.status = Status.RUNNING
        self.step_index += 1  # move past the approval step

    def reject(self):
        self._require_paused()
        self.status = Status.REJECTED
        self._log("REJECTED", "Human rejected draft, nothing was sent")

    def _require_paused(self):
        if self.status is not Status.PAUSED:
            raise ValueError("Nothing is waiting for approval")

    def _run_step(self, step):
        """Try a step up to max_attempts times. Returns True if it worked."""
        self._log("RUNNING", step.label)
        for attempt in range(1, self.max_attempts + 1):
            if attempt > 1:
                delay = self.retry_delay * 2 ** (attempt - 2)  # 0.5s, then 1s
                self._log("RETRY", f"Attempt {attempt} (after {delay:g}s backoff)")
                time.sleep(delay)
            try:
                result = step.fn(self.context)
            except ToolError as error:
                self._log("FAILED", str(error))
                continue
            self.context[step.name] = result
            self._log("SUCCESS", step.success)
            return True

        self._log("FAILED", f"{step.label} failed after {self.max_attempts} attempts")
        return False

    def _log(self, label, message):
        self.history.append((label, message))
        if self.verbose:
            print(f"[{label}]".ljust(12) + message)
