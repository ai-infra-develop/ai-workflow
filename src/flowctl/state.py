import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


class WorkflowStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowState:
    current_node: str
    context: dict[str, str]
    iterations: int
    timestamp: str
    status: WorkflowStatus = WorkflowStatus.RUNNING
    pending_approval_for: Optional[str] = None
    pending_transition_from: Optional[str] = None
    reject_counts: Optional[dict[str, int]] = None
    skipped_nodes: Optional[list[str]] = None


def save_state(
    run_dir: Path,
    current: str,
    context: dict[str, str],
    iterations: int,
    status: WorkflowStatus = WorkflowStatus.RUNNING,
    pending_approval_for: Optional[str] = None,
    pending_transition_from: Optional[str] = None,
    reject_counts: Optional[dict[str, int]] = None,
    skipped_nodes: Optional[list[str]] = None,
) -> None:
    state_file = run_dir / "state.json"
    state = WorkflowState(
        current_node=current,
        context=context,
        iterations=iterations,
        timestamp=_timestamp(),
        status=status,
        pending_approval_for=pending_approval_for,
        pending_transition_from=pending_transition_from,
        reject_counts=reject_counts,
        skipped_nodes=skipped_nodes,
    )
    state_file.write_text(json.dumps({
        "current_node": state.current_node,
        "context": state.context,
        "iterations": state.iterations,
        "timestamp": state.timestamp,
        "status": state.status.value if isinstance(state.status, WorkflowStatus) else state.status,
        "pending_approval_for": state.pending_approval_for,
        "pending_transition_from": state.pending_transition_from,
        "reject_counts": state.reject_counts,
        "skipped_nodes": state.skipped_nodes,
    }, indent=2))


def load_state(run_dir: Path) -> Optional[WorkflowState]:
    state_file = run_dir / "state.json"
    if not state_file.exists():
        return None
    
    try:
        data = json.loads(state_file.read_text())
        status_val = data.get("status", "running")
        status = WorkflowStatus(status_val) if status_val in [s.value for s in WorkflowStatus] else WorkflowStatus.RUNNING
        return WorkflowState(
            current_node=data["current_node"],
            context=data["context"],
            iterations=data["iterations"],
            timestamp=data["timestamp"],
            status=status,
            pending_approval_for=data.get("pending_approval_for"),
            pending_transition_from=data.get("pending_transition_from"),
            reject_counts=data.get("reject_counts"),
            skipped_nodes=data.get("skipped_nodes"),
        )
    except (json.JSONDecodeError, KeyError):
        return None


def has_state(run_dir: Path) -> bool:
    state_file = run_dir / "state.json"
    return state_file.exists()


def clear_state(run_dir: Path) -> None:
    state_file = run_dir / "state.json"
    if state_file.exists():
        state_file.unlink()


def _timestamp() -> str:
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())