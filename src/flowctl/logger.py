import json
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class LogEntry:
    timestamp: str
    level: str
    run_id: str
    event: str
    node: Optional[str] = None
    role: Optional[str] = None
    state: Optional[str] = None
    duration_ms: Optional[int] = None
    from_node: Optional[str] = None
    to_node: Optional[str] = None
    condition: Optional[str] = None
    matched: Optional[bool] = None
    inputs: Optional[dict] = None
    outputs: Optional[dict] = None
    error: Optional[str] = None
    workflow: Optional[str] = None
    executor: Optional[str] = None
    total_duration_ms: Optional[int] = None
    nodes_executed: Optional[int] = None
    status: Optional[str] = None
    command: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    returncode: Optional[int] = None


class WorkflowLogger:
    def __init__(self, run_id: str, run_dir: Path, log_level: str = "INFO", log_format: str = "json"):
        self.run_id = run_id
        self.run_dir = run_dir
        self.log_file = run_dir / "execution.log"
        self.log_level = log_level
        self.log_format = log_format
        self._start_time: Optional[float] = None
        self._node_start_times: dict[str, float] = {}
        self._nodes_executed: int = 0
        
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _timestamp(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    
    def _write(self, entry: LogEntry):
        if entry.event == "executor":
            lines = self._format_executor(entry)
        elif self.log_format == "json":
            data = {k: v for k, v in entry.__dict__.items() if v is not None}
            lines = [json.dumps(data)]
        else:
            lines = [self._format_text(entry)]
        
        with open(self.log_file, "a") as f:
            for line in lines:
                f.write(line + "\n")
    
    def _format_executor(self, entry: LogEntry) -> list[str]:
        lines = [
            f"[{entry.timestamp}] [{entry.level}] [{entry.event}]",
            f"  node: {entry.node}",
            f"  executor: {entry.executor}",
            f"  command: {entry.command}",
            f"  returncode: {entry.returncode}",
            f"  duration: {entry.duration_ms}ms",
        ]
        
        if entry.stdout:
            lines.append("  stdout:")
            for line in entry.stdout.splitlines():
                lines.append(f"    {line}")
        
        if entry.stderr:
            lines.append("  stderr:")
            for line in entry.stderr.splitlines():
                lines.append(f"    {line}")
        
        return lines
    
    def _format_text(self, entry: LogEntry) -> str:
        parts = [f"[{entry.timestamp}] [{entry.level}] [{entry.event}]"]
        if entry.node:
            parts.append(f"node={entry.node}")
        if entry.state:
            parts.append(f"state={entry.state}")
        if entry.duration_ms:
            parts.append(f"duration={entry.duration_ms}ms")
        return " ".join(parts)
    
    def log_workflow_start(self, workflow: str, executor: str, initial_context: dict = None):
        self._start_time = time.time()
        entry = LogEntry(
            timestamp=self._timestamp(),
            level="INFO",
            run_id=self.run_id,
            event="workflow_start",
            workflow=workflow,
            executor=executor,
            inputs=initial_context,
        )
        self._write(entry)
    
    def log_workflow_end(self, status: str):
        total_duration_ms = int((time.time() - self._start_time) * 1000) if self._start_time else 0
        entry = LogEntry(
            timestamp=self._timestamp(),
            level="INFO",
            run_id=self.run_id,
            event="workflow_end",
            status=status,
            total_duration_ms=total_duration_ms,
            nodes_executed=self._nodes_executed,
        )
        self._write(entry)
    
    def log_node_start(self, node_id: str, role: str, prompt: str, skills: list[str] = None, inputs: dict = None):
        self._node_start_times[node_id] = time.time()
        self._nodes_executed += 1
        entry = LogEntry(
            timestamp=self._timestamp(),
            level="INFO",
            run_id=self.run_id,
            event="node_start",
            node=node_id,
            role=role,
            inputs=inputs,
        )
        self._write(entry)
    
    def log_node_end(self, node_id: str, state: str, outputs: dict = None):
        start_time = self._node_start_times.get(node_id, time.time())
        duration_ms = int((time.time() - start_time) * 1000)
        entry = LogEntry(
            timestamp=self._timestamp(),
            level="INFO",
            run_id=self.run_id,
            event="node_end",
            node=node_id,
            state=state,
            outputs=outputs,
            duration_ms=duration_ms,
        )
        self._write(entry)
    
    def log_node_failure(self, node_id: str, error: Exception):
        start_time = self._node_start_times.get(node_id, time.time())
        duration_ms = int((time.time() - start_time) * 1000)
        entry = LogEntry(
            timestamp=self._timestamp(),
            level="ERROR",
            run_id=self.run_id,
            event="node_failure",
            node=node_id,
            state="failed",
            error=str(error),
            duration_ms=duration_ms,
        )
        self._write(entry)
    
    def log_transition(self, from_node: str, to_node: str, condition: Optional[str] = None, matched: bool = True):
        entry = LogEntry(
            timestamp=self._timestamp(),
            level="DEBUG",
            run_id=self.run_id,
            event="transition",
            from_node=from_node,
            to_node=to_node,
            condition=condition,
            matched=matched,
        )
        self._write(entry)
    
    def log_validation(self, node_id: str, errors: list[str]):
        entry = LogEntry(
            timestamp=self._timestamp(),
            level="ERROR" if errors else "INFO",
            run_id=self.run_id,
            event="validation",
            node=node_id,
            error="; ".join(errors) if errors else None,
        )
        self._write(entry)
    
    def log_error(self, error: Exception, context: dict = None):
        entry = LogEntry(
            timestamp=self._timestamp(),
            level="ERROR",
            run_id=self.run_id,
            event="error",
            error=str(error),
            inputs=context,
        )
        self._write(entry)
    
    def log_pause(self, node_id: str, inputs: dict = None):
        entry = LogEntry(
            timestamp=self._timestamp(),
            level="INFO",
            run_id=self.run_id,
            event="pause",
            node=node_id,
            inputs=inputs,
        )
        self._write(entry)
    
    def log_warning(self, message: str, node_id: str = None):
        entry = LogEntry(
            timestamp=self._timestamp(),
            level="WARNING",
            run_id=self.run_id,
            event="warning",
            node=node_id,
            error=message,
        )
        self._write(entry)
    
    def log_executor(
        self,
        node_id: str,
        executor: str,
        command: str,
        returncode: int,
        stdout: str = None,
        stderr: str = None,
        duration_ms: int = None,
    ):
        entry = LogEntry(
            timestamp=self._timestamp(),
            level="DEBUG",
            run_id=self.run_id,
            event="executor",
            node=node_id,
            executor=executor,
            command=command,
            returncode=returncode,
            stdout=stdout[:10000] if stdout else None,
            stderr=stderr[:10000] if stderr else None,
            duration_ms=duration_ms,
        )
        self._write(entry)