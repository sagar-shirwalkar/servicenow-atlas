---
name: atlas-add-tool
description: >-
  Add a new MCP tool to the atlas-fs or atlas-rag server. Covers tool
  definition, handler function, parameter schema, and register call.
  Use when implementing a new feature that needs to be exposed as an MCP tool.
---

## When to use

- User asks to "add a new tool", "create a tool for X", "expose Y as an MCP tool"
- User is building a new capability that needs to be callable by an LLM
- User wants to understand the existing tool registration pattern

## Not for

- General code changes outside tool definitions
- Modifying the embedder or chunker internals
- Changing the MCP server lifecycle (startup, shutdown, transport)

## Prerequisites

Read the existing tool implementations in:
- `atlas/rag_server.py` — tools on the RAG server (semantic search, etc.)
- `atlas/fs_server.py` — tools on the filesystem server (read, list, search, etc.)

## Workflow

### 1. Locate the right server file

| Tool belongs to | Server file |
|---|---|
| Document search / RAG | `atlas/rag_server.py` |
| File listing / reading | `atlas/fs_server.py` |
| Build / maintenance | Consider a new server or `atlas/doctor.py` |

### 2. Follow the existing pattern

Each tool has three parts in the server file:

**a) Tool docstring + `@server.list_tools()` handler**

```python
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # existing tools ...
        Tool(
            name="your_tool_name",
            description="What the tool does — be specific",
            inputSchema={
                "type": "object",
                "properties": {
                    "param_name": {
                        "type": "string",
                        "description": "What this parameter is for",
                    },
                },
                "required": ["param_name"],
            },
        ),
    ]
```

- Tool names: `snake_case`, conventionally matching the function name.
- Descriptions: written for an LLM reader. Include edge cases, defaults, and example values.
- Parameters: use JSON Schema types (`string`, `integer`, `array`, etc.). Mark `required` explicitly.

**b) The `@server.call_tool()` handler branch**

```python
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "your_tool_name":
        result = await your_handler(arguments)
        return [TextContent(type="text", text=result)]
    elif name == "existing_tool":
        ...
```

- Handler returns `list[TextContent]`.
- For errors, raise `ValueError` with a clear message — the MCP framework serialises it.
- Keep the handler thin; business logic goes in private helpers.

**c) The business logic function** (inline or imported)

```python
async def your_handler(args: dict) -> str:
    param = args["param_name"]
    # ... do the work ...
    return json.dumps(result, indent=2, default=str)
```

### 3. Register the tool as a console script (if needed)

If the tool needs a CLI equivalent, add an entry in `pyproject.toml` under `[project.scripts]`:

```toml
atlas-your-tool = "atlas.module:main"
```

### 4. Sync vs async decision

| Criterion | Use |
|---|---|
| I/O-bound (file read, HTTP, subprocess) | `async def` |
| CPU-bound (embedding, chunking) | `async def` that calls `loop.run_in_executor` for the heavy part |
| Trivial (string formatting, data lookup) | `def` is fine |

### 5. Parameter schema rules

- `type`: one of `string`, `integer`, `number`, `boolean`, `array`, `object`.
- Use `description` on every parameter — the LLM client reads these.
- Use `enum` for constrained values:
  ```json
  "backend": {
    "type": "string",
    "enum": ["mlx", "onnx-cpu", "onnx-gpu"]
  }
  ```
- Use `default` for optional parameters (omit from `required` array).

## Example

See `atlas/rag_server.py` for a real tool (semantic search), and `atlas/fs_server.py` for filesystem tools (list publications, list files, read file, search).

## References

- `atlas/rag_server.py` — RAG tool pattern (embed queries + cosine similarity + return results)
- `atlas/fs_server.py` — FS tool pattern (MCP resource enumeration + tool calls)
- MCP Python SDK documentation for `Tool`, `TextContent`, `server.list_tools`, `server.call_tool`
