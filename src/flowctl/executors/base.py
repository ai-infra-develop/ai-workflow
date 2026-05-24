import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from flowctl.models import Node


@dataclass
class ExecutorInput:
    role: str
    prompt: str
    run_dir: Path
    prompt_path: Optional[str] = None
    skill_paths: list[str] = field(default_factory=list)
    inputs: dict[str, str] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)
    workflow_dir: Optional[Path] = None
    repo_dir: Optional[Path] = None
    node: Optional[Node] = None


@dataclass
class ExecutorResult:
    outputs: dict[str, str]
    returncode: int
    stdout: str
    stderr: str
    command: Optional[str] = None


class ExecutorAdapter(ABC):
    @abstractmethod
    def execute(self, inp: ExecutorInput) -> ExecutorResult:
        ...