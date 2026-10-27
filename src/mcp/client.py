"""MCP client implementations over stdio and HTTP."""

import json
import shlex
import subprocess
from typing import Any, Dict, List, Optional, cast


class MCPClient:
    """Client for Model Context Protocol (MCP) servers communicating over stdio."""

    def __init__(self, command: str) -> None:
        """Initialize stdio MCP client with the server launch command."""
        self.command = command
        self.process: Optional[subprocess.Popen[str]] = None
        self._request_id = 0
        self.tools: List[Dict[str, Any]] = []
        self.resources: List[Dict[str, Any]] = []
        self.prompts: List[Dict[str, Any]] = []

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
        self._initialize()

    def _next_id(self) -> int:
        """Generate and return the next JSON-RPC request identifier."""
        self._request_id += 1
        return self._request_id

    def _send_request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a JSON-RPC 2.0 request and read the response line from stdout."""
        if (
            not self.process
            or not self.process.stdin
            or not self.process.stdout
        ):
            raise RuntimeError("MCP server process is not running.")

        req_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params if params is not None else {},
        }

        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()

        response_line = self.process.stdout.readline()
        if not response_line:
            err = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(
                f"MCP server closed unexpectedly. Stderr: {err}"
            )

        response = json.loads(response_line)
        if "error" in response:
            raise RuntimeError(f"MCP Error: {response['error']}")
        return cast(Dict[str, Any], response.get("result", {}))

    def _initialize(self) -> None:
        """Initialize the MCP session and query available tools, resources, and prompts."""
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
        self.list_tools()
        try:
            self.list_resources()
        except Exception:
            pass
        try:
            self.list_prompts()
        except Exception:
            pass

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

    def list_resources(self) -> List[Dict[str, Any]]:
        """Query the MCP server for available resources."""
        result = self._send_request("resources/list")
        self.resources = result.get("resources", [])
        return self.resources

    def read_resource(self, uri: str) -> str:
        """Read a resource from the MCP server and return its text content."""
        result = self._send_request("resources/read", {"uri": uri})
        contents = result.get("contents", [])
        text_outputs = [
            item.get("text", "")
            for item in contents
            if isinstance(item, dict) and "text" in item
        ]
        return "\n".join(text_outputs)

    def list_prompts(self) -> List[Dict[str, Any]]:
        """Query the MCP server for available prompts."""
        result = self._send_request("prompts/list")
        self.prompts = result.get("prompts", [])
        return self.prompts

    def get_prompt(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Retrieve a prompt template and its messages from the MCP server."""
        params: Dict[str, Any] = {"name": name}
        if arguments:
            params["arguments"] = arguments
        return self._send_request("prompts/get", params)

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
    """Client for Model Context Protocol (MCP) servers communicating over HTTP."""

    def __init__(self, server_url: str) -> None:
        """Initialize HTTP MCP client with target server URL."""
        self.server_url = server_url.rstrip("/")
        self._request_id = 0
        self.tools: List[Dict[str, Any]] = []
        self.resources: List[Dict[str, Any]] = []
        self.prompts: List[Dict[str, Any]] = []

    def _next_id(self) -> int:
        """Generate and return the next JSON-RPC request identifier."""
        self._request_id += 1
        return self._request_id

    def _send_request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a JSON-RPC 2.0 POST request over HTTP."""
        import requests

        req_id = self._next_id()
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params if params is not None else {},
        }
        headers = {"Content-Type": "application/json"}

        resp = requests.post(
            self.server_url, json=payload, headers=headers, timeout=30
        )
        resp.raise_for_status()

        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"MCP HTTP Error: {data['error']}")
        return cast(Dict[str, Any], data.get("result", {}))

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
        try:
            self.list_resources()
        except Exception:
            pass
        try:
            self.list_prompts()
        except Exception:
            pass

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

    def list_resources(self) -> List[Dict[str, Any]]:
        """Query the remote HTTP MCP server for available resources."""
        result = self._send_request("resources/list")
        self.resources = result.get("resources", [])
        return self.resources

    def read_resource(self, uri: str) -> str:
        """Read a resource from the remote HTTP MCP server."""
        result = self._send_request("resources/read", {"uri": uri})
        contents = result.get("contents", [])
        text_outputs = [
            item.get("text", "")
            for item in contents
            if isinstance(item, dict) and "text" in item
        ]
        return "\n".join(text_outputs)

    def list_prompts(self) -> List[Dict[str, Any]]:
        """Query the remote HTTP MCP server for available prompts."""
        result = self._send_request("prompts/list")
        self.prompts = result.get("prompts", [])
        return self.prompts

    def get_prompt(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Retrieve a prompt template from the remote HTTP MCP server."""
        params: Dict[str, Any] = {"name": name}
        if arguments:
            params["arguments"] = arguments
        return self._send_request("prompts/get", params)

    def stop(self) -> None:
        """No-op for HTTP client since the remote server lifecycle is external."""
        pass
