import json
import shlex
import subprocess

# import sys
from typing import Any, Dict, List, Optional


class MCPClient:
    """Client for Model Context Protocol (MCP)
    servers communicating over stdio"""

    def __init__(self, command: str) -> None:
        self.command = command
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self.tools: List[Dict[str, Any]] = []

    def start(self) -> None:
        """Start the MCP server subprocess."""
        args = shlex.split(self.command)
        self.process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        # Perform MCP initialize handshake
        self._initialize()

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _send_request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a JSON-RPC 2.0 request and read
        the response line from stdout."""
        if (
            not self.process
            or not self.process.stdin
            or not self.process.stdout
        ):
            raise RuntimeError("MCP server process is not running.")

        req_id = self._next_id()
        # prepare JSON msg
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params if params is not None else {},
        }

        # write on entry pipeline server
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()

        # wait and reqad the return from server
        response_line = self.process.stdout.readline()
        if not response_line:
            err = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(
                f"MCP server closed unexpectedly. Stderr: {err}"
            )

        response = json.loads(response_line)
        if "error" in response:
            raise RuntimeError(f"MCP Error: {response['error']}")
        return response.get("result", {})

    def _initialize(self) -> None:
        """Initialize the MCP session."""
        self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "agent_smith_sandbox",
                    "version": "1.0.0",
                },
            },
        )
        # Discover tools immediately
        self.list_tools()

    def list_tools(self) -> List[Dict[str, Any]]:
        """Query the MCP server for available tools."""
        result = self._send_request("tools/list")
        self.tools = result.get("tools", [])
        return self.tools

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool on the MCP server and return text content."""
        result = self._send_request(
            "tools/call",
            {"name": name, "arguments": arguments},
        )
        content_items = result.get("content", [])
        text_outputs = [
            item.get("text", "")
            for item in content_items
            if item.get("type") == "text"
        ]
        return "\n".join(text_outputs)

    def stop(self) -> None:
        """Terminate the MCP server subprocess."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                self.process.kill()
            finally:
                self.process = None


class HttpMCPClient:
    """Client for Model Context Protocol
    (MCP) servers communicating over HTTP."""

    def __init__(self, server_url: str) -> None:
        self.server_url = server_url.rstrip("/")
        self._request_id = 0
        self.tools: List[Dict[str, Any]] = []

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _send_request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a JSON-RPC 2.0 POST request over HTTP."""
        import requests

        req_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params if params is not None else {},
        }
        headers = {"Content-Type": "application/json"}

        # Handles standard MCP HTTP endpoints (/mcp or / or direct URL)
        resp = requests.post(
            self.server_url, json=payload, headers=headers, timeout=30
        )
        resp.raise_for_status()

        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"MCP HTTP Error: {data['error']}")
        return data.get("result", {})

    def start(self) -> None:
        """Initialize the HTTP MCP session."""
        self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "agent_smith_sandbox_http",
                    "version": "1.0.0",
                },
            },
        )
        self.list_tools()

    def list_tools(self) -> List[Dict[str, Any]]:
        """Query the remote HTTP MCP server for available tools."""
        result = self._send_request("tools/list")
        self.tools = result.get("tools", [])
        return self.tools

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool on the remote HTTP MCP server."""
        result = self._send_request(
            "tools/call",
            {"name": name, "arguments": arguments},
        )
        content_items = result.get("content", [])
        text_outputs = [
            item.get("text", "")
            for item in content_items
            if item.get("type") == "text"
        ]
        return "\n".join(text_outputs)

    def stop(self) -> None:
        """No-op for HTTP client since the
        remote server lifecycle is external."""
        pass
