"""
Validators for integration test cases.

Each validator checks if a test case passed based on execution artifacts.
"""

import json
from pathlib import Path
from typing import Optional


class TestResultValidator:
    """Validates integration test execution results."""
    
    def __init__(self, run_dir: Path, repo_dir: Optional[Path] = None):
        self.run_dir = run_dir
        self.repo_dir = repo_dir
        self.log_file = run_dir / "execution.log"
    
    def validate(self) -> dict:
        """
        Run all validations and return result summary.
        
        Returns:
            dict with keys: passed, checks, errors
        """
        checks = {
            "log_exists": self._check_log_exists(),
            "workflow_completed": self._check_workflow_completed(),
            "all_nodes_executed": self._check_all_nodes_executed(),
            "executor_logs_valid": self._check_executor_logs(),
            "no_failures": self._check_no_failures(),
        }
        
        if self.repo_dir:
            checks["repo_structure_valid"] = self._check_repo_structure()
        
        passed = all(c["passed"] for c in checks.values())
        errors = [c["error"] for c in checks.values() if c.get("error")]
        
        return {
            "passed": passed,
            "checks": checks,
            "errors": errors,
        }
    
    def _check_log_exists(self) -> dict:
        """Check execution.log file exists."""
        if not self.log_file.exists():
            return {"passed": False, "error": "execution.log not found"}
        return {"passed": True}
    
    def _check_workflow_completed(self) -> dict:
        """Check workflow reached __end__ state."""
        if not self.log_file.exists():
            return {"passed": False, "error": "execution.log not found"}
        
        content = self.log_file.read_text()
        
        for line in content.splitlines():
            if line.strip().startswith("{"):
                try:
                    entry = json.loads(line)
                    if entry.get("event") == "workflow_end":
                        if entry.get("status") == "completed":
                            return {"passed": True, "nodes_executed": entry.get("nodes_executed")}
                        return {"passed": False, "error": f"workflow status: {entry.get('status')}"}
                except json.JSONDecodeError:
                    continue
        
        return {"passed": False, "error": "workflow_end event not found"}
    
    def _check_all_nodes_executed(self) -> dict:
        """Check all expected nodes executed."""
        if not self.log_file.exists():
            return {"passed": False, "error": "execution.log not found"}
        
        content = self.log_file.read_text()
        
        node_starts = set()
        node_ends = set()
        
        for line in content.splitlines():
            if line.strip().startswith("{"):
                try:
                    entry = json.loads(line)
                    if entry.get("event") == "node_start":
                        node_starts.add(entry.get("node"))
                    elif entry.get("event") == "node_end":
                        node_ends.add(entry.get("node"))
                except json.JSONDecodeError:
                    continue
        
        if not node_starts:
            return {"passed": False, "error": "no node_start events found"}
        
        missing_ends = node_starts - node_ends
        if missing_ends:
            return {"passed": False, "error": f"nodes without end: {missing_ends}"}
        
        return {"passed": True, "nodes": list(node_ends)}
    
    def _check_executor_logs(self) -> dict:
        """Check executor log format is valid."""
        if not self.log_file.exists():
            return {"passed": False, "error": "execution.log not found"}
        
        content = self.log_file.read_text()
        
        executor_blocks = content.count("[executor]")
        if executor_blocks == 0:
            return {"passed": False, "error": "no executor logs found"}
        
        required_fields = ["node:", "executor:", "command:", "returncode:", "duration:"]
        for field in required_fields:
            if field not in content:
                return {"passed": False, "error": f"missing field: {field}"}
        
        return {"passed": True, "executor_blocks": executor_blocks}
    
    def _check_no_failures(self) -> dict:
        """Check no node failures occurred."""
        if not self.log_file.exists():
            return {"passed": False, "error": "execution.log not found"}
        
        content = self.log_file.read_text()
        
        for line in content.splitlines():
            if line.strip().startswith("{"):
                try:
                    entry = json.loads(line)
                    if entry.get("event") == "node_failure":
                        return {"passed": False, "error": f"node failed: {entry.get('node')}, error: {entry.get('error')}"}
                except json.JSONDecodeError:
                    continue
        
        return {"passed": True}
    
    def _check_repo_structure(self) -> dict:
        """Check repo directory structure."""
        if not self.repo_dir:
            return {"passed": True}
        
        if not self.repo_dir.exists():
            return {"passed": False, "error": "repo_dir not found"}
        
        src_dir = self.repo_dir / "src"
        if not src_dir.exists():
            return {"passed": False, "error": "repo/src not found"}
        
        py_files = list(src_dir.glob("*.py"))
        return {"passed": True, "files": [f.name for f in py_files]}
    
    def print_summary(self):
        """Print validation summary."""
        result = self.validate()
        
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Overall: {'PASSED' if result['passed'] else 'FAILED'}")
        print()
        
        for check_name, check_result in result["checks"].items():
            status = "✓" if check_result["passed"] else "✗"
            print(f"  {status} {check_name}")
            if check_result.get("error"):
                print(f"      Error: {check_result['error']}")
            if check_result.get("nodes"):
                print(f"      Nodes: {check_result['nodes']}")
            if check_result.get("executor_blocks"):
                print(f"      Blocks: {check_result['executor_blocks']}")
            if check_result.get("files"):
                print(f"      Files: {check_result['files']}")
        
        if result["errors"]:
            print()
            print("Errors:")
            for error in result["errors"]:
                print(f"  - {error}")
        
        print("=" * 60)
        return result


def validate_test_case(run_dir: Path, repo_dir: Optional[Path] = None) -> dict:
    """
    Validate integration test case execution.
    
    Args:
        run_dir: Directory containing execution.log
        repo_dir: Directory containing generated code
    
    Returns:
        dict with keys: passed, checks, errors
    """
    validator = TestResultValidator(run_dir, repo_dir)
    return validator.validate()


def assert_test_passed(run_dir: Path, repo_dir: Optional[Path] = None):
    """
    Assert that test case passed, raising AssertionError with details.
    
    Args:
        run_dir: Directory containing execution.log
        repo_dir: Directory containing generated code
    
    Raises:
        AssertionError: If validation fails
    """
    validator = TestResultValidator(run_dir, repo_dir)
    validator.print_summary()
    
    result = validator.validate()
    if not result["passed"]:
        errors = "; ".join(result["errors"])
        raise AssertionError(f"Test validation failed: {errors}")