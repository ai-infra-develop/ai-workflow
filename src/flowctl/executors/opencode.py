import subprocess
import json
from pathlib import Path
from .base import ExecutorAdapter, ExecutorInput, ExecutorResult
from flowctl.path_utils import resolve_prefixed_path


class OpencodeAdapter(ExecutorAdapter):
    def __init__(self, model: str = None, agent: str = None):
        self.model = model
        self.agent = agent

    def execute(self, inp: ExecutorInput) -> ExecutorResult:
        prompt_content = self._load_prompt(inp)
        
        cmd = ["opencode", "run"]
        
        # Opencode runs in repo_dir (not run_dir) so it can write repo: prefix outputs
        if inp.repo_dir:
            work_dir = inp.repo_dir.resolve()
        else:
            work_dir = inp.run_dir.resolve()
        
        cmd.extend(["--dir", str(work_dir)])
        cmd.extend(["--format", "json"])

        if self.model:
            cmd.extend(["--model", self.model])
        if self.agent:
            cmd.extend(["--agent", self.agent])

        for skill_path in inp.skill_paths:
            if inp.workflow_dir:
                src_skill = inp.workflow_dir / skill_path
            else:
                src_skill = Path(skill_path)
            skill_file = inp.run_dir / Path(skill_path).name
            if src_skill.exists():
                skill_file.write_text(src_skill.read_text())
                cmd.extend(["--file", str(skill_file)])

        proc = subprocess.run(
            cmd,
            input=prompt_content,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(work_dir),
        )

        outputs = {}
        session_id = None

        if proc.returncode == 0:
            session_id = self._extract_session_id(proc.stdout) or self._extract_session_id(proc.stderr)
            self._extract_and_write_outputs(proc.stdout, inp.outputs, inp.run_dir)
            for key, filename in inp.outputs.items():
                artifact_path = resolve_prefixed_path(filename, inp.run_dir, inp.workflow_dir, inp.repo_dir)
                if artifact_path.exists():
                    outputs[key] = artifact_path.read_text()

        if session_id:
            self._delete_session(session_id)

        return ExecutorResult(
            outputs=outputs,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            command=" ".join(cmd),
        )

    def _extract_session_id(self, stdout: str) -> str | None:
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
                if "sessionID" in event:
                    return event["sessionID"]
            except json.JSONDecodeError:
                continue
        return None

    def _delete_session(self, session_id: str):
        subprocess.run(
            ["opencode", "session", "delete", session_id],
            capture_output=True,
            text=True,
        )

    def _load_prompt(self, inp: ExecutorInput) -> str:
        if inp.prompt:
            return inp.prompt
        
        prompt_lines = [f"Role: {inp.role}"]
        if inp.prompt_path:
            prompt_lines.append(f"Prompt file: {inp.prompt_path}")
        return "\n".join(prompt_lines)

    def _extract_and_write_outputs(self, stdout: str, expected_outputs: dict, run_dir: Path):
        pass