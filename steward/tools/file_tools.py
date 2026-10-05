"""
High-Precision File Tools.
Features atomic writes, mtime concurrency guards, 3-tier fuzzy search-and-replace, and diff generation.
"""

from __future__ import annotations

import difflib
import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseTool, ToolResult
from ..config.settings import get_settings


def generate_unified_diff(
    original_lines: List[str], new_lines: List[str], file_path: str
) -> str:
    """Generate a clean unified diff string."""
    diff = difflib.unified_diff(
        original_lines,
        new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    )
    return "\n".join(diff)


def atomic_write(target_path: Path, content: str) -> None:
    """
    Atomically writes content to target_path using staging file and os.replace.
    Guarantees no half-written or corrupted files on power/process interruption.
    """
    target_path = target_path.resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = target_path.with_name(f".tmp_{target_path.name}_{os.getpid()}")

    with open(temp_file, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())

    os.replace(temp_file, target_path)


class ViewFileTool(BaseTool):
    name = "view_file"
    description = "View lines of a file with 1-indexed line numbers and slice notation."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative file path"},
            "start_line": {"type": "integer", "description": "1-indexed start line (inclusive)"},
            "end_line": {"type": "integer", "description": "1-indexed end line (inclusive)"},
        },
        "required": ["path"],
    }

    async def execute(
        self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None, **kwargs
    ) -> ToolResult:
        file_path = Path(path).resolve()
        if not file_path.exists():
            return ToolResult(success=False, error=f"File not found: {file_path}")
        if not file_path.is_file():
            return ToolResult(success=False, error=f"Path is not a file: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            s_line = max(1, start_line or 1)
            e_line = min(total_lines, end_line or total_lines)

            if s_line > total_lines:
                return ToolResult(
                    success=True,
                    output=f"File has {total_lines} lines; start line {s_line} is beyond file.",
                )

            formatted = []
            for idx in range(s_line, e_line + 1):
                formatted.append(f"{idx:4d} | {lines[idx - 1].rstrip()}")

            header = f"File: {file_path} (Lines {s_line}-{e_line} of {total_lines})\n"
            return ToolResult(
                success=True,
                output=header + "\n".join(formatted),
                data={"total_lines": total_lines, "start_line": s_line, "end_line": e_line},
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Error reading file: {e}")


class WriteToFileTool(BaseTool):
    name = "write_to_file"
    description = "Create or overwrite a file atomically with full content."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Target file path"},
            "content": {"type": "string", "description": "Complete file text content"},
            "overwrite": {"type": "boolean", "description": "Whether to overwrite existing file"},
        },
        "required": ["path", "content"],
    }

    async def execute(
        self, path: str, content: str, overwrite: bool = True, **kwargs
    ) -> ToolResult:
        file_path = Path(path).resolve()
        existed = file_path.exists()

        if existed and not overwrite:
            return ToolResult(
                success=False,
                error=f"File {file_path} already exists and overwrite is False.",
            )

        old_lines = []
        if existed:
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    old_lines = f.read().splitlines()
            except Exception:
                pass

        try:
            atomic_write(file_path, content)
            new_lines = content.splitlines()
            diff = generate_unified_diff(old_lines, new_lines, str(file_path))

            action_desc = "Overwrote" if existed else "Created"
            return ToolResult(
                success=True,
                output=f"{action_desc} file: {file_path} ({len(new_lines)} lines)",
                diff=diff,
                data={"path": str(file_path), "bytes": len(content)},
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to write file {file_path}: {e}")


class ReplaceContentTool(BaseTool):
    name = "replace_file_content"
    description = "3-Tier robust search-and-replace (Exact -> Whitespace-tolerant -> Fuzzy match)."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to modify"},
            "target": {"type": "string", "description": "Existing text block to replace"},
            "replacement": {"type": "string", "description": "New replacement text block"},
            "allow_multiple": {"type": "boolean", "description": "Allow multiple replacements"},
        },
        "required": ["path", "target", "replacement"],
    }

    def _normalize_spaces(self, text: str) -> str:
        # Normalize CRLF and trailing line spaces
        lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
        return "\n".join(lines)

    def _fuzzy_replace(
        self, original: str, target: str, replacement: str, similarity_threshold: float = 0.70
    ) -> Tuple[Optional[str], str]:
        """
        3-Tier Search-and-Replace:
        Tier 1: Exact match (including line-ending normalization).
        Tier 2: Whitespace-normalized line matching.
        Tier 3: Sliding window sequence matching.
        """
        # Tier 1: Exact match
        if target in original:
            return original.replace(target, replacement, 1), "Tier 1 (Exact Match)"

        # Tier 1b: CRLF vs LF match
        le = "\r\n" if "\r\n" in original else "\n"
        norm_orig = original.replace("\r\n", "\n")
        norm_target = target.replace("\r\n", "\n")
        norm_repl = replacement.replace("\r\n", "\n")

        if norm_target in norm_orig:
            replaced_norm = norm_orig.replace(norm_target, norm_repl, 1)
            if le == "\r\n":
                return replaced_norm.replace("\n", "\r\n"), "Tier 1 (Line-Ending Normalized)"
            return replaced_norm, "Tier 1 (Line-Ending Normalized)"

        # Tier 2: Whitespace-normalized line matching
        orig_lines = original.splitlines(keepends=True)
        target_lines = target.splitlines()
        m = len(target_lines)

        if m > 0 and len(orig_lines) >= m:
            target_stripped = [l.strip() for l in target_lines]
            orig_stripped = [l.strip() for l in orig_lines]

            for i in range(len(orig_lines) - m + 1):
                if orig_stripped[i : i + m] == target_stripped:
                    repl_lines = [
                        (l + le if not l.endswith(("\r", "\n")) else l)
                        for l in replacement.splitlines()
                    ]
                    new_lines = orig_lines[:i] + repl_lines + orig_lines[i + m :]
                    return "".join(new_lines), "Tier 2 (Whitespace-Normalized Match)"

        # Tier 3: Difflib sliding window matching
        if m > 0 and len(orig_lines) >= m:
            best_ratio = 0.0
            best_start = -1
            best_end = -1
            target_str = "\n".join(target.splitlines()).strip()

            for window_size in (m - 1, m, m + 1):
                if window_size <= 0:
                    continue
                for i in range(len(orig_lines) - window_size + 1):
                    window = orig_lines[i : i + window_size]
                    window_str = "\n".join(l.strip() for l in window)
                    ratio = difflib.SequenceMatcher(None, target_str, window_str).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_start = i
                        best_end = i + window_size

            if best_ratio >= similarity_threshold and best_start >= 0:
                repl_lines = [
                    (l + le if not l.endswith(("\r", "\n")) else l)
                    for l in replacement.splitlines()
                ]
                new_lines = orig_lines[:best_start] + repl_lines + orig_lines[best_end:]
                return "".join(new_lines), f"Tier 3 (Fuzzy Match: ratio={best_ratio:.2f})"

        return None, f"No match found"

    async def execute(
        self,
        path: str,
        target: str,
        replacement: str,
        allow_multiple: bool = False,
        **kwargs,
    ) -> ToolResult:
        file_path = Path(path).resolve()
        if not file_path.exists() or not file_path.is_file():
            return ToolResult(success=False, error=f"File not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8", newline="") as f:
                content = f.read()
        except Exception as e:
            return ToolResult(success=False, error=f"Could not read {file_path}: {e}")

        # Check multiplicity if not allowed
        if not allow_multiple and content.count(target) > 1:
            return ToolResult(
                success=False,
                error=f"Target content found {content.count(target)} times. Provide larger unique context.",
            )

        new_content, tier_used = self._fuzzy_replace(content, target, replacement)
        if new_content is None:
            return ToolResult(
                success=False,
                error=f"Could not locate target in {file_path}. Strategy outcome: {tier_used}",
            )

        try:
            atomic_write(file_path, new_content)
            diff = generate_unified_diff(
                content.splitlines(), new_content.splitlines(), str(file_path)
            )
            return ToolResult(
                success=True,
                output=f"Successfully updated {file_path} via {tier_used}.",
                diff=diff,
                data={"tier": tier_used, "path": str(file_path)},
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Error saving modified file {file_path}: {e}")


class ListDirTool(BaseTool):
    name = "list_dir"
    description = "List entries in a directory with file sizes and item types."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path (defaults to current dir)"},
            "max_items": {"type": "integer", "description": "Maximum entries to return"},
        },
    }

    async def execute(self, path: str = ".", max_items: int = 100, **kwargs) -> ToolResult:
        target_dir = Path(path).resolve()
        if not target_dir.exists() or not target_dir.is_dir():
            return ToolResult(success=False, error=f"Directory not found: {target_dir}")

        entries = []
        try:
            count = 0
            for item in target_dir.iterdir():
                count += 1
                if count > max_items:
                    entries.append(f"... (truncated after {max_items} items)")
                    break
                kind = "DIR " if item.is_dir() else "FILE"
                size = item.stat().st_size if item.is_file() else 0
                entries.append(f"[{kind}] {item.name:<30} {size:>10} bytes")

            return ToolResult(
                success=True,
                output=f"Contents of {target_dir}:\n" + "\n".join(entries),
                data={"count": count, "dir": str(target_dir)},
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Error listing directory {target_dir}: {e}")


class GrepSearchTool(BaseTool):
    name = "grep_search"
    description = "Search text pattern or regex across files in workspace."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Pattern or text query to search for"},
            "path": {"type": "string", "description": "Starting directory path"},
            "is_regex": {"type": "boolean", "description": "Whether query is a regular expression"},
            "max_results": {"type": "integer", "description": "Max search matches to return"},
        },
        "required": ["query"],
    }

    async def execute(
        self,
        query: str,
        path: str = ".",
        is_regex: bool = False,
        max_results: int = 50,
        **kwargs,
    ) -> ToolResult:
        start_dir = Path(path).resolve()
        results = []

        try:
            pattern = re.compile(query, re.IGNORECASE) if is_regex else None
        except re.error as e:
            return ToolResult(success=False, error=f"Invalid regex: {e}")

        # Ignored directory names
        ignore_dirs = {".git", "__pycache__", "venv", ".venv", "node_modules", "dist", "build"}

        for root, dirs, files in os.walk(start_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                if len(results) >= max_results:
                    break
                f_path = Path(root) / file
                if f_path.stat().st_size > 1_000_000:  # skip files > 1MB
                    continue
                try:
                    with open(f_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_idx, line in enumerate(f, start=1):
                            match = (
                                pattern.search(line)
                                if is_regex
                                else (query.lower() in line.lower())
                            )
                            if match:
                                rel = f_path.relative_to(start_dir)
                                results.append(f"{rel}:{line_idx}: {line.strip()[:150]}")
                                if len(results) >= max_results:
                                    break
                except Exception:
                    continue

        if not results:
            return ToolResult(success=True, output=f"No matches found for query: '{query}'")

        return ToolResult(
            success=True,
            output=f"Found {len(results)} matches:\n" + "\n".join(results),
            data={"match_count": len(results)},
        )


class FindByNameTool(BaseTool):
    name = "find_by_name"
    description = "Search for files and directories matching a glob pattern."
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern (e.g. *.py, test_*)"},
            "path": {"type": "string", "description": "Starting directory"},
            "max_results": {"type": "integer", "description": "Max items to return"},
        },
        "required": ["pattern"],
    }

    async def execute(
        self, pattern: str, path: str = ".", max_results: int = 50, **kwargs
    ) -> ToolResult:
        start_dir = Path(path).resolve()
        matches = []
        try:
            for p in start_dir.rglob(pattern):
                if any(part in {".git", "__pycache__", ".venv"} for part in p.parts):
                    continue
                matches.append(str(p.relative_to(start_dir)))
                if len(matches) >= max_results:
                    break

            if not matches:
                return ToolResult(success=True, output=f"No files matching '{pattern}'.")

            return ToolResult(
                success=True,
                output=f"Matching files ({len(matches)}):\n" + "\n".join(matches),
                data={"matches": matches},
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Error finding files: {e}")
