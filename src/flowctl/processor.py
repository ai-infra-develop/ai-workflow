from typing import Protocol
import re
import logging
from pathlib import Path
from flowctl.path_utils import parse_path_prefix, resolve_prefixed_path
from flowctl.models import Node

logger = logging.getLogger(__name__)


class Processor(Protocol):
    """Interface for prompt/content processors."""
    
    def process(self, content: str, context: dict) -> str:
        """Transform content before execution."""
        ...


class PromptProcessor:
    """Processor that injects I/O sections from node definitions."""
    
    def process(self, content: str, context: dict) -> str:
        if not isinstance(content, str):
            return content
        
        node = context.get("node")
        if not node:
            return content
        
        if node.executor == "bash":
            return content
        
        try:
            cleaned = self._remove_existing_sections(content)
            input_section = self._generate_input_section(node.inputs, context)
            output_section = self._generate_output_section(node.outputs, context)
            
            sections = []
            if input_section:
                sections.append(input_section)
            if output_section:
                sections.append(output_section)
            
            if sections:
                header = "\n\n".join(sections)
                return f"{header}\n\n{cleaned}"
            
            return cleaned
        except Exception as e:
            logger.warning(f"Processor failed for node: {e}")
            return content
    
    def _remove_existing_sections(self, content: str) -> str:
        try:
            input_pattern = r'(?i)^## input.*?(?=^## |\Z)'
            output_pattern = r'(?i)^## output.*?(?=^## |\Z)'
            
            cleaned = re.sub(input_pattern, '', content, flags=re.MULTILINE | re.DOTALL)
            cleaned = re.sub(output_pattern, '', cleaned, flags=re.MULTILINE | re.DOTALL)
            
            if cleaned != content:
                return cleaned.strip()
            return content
        except Exception as e:
            logger.warning(f"Failed to remove sections: {e}")
            return content
    
    def _generate_input_section(self, inputs: dict[str, str], context: dict) -> str:
        if not inputs:
            return ""
        
        run_dir = context.get("run_dir")
        workflow_dir = context.get("workflow_dir")
        repo_dir = context.get("repo_dir")
        
        lines = ["## Input", ""]
        for key, filename in inputs.items():
            prefix, rel_path = parse_path_prefix(filename)
            if run_dir:
                abs_path = resolve_prefixed_path(filename, run_dir, workflow_dir, repo_dir)
            else:
                abs_path = Path(rel_path)
            prefix_name = prefix.rstrip(":")
            lines.append(f"- {key}: Read from {rel_path} ({prefix_name}_dir: {abs_path})")
        
        return "\n".join(lines)
    
    def _generate_output_section(self, outputs: dict[str, str], context: dict) -> str:
        if not outputs:
            return ""
        
        run_dir = context.get("run_dir")
        workflow_dir = context.get("workflow_dir")
        repo_dir = context.get("repo_dir")
        
        lines = ["## Output", ""]
        for key, filename in outputs.items():
            prefix, rel_path = parse_path_prefix(filename)
            if run_dir:
                abs_path = resolve_prefixed_path(filename, run_dir, workflow_dir, repo_dir)
            else:
                abs_path = Path(rel_path)
            prefix_name = prefix.rstrip(":")
            lines.append(f"- {key}: Write to {rel_path} ({prefix_name}_dir: {abs_path})")
        
        return "\n".join(lines)