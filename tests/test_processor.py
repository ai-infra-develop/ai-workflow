import pytest
from pathlib import Path
from flowctl.processor import PromptProcessor
from flowctl.models import Node


def test_process_with_inputs_and_outputs():
    processor = PromptProcessor()
    node = Node(
        role="developer",
        prompt="test.md",
        inputs={"requirement": "requirement.md", "design": "docs/design.md"},
        outputs={"impl": "impl.md"},
    )
    context = {"node": node}
    prompt = "# Test\n\n## Task\n\nDo something."
    
    result = processor.process(prompt, context)
    
    assert "## Input" in result
    assert "requirement: Read from requirement.md" in result
    assert "design: Read from docs/design.md" in result
    assert "## Output" in result
    assert "impl: Write to impl.md" in result
    assert "# Test" in result
    assert "## Task" in result


def test_process_only_inputs():
    processor = PromptProcessor()
    node = Node(
        role="dev",
        prompt="test.md",
        inputs={"req": "req.md"},
        outputs={},
    )
    context = {"node": node}
    prompt = "# Test"
    
    result = processor.process(prompt, context)
    
    assert "## Input" in result
    assert "## Output" not in result


def test_process_only_outputs():
    processor = PromptProcessor()
    node = Node(
        role="dev",
        prompt="test.md",
        inputs={},
        outputs={"result": "result.md"},
    )
    context = {"node": node}
    prompt = "# Test"
    
    result = processor.process(prompt, context)
    
    assert "## Input" not in result
    assert "## Output" in result


def test_process_empty_inputs_outputs():
    processor = PromptProcessor()
    node = Node(
        role="dev",
        prompt="test.md",
        inputs={},
        outputs={},
    )
    context = {"node": node}
    prompt = "# Test"
    
    result = processor.process(prompt, context)
    
    assert result == "# Test"


def test_skip_bash_executor():
    processor = PromptProcessor()
    node = Node(
        role="dev",
        prompt="test.md",
        executor="bash",
        command="echo test",
        inputs={"req": "req.md"},
        outputs={"result": "result.md"},
    )
    context = {"node": node}
    prompt = "# Test"
    
    result = processor.process(prompt, context)
    
    assert result == "# Test"


def test_remove_existing_input_section():
    processor = PromptProcessor()
    node = Node(
        role="dev",
        prompt="test.md",
        inputs={"req": "req.md"},
        outputs={},
    )
    context = {"node": node}
    prompt = "# Test\n\n## Input\n\nOld input text.\n\n## Task\n\nDo work."
    
    result = processor.process(prompt, context)
    
    assert "Old input text" not in result
    assert "## Input" in result
    assert "req: Read from req.md" in result
    assert "## Task" in result


def test_remove_existing_output_section():
    processor = PromptProcessor()
    node = Node(
        role="dev",
        prompt="test.md",
        inputs={},
        outputs={"result": "result.md"},
    )
    context = {"node": node}
    prompt = "# Test\n\n## Output\n\nOld output.\n\n## Task\n\nDo work."
    
    result = processor.process(prompt, context)
    
    assert "Old output" not in result
    assert "## Output" in result
    assert "result: Write to result.md" in result


def test_case_insensitive_section_removal():
    processor = PromptProcessor()
    node = Node(
        role="dev",
        prompt="test.md",
        inputs={"req": "req.md"},
        outputs={},
    )
    context = {"node": node}
    prompt = "# Test\n\n## input\n\nOld.\n\n## OUTPUT\n\nOld.\n\n## Task"
    
    result = processor.process(prompt, context)
    
    assert "Old." not in result
    assert "## Input" in result


def test_no_existing_sections():
    processor = PromptProcessor()
    node = Node(
        role="dev",
        prompt="test.md",
        inputs={"req": "req.md"},
        outputs={"res": "res.md"},
    )
    context = {"node": node}
    prompt = "# Test\n\n## Task\n\nWork."
    
    result = processor.process(prompt, context)
    
    assert "## Input" in result
    assert "## Output" in result
    assert "## Task" in result


def test_preserve_other_sections():
    processor = PromptProcessor()
    node = Node(
        role="dev",
        prompt="test.md",
        inputs={"req": "req.md"},
        outputs={},
    )
    context = {"node": node}
    prompt = "# Test\n\n## Notes\n\nImportant.\n\n## Task\n\nWork."
    
    result = processor.process(prompt, context)
    
    assert "## Notes" in result
    assert "Important" in result
    assert "## Task" in result


def test_no_node_in_context():
    processor = PromptProcessor()
    context = {}
    prompt = "# Test"
    
    result = processor.process(prompt, context)
    
    assert result == "# Test"


def test_error_handling_returns_original():
    processor = PromptProcessor()
    node = Node(
        role="dev",
        prompt="test.md",
        inputs={"req": "req.md"},
        outputs={},
    )
    context = {"node": node}
    prompt = None  # Will cause error
    
    result = processor.process(prompt, context)
    
    assert result == prompt


def test_parse_prefix_run():
    processor = PromptProcessor()
    prefix, path = processor._parse_prefix("run:clarify.md")
    assert prefix == "run"
    assert path == "clarify.md"


