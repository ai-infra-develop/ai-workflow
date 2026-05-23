from typing import Protocol
import re
import logging
from pathlib import Path
from flowctl.models import Node

logger = logging.getLogger(__name__)


class Processor(Protocol):
    """Interface for prompt/content processors."""
    
    def process(self, content: str, context: dict) -> str:
        """Transform content before execution.
        
        Args:
            content: The prompt/content to process
            context: Execution context with 'node', 'run_dir', etc.
            
        Returns:
            Processed content
        """
        ...


class PromptProcessor:
    """Processor that injects I/O sections from node definitions."""
    
    def _parse_prefix(self, filename: str) -> tuple[str, str]:
        """Extract prefix and relative path from filename.
        
        Args:
            filename: Filename with optional prefix (e.g., "run:file.md", "workflow:mem/ba.md")
            
        Returns:
            Tuple of (prefix, relative_path)
            prefix is one of: "run", "workflow", "repo"
        """
        if filename.startswith("workflow:"):
            return "workflow", filename[len("workflow:"):]
        elif filename.startswith("repo:"):
            return "repo", filename[len("repo:"):]
        elif filename.startswith("run:"):
            return "run", filename[len("run:"):]
        else:
            return "run", filename
    
    def _resolve_path(self, prefix: str, rel_path: str, context: dict) -> Path:
        """Resolve relative path to absolute path based on prefix.
        
        Args:
            prefix: One of "run", "workflow", "repo"
            rel_path: Relative path from the prefix directory
            context: Context dict with 'run_dir', 'workflow_dir', 'repo_dir'
            
        Returns:
            Resolved absolute Path, or relative Path if base dir not available
        """
        if prefix == "workflow":
            base_dir = context.get("workflow_dir")
        elif prefix == "repo":
            base_dir = context.get("repo_dir") or context.get("run_dir")
        else:
            base_dir = context.get("run_dir")
        
        if base_dir:
            return base_dir / rel_path
        return Path(rel_path)
    
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
        
        lines = ["## Input", ""]
        for key, filename in inputs.items():
            prefix, rel_path = self._parse_prefix(filename)
            abs_path = self._resolve_path(prefix, rel_path, context)
            lines.append(f"- {key}: Read from {rel_path} ({prefix}_dir: {abs_path})")
        
        return "\n".join(lines)
    
    def _generate_output_section(self, outputs: dict[str, str], context: dict) -> str:
        if not outputs:
            return ""
        
        lines = ["## Output", ""]
        for key, filename in outputs.items():
            prefix, rel_path = self._parse_prefix(filename)
            abs_path = self._resolve_path(prefix, rel_path, context)
            lines.append(f"- {key}: Write to {rel_path} ({prefix}_dir: {abs_path})")
        
        return "\n".join(lines)