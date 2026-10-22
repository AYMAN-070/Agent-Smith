from typing import Any, Callable, Dict, List
from src.mcp.client import MCPClient


class ToolWrapper:
    """Represents a callable Python tool connected to an MCP server.
    """

    def __init__(self, client: MCPClient, tool_schema: Dict[str, Any]) -> None:
        self.client = client
        self.name: str = tool_schema.get("name", "")
        self.__name__ = self.name
        self.__doc__ = tool_schema.get("description", "")

        # Extract the ordered list of parameter ['code', 'test_list']
        properties = tool_schema.get("inputSchema", {}).get("properties", {})
        self.param_names: List[str] = list(properties.keys())

    def _prepare_arguments(self, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """Maps positional arguments (*args) and keyword arguments (**kwargs)
        to the parameter names expected by the MCP tool.
        """
        mapped: Dict[str, Any] = {}

        # Match positional arguments (run_tests("def add()...", ["assert..."]))
        for i, val in enumerate(args):
            if i < len(self.param_names):
                param_key = self.param_names[i]
                mapped[param_key] = val

        #  Add keyword arguments (run_tests(code="...", test_list=[...]))
        mapped.update(kwargs)
        return mapped

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Executed whenever the tool is called as a Python function"""
        arguments = self._prepare_arguments(args, kwargs)
        return self.client.call_tool(self.name, arguments)


def create_tool_wrappers(client: MCPClient) -> Dict[str, Callable[..., Any]]:
    """Creates ToolWrapper instances for all tools found on the MCP server."""
    wrappers: Dict[str, Callable[..., Any]] = {}

    for tool_schema in client.tools:
        name = tool_schema.get("name")
        if name:
            wrappers[name] = ToolWrapper(client, tool_schema)

    return wrappers