def test_parse_prefix_workflow():
    processor = PromptProcessor()
    prefix, path = processor._parse_prefix("workflow:memory/architect.md")
    assert prefix == "workflow"
    assert path == "memory/architect.md"


def test_parse_prefix_repo():
    processor = PromptProcessor()
    prefix, path = processor._parse_prefix("repo:ARCHITECTURE.md")
    assert prefix == "repo"
    assert path == "ARCHITECTURE.md"


def test_parse_prefix_default():
    processor = PromptProcessor()
    prefix, path = processor._parse_prefix("clarify.md")
    assert prefix == "run"
    assert path == "clarify.md"


def test_resolve_path_workflow():
    processor = PromptProcessor()
    context = {
        "workflow_dir": Path("/home/user/.flows"),
        "run_dir": Path("/home/user/.flows/runs/test"),
    }
    abs_path = processor._resolve_path("workflow", "memory/ba.md", context)
    assert abs_path == Path("/home/user/.flows/memory/ba.md")


def test_resolve_path_repo():
    processor = PromptProcessor()
    context = {
        "repo_dir": Path("/home/user/code/my-project"),
        "run_dir": Path("/home/user/.flows/runs/test"),
    }
    abs_path = processor._resolve_path("repo", "ARCHITECTURE.md", context)
    assert abs_path == Path("/home/user/code/my-project/ARCHITECTURE.md")


def test_resolve_path_run():
    processor = PromptProcessor()
    context = {
        "run_dir": Path("/home/user/.flows/runs/test"),
    }
    abs_path = processor._resolve_path("run", "clarify.md", context)
    assert abs_path == Path("/home/user/.flows/runs/test/clarify.md")


def test_resolve_path_missing_dir():
    processor = PromptProcessor()
    context = {
        "run_dir": Path("/home/user/.flows/runs/test"),
    }
    abs_path = processor._resolve_path("workflow", "memory/ba.md", context)
    assert abs_path == Path("memory/ba.md")


def test_generate_input_with_prefix():
    processor = PromptProcessor()
    node = Node(
        role="dev",
        prompt="test.md",
        inputs={"arch": "workflow:memory/architect.md"},
        outputs={},
    )
    context = {
        "node": node,
        "workflow_dir": Path("/flows"),
        "run_dir": Path("/runs/test"),
    }
    result = processor.process("# Task", context)
    assert "Read from memory/architect.md (workflow_dir: /flows/memory/architect.md)" in result


def test_generate_output_with_prefix():
    processor = PromptProcessor()
    node = Node(
        role="dev",
        prompt="test.md",
        inputs={},
        outputs={"memory_update": "workflow:memory/ba.md"},
    )
    context = {
        "node": node,
        "workflow_dir": Path("/flows"),
        "run_dir": Path("/runs/test"),
    }
    result = processor.process("# Task", context)
    assert "Write to memory/ba.md (workflow_dir: /flows/memory/ba.md)" in result


def test_generate_input_with_repo_prefix():
    processor = PromptProcessor()
    node = Node(
        role="dev",
        prompt="test.md",
        inputs={"architecture": "repo:ARCHITECTURE.md"},
        outputs={},
    )
    context = {
        "node": node,
        "repo_dir": Path("/home/user/code/project"),
        "run_dir": Path("/runs/test"),
    }
    result = processor.process("# Task", context)
    assert "Read from ARCHITECTURE.md (repo_dir: /home/user/code/project/ARCHITECTURE.md)" in result


def test_generate_output_with_repo_prefix():
    processor = PromptProcessor()
    node = Node(
        role="dev",
        prompt="test.md",
        inputs={},
        outputs={"main_file": "repo:src/main.py"},
    )
    context = {
        "node": node,
        "repo_dir": Path("/home/user/code/project"),
        "run_dir": Path("/runs/test"),
    }
    result = processor.process("# Task", context)
    assert "Write to src/main.py (repo_dir: /home/user/code/project/src/main.py)" in result


def test_mixed_prefixes_in_processed_prompt():
    processor = PromptProcessor()
    node = Node(
        role="dev",
        prompt="test.md",
        inputs={
            "clarify": "run:clarify.md",
            "memory": "workflow:memory/architect.md",
            "architecture": "repo:ARCHITECTURE.md",
        },
        outputs={
            "design": "run:design.md",
            "memory_update": "workflow:memory/ba.md",
        },
    )
    context = {
        "node": node,
        "run_dir": Path("/runs/test"),
        "workflow_dir": Path("/flows"),
        "repo_dir": Path("/repo"),
    }
    result = processor.process("# Task", context)
    assert "run_dir: /runs/test/clarify.md" in result
    assert "workflow_dir: /flows/memory/architect.md" in result
    assert "repo_dir: /repo/ARCHITECTURE.md" in result
    assert "run_dir: /runs/test/design.md" in result
    assert "workflow_dir: /flows/memory/ba.md" in result


def test_empty_path_graceful_handling():
    processor = PromptProcessor()
    node = Node(
        role="dev",
        prompt="test.md",
        inputs={"empty": ""},
        outputs={"whitespace": "   "},
    )
    context = {"node": node, "run_dir": Path("/runs/test")}
    result = processor.process("# Task", context)
    assert "## Input" in result
    assert "## Output" in result