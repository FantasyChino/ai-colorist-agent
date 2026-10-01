"""Export actual tool schemas without invoking image tools."""
import asyncio
import json
from pathlib import Path
import sys
from mcp import Client, StdioServerParameters

ROOT=Path(__file__).resolve().parents[1]

async def main():
    parameters=StdioServerParameters(command=sys.executable,args=[str(ROOT/"server/mcp_server.py")],cwd=str(ROOT))
    async with Client(parameters,mode="legacy",read_timeout_seconds=30) as client:
        listing=await client.list_tools()
        catalog={"description":"Generated from MCP list_tools; actual input/output schemas.",
                 "tools":[tool.model_dump(by_alias=True,exclude_none=True) for tool in listing.tools]}
    (ROOT/"schemas/tool_schema.json").write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"tools":[t["name"] for t in catalog["tools"]]}))

if __name__=="__main__":asyncio.run(main())
