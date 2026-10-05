"""
Unit tests for File Tools and 3-Tier Search-and-Replace.
"""

import os
from pathlib import Path
import pytest
from steward.tools.file_tools import (
    FindByNameTool,
    GrepSearchTool,
    ListDirTool,
    ReplaceContentTool,
    ViewFileTool,
    WriteToFileTool,
    atomic_write,
)


@pytest.mark.asyncio
async def test_atomic_write_and_view(tmp_path: Path):
    target = tmp_path / "sample.py"
    content = "line 1\nline 2\nline 3\nline 4\nline 5\n"

    # Write
    writer = WriteToFileTool()
    res = await writer.execute(path=str(target), content=content)
    assert res.success is True
    assert target.exists()

    # View with slicing
    viewer = ViewFileTool()
    view_res = await viewer.execute(path=str(target), start_line=2, end_line=4)
    assert view_res.success is True
    assert "line 2" in view_res.output
    assert "line 4" in view_res.output
    assert "line 5" not in view_res.output


@pytest.mark.asyncio
async def test_3tier_replace_exact(tmp_path: Path):
    target = tmp_path / "tier1.py"
    target.write_text("def hello():\n    return 42\n", encoding="utf-8")

    replacer = ReplaceContentTool()
    res = await replacer.execute(
        path=str(target),
        target="return 42",
        replacement="return 100",
    )
    assert res.success is True
    assert "Tier 1" in res.output
    assert "return 100" in target.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_3tier_replace_whitespace_normalized(tmp_path: Path):
    target = tmp_path / "tier2.py"
    # Target file with CRLF and trailing spaces
    target.write_bytes(b"def test():\r\n    x = 1   \r\n    return x\r\n")

    replacer = ReplaceContentTool()
    # Search block with LF and trimmed spaces
    search_block = "def test():\n    x = 1\n    return x"
    replace_block = "def test():\n    x = 2\n    return x"

    res = await replacer.execute(
        path=str(target),
        target=search_block,
        replacement=replace_block,
    )
    assert res.success is True
    assert "Tier 2" in res.output or "Tier 1" in res.output
    assert "x = 2" in target.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_3tier_replace_fuzzy_difflib(tmp_path: Path):
    target = tmp_path / "tier3.py"
    initial_text = (
        "class Engine:\n"
        "    def __init__(self):\n"
        "        self.speed = 10\n"
        "        self.status = 'active'\n"
        "    def run(self):\n"
        "        pass\n"
    )
    target.write_text(initial_text, encoding="utf-8")

    replacer = ReplaceContentTool()
    # Target with minor typo / diff in one line
    search_block = (
        "class Engine:\n"
        "    def __init__(self):\n"
        "        self.speed = 10\n"
        "        self.status = 'active_modified'\n"
    )
    replacement = (
        "class Engine:\n"
        "    def __init__(self):\n"
        "        self.speed = 999\n"
        "        self.status = 'turbo'\n"
    )

    res = await replacer.execute(
        path=str(target),
        target=search_block,
        replacement=replacement,
    )
    assert res.success is True
    assert "Tier 3" in res.output
    assert "speed = 999" in target.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_grep_and_find_tools(tmp_path: Path):
    sub = tmp_path / "pkg"
    sub.mkdir()
    f1 = sub / "module_a.py"
    f1.write_text("MAGIC_TOKEN_ABC = 123\n", encoding="utf-8")

    grep = GrepSearchTool()
    res_grep = await grep.execute(query="MAGIC_TOKEN_ABC", path=str(tmp_path))
    assert res_grep.success is True
    assert "MAGIC_TOKEN_ABC" in res_grep.output

    finder = FindByNameTool()
    res_find = await finder.execute(pattern="*module_a*", path=str(tmp_path))
    assert res_find.success is True
    assert "module_a.py" in res_find.output
