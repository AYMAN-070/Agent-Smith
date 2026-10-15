from typing import Any, Callable, Dict
from src.mcp.client import MCPClient


def create_tool_wrappers(client: MCPClient) -> Dict[str, Callable[..., Any]]:
    """
    Dynamically generate callable Python functions for each tool discovered on the MCP server.

    According to Agent Smith specification (Section V.2.2 & V.2.4):
    'MCP tools must be callable as Python functions from the sandbox'
    """
    wrappers: Dict[str, Callable[..., Any]] = {}

    for tool_schema in client.tools:
        tool_name = tool_schema.get("name")
        if not tool_name:
            continue

        # Create a closure binding tool_name and client
        def make_wrapper(name: str) -> Callable[..., Any]:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                # If positional arguments are passed, map them if possible
                arguments: Dict[str, Any] = {}
                properties = tool_schema.get("inputSchema", {}).get("properties", {})
                param_names = list(properties.keys())

                # Map positional args to schema param names
                for i, arg in enumerate(args):
                    if i < len(param_names):
                        arguments[param_names[i]] = arg

                # Add keyword arguments
                arguments.update(kwargs)

                # Send remote call to MCP server
                return client.call_tool(name, arguments)

            wrapper.__name__ = name
            wrapper.__doc__ = tool_schema.get("description", "")
            return wrapper

        wrappers[tool_name] = make_wrapper(tool_name)

    return wrappers
