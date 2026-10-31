"""Local stdio MCP server; no public listener, no action execution."""
from mcp.server.fastmcp import FastMCP
from service import review, demo, scenarios
mcp=FastMCP("VEIL advisory prototype")
@mcp.tool()
def veil_review(action: str, context: str) -> dict:
    """Review a hypothetical proposed action. Advisory only; does not verify authority.
    Uses configured live model; returns status=error/hold if unavailable.
    """
    return review(action,context)
@mcp.tool()
def veil_demo(scenario_id: str = "P01") -> dict:
    """Return a labeled predefined fixture demonstration, not live judgment."""
    return demo(scenario_id)
@mcp.tool()
def veil_scenarios() -> list[dict]:
    """List built-in synthetic demo scenarios."""
    return [{"id":c["id"],"action":c["request"]["action"]} for c in scenarios()]
if __name__=="__main__": mcp.run(transport="stdio")
