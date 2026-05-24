from pathlib import Path
from .base import ExecutorAdapter, ExecutorInput, ExecutorResult
from flowctl.path_utils import resolve_prefixed_path


class EchoAdapter(ExecutorAdapter):
    def execute(self, inp: ExecutorInput) -> ExecutorResult:
        stdout_lines = [
            f"Role: {inp.role}",
            f"Prompt Path: {inp.prompt_path}",
            "",
            "=" * 60,
            "PROCESSED PROMPT",
            "=" * 60,
            inp.prompt,
            "=" * 60,
            "",
            "=" * 60,
            "RESOLVED PATHS",
            "=" * 60,
        ]
        
        if inp.inputs:
            stdout_lines.append("Inputs:")
            for key, filename in inp.inputs.items():
                resolved = resolve_prefixed_path(filename, inp.run_dir, inp.workflow_dir, inp.repo_dir)
                stdout_lines.append(f"  {key}: {filename} -> {resolved}")
        
        if inp.outputs:
            stdout_lines.append("Outputs:")
            for key, filename in inp.outputs.items():
                resolved = resolve_prefixed_path(filename, inp.run_dir, inp.workflow_dir, inp.repo_dir)
                stdout_lines.append(f"  {key}: {filename} -> {resolved}")
        
        stdout_lines.append("=" * 60)
        
        outputs = {}
        for key, filename in inp.inputs.items():
            resolved = resolve_prefixed_path(filename, inp.run_dir, inp.workflow_dir, inp.repo_dir)
            if resolved.exists():
                outputs[key] = resolved.read_text()
        
        for key, filename in inp.outputs.items():
            resolved = resolve_prefixed_path(filename, inp.run_dir, inp.workflow_dir, inp.repo_dir)
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(f"echo: mock artifact for {key}")
            outputs[key] = str(resolved)
        
        return ExecutorResult(
            outputs=outputs,
            returncode=0,
            stdout="\n".join(stdout_lines),
            stderr="",
            command=f"echo (role={inp.role})",
        )