"""Real SDK client/server round trip; no live provider calls."""
import asyncio
import json
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def main():
    params=StdioServerParameters(command=sys.executable,args=[str(Path(__file__).with_name("mcp_server.py"))])
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            tools=await session.list_tools()
            assert {t.name for t in tools.tools}=={"veil_review","veil_demo","veil_scenarios"}
            for id,expected in (("P01","proceed"),("A01","ask"),("H01","hold")):
                response=await session.call_tool("veil_demo",{"scenario_id":id})
                assert not response.isError
                data=json.loads(response.content[0].text)
                assert data["decision"]==expected and not data["eligible_to_execute"]
            response=await session.call_tool("veil_review",{"action":"","context":"Invalid input"})
            data=json.loads(response.content[0].text)
            assert data["status"]=="error" and data["decision"]=="hold"
    print("MCP round trip passed: discovery, proceed/ask/hold fixtures, invalid-input hold.")
if __name__=="__main__": asyncio.run(main())
