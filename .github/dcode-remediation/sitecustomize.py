import os
from pathlib import Path


READ_TOOLS = {"ls", "read_file", "glob", "grep"}
WRITE_TOOLS = {"write_file", "edit_file"}
WORK = Path("/work").resolve()
SKILLS = Path("/tmp/dcode-home/.deepagents/agent/skills").resolve()
BLOCKED = {".git", ".github", ".deepagents", ".agents", ".claude", ".mcp.json", "AGENTS.md", "CLAUDE.md"}


def permitted(call):
    name, args = call["name"], call["args"]
    if name not in READ_TOOLS | WRITE_TOOLS:
        return False
    raw = args.get("file_path" if name in {"read_file", "write_file", "edit_file"} else "path") or "/work"
    try:
        path = Path(raw).resolve()
        for field in ("pattern", "glob") if name == "glob" else ("glob",):
            pattern = args.get(field) or ""
            if ".." in pattern or "\\" in pattern:
                return False
        if name in READ_TOOLS and path.is_relative_to(SKILLS):
            return True
        if not path.is_relative_to(WORK):
            return False
        return not any(part in BLOCKED or part.startswith(".env") for part in path.relative_to(WORK).parts)
    except (TypeError, ValueError, OSError, RuntimeError):
        return False


def install():
    from langchain_core.messages import ToolMessage
    from langgraph.prebuilt import ToolNode
    from importlib.metadata import version

    if version("langgraph-prebuilt") != "1.1.0":
        raise RuntimeError("Unverified tool runtime")
    original_sync = ToolNode._execute_tool_sync
    original_async = ToolNode._execute_tool_async

    def denied(request):
        return ToolMessage(content="Denied: only static source-file tools are permitted.",
                           tool_call_id=request.tool_call["id"], status="error")

    def sync(self, request, input_type, config):
        if not permitted(request.tool_call):
            return denied(request)
        return original_sync(self, request, input_type, config)

    async def asynchronous(self, request, input_type, config):
        if not permitted(request.tool_call):
            return denied(request)
        return await original_async(self, request, input_type, config)

    ToolNode._execute_tool_sync = sync
    ToolNode._execute_tool_async = asynchronous


if os.environ.get("DCODE_STATIC_POLICY") == "1":
    try:
        install()
    except BaseException:
        os._exit(78)
