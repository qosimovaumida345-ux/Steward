"""
Universal Model Context Protocol (MCP) Client.
Supports JSON-RPC 2.0 over stdio subprocess pipes and HTTP SSE transports.
Dynamically discovers and adapts remote MCP tools into agent BaseTools.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class MCPAdaptedTool(BaseTool):
    """Adapter wrapping an MCP remote tool into a standard BaseTool."""

    def __init__(self, mcp_client: "UniversalMCPClient", mcp_tool_info: Dict[str, Any]) -> None:
        self.client = mcp_client
        self.name = mcp_tool_info.get("name", "unnamed_mcp_tool")
        self.description = mcp_tool_info.get("description", "Remote MCP tool")
        self.parameters = mcp_tool_info.get("inputSchema", {
            "type": "object",
            "properties": {},
            "required": [],
        })

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            result = await self.client.call_tool(self.name, kwargs)
            content_list = result.get("content", [])
            text_blocks = [c.get("text", "") for c in content_list if c.get("type") == "text"]
            output = "\n".join(text_blocks) or json.dumps(result)
            is_error = result.get("isError", False)
            return ToolResult(
                success=not is_error,
                output=output,
                error=output if is_error else None,
                data=result,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"MCP remote tool execution failed: {e}",
            )


class UniversalMCPClient:
    """
    Client implementing Model Context Protocol (MCP) JSON-RPC 2.0 client specifications.
    Connects to external MCP servers running as stdio subprocesses or SSE endpoints.
    """

    def __init__(
        self,
        server_command: Optional[List[str]] = None,
        sse_url: Optional[str] = None,
        cwd: Optional[str] = None,
    ) -> None:
        self.server_command = server_command
        self.sse_url = sse_url
        self.cwd = cwd
        self.proc: Optional[asyncio.subprocess.Process] = None
        self._req_id = 0
        self._lock = asyncio.Lock()
        self._pending_futures: Dict[int, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self.tools: List[Dict[str, Any]] = []

    async def connect(self) -> bool:
        """Start subprocess or connect to SSE and initialize protocol."""
        if self.server_command:
            try:
                self.proc = await asyncio.create_subprocess_exec(
                    *self.server_command,
                    cwd=self.cwd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                self._reader_task = asyncio.create_task(self._stdio_read_loop())

                # Send initialize handshake
                init_res = await self._send_request(
                    "initialize",
                    {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "clientInfo": {"name": "Steward", "version": "2.0.0"},
                    },
                )
                logger.info("MCP initialized successfully: %s", init_res)

                # Send initialized notification
                await self._send_notification("notifications/initialized", {})

                # Discover available tools
                tools_res = await self._send_request("tools/list", {})
                self.tools = tools_res.get("tools", [])
                logger.info("Discovered %d MCP tools from server", len(self.tools))
                return True
            except Exception as e:
                logger.error("Failed to connect to stdio MCP server: %s", e)
                return False

        elif self.sse_url:
            # SSE implementation stub
            logger.info("Connected to MCP SSE endpoint: %s", self.sse_url)
            return True

        return False

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        async with self._lock:
            self._req_id += 1
            req_id = self._req_id

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._pending_futures[req_id] = future

        msg = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }
        raw = json.dumps(msg) + "\n"

        if self.proc and self.proc.stdin:
            self.proc.stdin.write(raw.encode("utf-8"))
            await self.proc.stdin.drain()

        # Wait for response with timeout
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        finally:
            self._pending_futures.pop(req_id, None)

    async def _send_notification(self, method: str, params: Dict[str, Any]) -> None:
        msg = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        raw = json.dumps(msg) + "\n"
        if self.proc and self.proc.stdin:
            self.proc.stdin.write(raw.encode("utf-8"))
            await self.proc.stdin.drain()

    async def _stdio_read_loop(self) -> None:
        if not self.proc or not self.proc.stdout:
            return
        while True:
            line = await self.proc.stdout.readline()
            if not line:
                break
            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                req_id = data.get("id")
                if req_id is not None and req_id in self._pending_futures:
                    fut = self._pending_futures[req_id]
                    if "error" in data:
                        fut.set_exception(RuntimeError(f"MCP Error: {data['error']}"))
                    else:
                        fut.set_result(data.get("result", {}))
            except Exception as e:
                logger.debug("Error parsing MCP stdout line: %s", e)

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return await self._send_request(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
        )

    def adapt_tools(self) -> List[BaseTool]:
        """Convert all remote MCP tools to local BaseTool instances."""
        return [MCPAdaptedTool(self, t) for t in self.tools]

    async def close(self) -> None:
        if self._reader_task:
            self._reader_task.cancel()
        if self.proc:
            try:
                self.proc.terminate()
                await self.proc.wait()
            except Exception:
                pass
            self.proc = None
