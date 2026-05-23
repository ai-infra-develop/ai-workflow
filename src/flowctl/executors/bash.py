import subprocess
import os
from pathlib import Path
from typing import Optional
from .base import ExecutorAdapter, ExecutorInput, ExecutorResult
from flowctl.path_utils import resolve_prefixed_path


class BashExecutor(ExecutorAdapter):
    """
    Executes shell scripts for deterministic operations.

    Scripts are located in .flows/scripts/ and receive inputs as positional
    arguments. The RUN_DIR environment variable points to the run directory
    where outputs should be written.
    """

    def __init__(self, script_path: str, timeout_seconds: int = 60):
        self.script_path = script_path
        self.timeout_seconds = timeout_seconds

    def execute(self, inp: ExecutorInput) -> ExecutorResult:
        """
        Execute the bash script with inputs as positional arguments.

        Args:
            inp: ExecutorInput containing inputs, outputs, and run_dir

        Returns:
            ExecutorResult with outputs, returncode, stdout, stderr

        Raises:
            RuntimeError: If script fails validation or execution
        """
        script_file = self._resolve_script_path(inp.workflow_dir)
        self._validate_script(script_file)
        args = self._read_inputs(inp)
        cmd = self._build_command(script_file, args)
        result = self._execute_script(cmd, inp.run_dir)

        if result.returncode != 0:
            raise RuntimeError(
                f"Script execution failed with exit code {result.returncode}\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

        self._validate_outputs(inp.outputs, inp)
        outputs = self._read_outputs(inp.outputs, inp)

        return ExecutorResult(
            outputs=outputs,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def _resolve_script_path(self, workflow_dir: Optional[Path]) -> Path:
        """Resolve script path relative to .flows/scripts/"""
        if not self.script_path:
            raise RuntimeError("No script path specified")

        script_rel = self.script_path
        if script_rel.startswith("scripts/"):
            script_rel = script_rel[len("scripts/"):]

        if ".." in script_rel:
            raise RuntimeError(f"Script path cannot contain '..': {self.script_path}")

        if script_rel.startswith("/") or (len(script_rel) > 1 and script_rel[1] == ":"):
            raise RuntimeError(f"Script path must be relative: {self.script_path}")

        if workflow_dir:
            return workflow_dir / "scripts" / script_rel
        else:
            return Path("scripts") / script_rel

    def _validate_script(self, script_file: Path) -> None:
        """Validate script exists and is executable."""
        if not script_file.exists():
            raise RuntimeError(f"Script not found: {script_file}")

        if not script_file.is_file():
            raise RuntimeError(f"Script path is not a file: {script_file}")

        if not script_file.stat().st_mode & 0o111:
            raise RuntimeError(f"Script is not executable: {script_file}")

    def _read_inputs(self, inp: ExecutorInput) -> list[str]:
        """Read input file contents as strings for positional arguments."""
        args = []

        for key, path_str in inp.inputs.items():
            input_path = resolve_prefixed_path(path_str, inp.run_dir, inp.workflow_dir, inp.repo_dir)

            if input_path.exists():
                args.append(input_path.read_text().rstrip('\n'))
            else:
                args.append("")

        return args

    def _build_command(self, script_file: Path, args: list[str]) -> list[str]:
        """Build command with properly escaped arguments."""
        cmd = ["/bin/bash", str(script_file.resolve())]
        cmd.extend(args)
        return cmd

    def _execute_script(
        self, cmd: list[str], run_dir: Path
    ) -> subprocess.CompletedProcess:
        """Execute script with RUN_DIR environment variable."""
        env = {
            **os.environ,
            "RUN_DIR": str(run_dir.resolve()),
        }

        try:
            return subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(run_dir.resolve()),
                env=env,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Script execution timed out after {self.timeout_seconds}s: {cmd[1]}"
            )

    def _validate_outputs(self, outputs: dict[str, str], inp: ExecutorInput) -> None:
        """Validate all output files exist."""
        if not outputs:
            return

        missing = []
        for key, path_str in outputs.items():
            output_path = resolve_prefixed_path(path_str, inp.run_dir, inp.workflow_dir, inp.repo_dir)
            if not output_path.exists():
                missing.append(f"{key}: {output_path}")

        if missing:
            raise RuntimeError(
                f"Output validation failed. Missing files:\n" +
                "\n".join(f"  - {m}" for m in missing)
            )

    def _read_outputs(self, outputs: dict[str, str], inp: ExecutorInput) -> dict[str, str]:
        """Read output file contents."""
        result = {}
        for key, path_str in outputs.items():
            output_path = resolve_prefixed_path(path_str, inp.run_dir, inp.workflow_dir, inp.repo_dir)
            if output_path.exists():
                result[key] = output_path.read_text()
        return result