"""
Skills Engine: Progressive Disclosure SKILL.md Loader.
Discovers local and global engineering skills with YAML frontmatter.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SkillDefinition(BaseModel):
    name: str
    description: str
    path: str
    content: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class SkillsEngine:
    """Discovers, parses, and provides progressive disclosure of skills."""

    def __init__(self, search_paths: Optional[List[Path]] = None) -> None:
        self.search_paths = search_paths or [
            Path.cwd() / "skills",
            Path.home() / ".STEWARD" / "skills",
        ]
        self._skills: Dict[str, SkillDefinition] = {}

    def discover_skills(self) -> List[SkillDefinition]:
        """Scan search paths for SKILL.md files."""
        self._skills.clear()
        for base_path in self.search_paths:
            if not base_path.exists() or not base_path.is_dir():
                continue
            for skill_file in base_path.rglob("SKILL.md"):
                try:
                    skill = self._parse_skill_file(skill_file)
                    if skill:
                        self._skills[skill.name] = skill
                except Exception as e:
                    logger.warning("Error parsing skill file %s: %s", skill_file, e)
        return list(self._skills.values())

    def _parse_skill_file(self, file_path: Path) -> Optional[SkillDefinition]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()

        name = file_path.parent.name
        desc = ""
        tags = []

        # Parse YAML frontmatter if present (--- ... ---)
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.DOTALL)
        if frontmatter_match:
            fm_text = frontmatter_match.group(1)
            body = frontmatter_match.group(2)
            for line in fm_text.splitlines():
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip()
                elif line.startswith("description:"):
                    desc = line.split(":", 1)[1].strip()
        else:
            body = raw
            # Take first paragraph as description
            first_line = raw.strip().split("\n")[0].lstrip("#").strip()
            desc = first_line or "Skill documentation"

        return SkillDefinition(
            name=name,
            description=desc,
            path=str(file_path),
            content=body,
            tags=tags,
        )

    def get_skill(self, name: str) -> Optional[SkillDefinition]:
        return self._skills.get(name)

    def get_skills_summary(self) -> str:
        """Produce brief summary string for system prompt injection."""
        if not self._skills:
            return ""
        lines = ["Available Skills:"]
        for s in self._skills.values():
            lines.append(f"- {s.name}: {s.description}")
        return "\n".join(lines)
