# A-Share Finance MCP

This package exposes the existing Baostock-based A-share tools as a cloud-ready MCP server.

## Tools

- A-share stock basic information
- Historical K-line data
- Financial report data
- Index constituents
- Market overview
- Macroeconomic data
- Trading-date helpers
- News crawling helper

## Local Build

```powershell
cd D:\Pycharm\Financialagent\a-share-mcp-is-just-i-need
python setup.py bdist_wheel
```

## Local Run

```powershell
python -m pip install dist\a_share_finance_mcp-0.1.0-py3-none-any.whl
a-share-finance-mcp
```

The default transport is `stdio`, which matches Bailian MCP `uvx` mode.

For a streamable HTTP deployment, set:

```text
A_SHARE_MCP_TRANSPORT=streamable-http
A_SHARE_MCP_HOST=0.0.0.0
A_SHARE_MCP_PORT=8000
A_SHARE_MCP_HTTP_PATH=/mcp
A_SHARE_MCP_STATELESS_HTTP=1
```

Then the MCP endpoint is:

```text
http://<host>:8000/mcp
```

For an SSE deployment, set:

```text
A_SHARE_MCP_TRANSPORT=sse
A_SHARE_MCP_HOST=0.0.0.0
A_SHARE_MCP_PORT=8000
A_SHARE_MCP_SSE_PATH=/sse
A_SHARE_MCP_MESSAGE_PATH=/messages/
```

Then the MCP endpoint is:

```text
http://<host>:8000/sse
```

## Bailian uvx Config

Use this after the package is published to PyPI or made available from a Git URL/OSS URL that `uvx` can install.

```json
{
  "mcpServers": {
    "a-share-finance": {
      "command": "uvx",
      "args": [
        "a-share-finance-mcp"
      ],
      "env": {
        "A_SHARE_MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

## Bailian HTTP Config

Use this only after deploying the package as a long-running HTTP service.

Streamable HTTP:

```json
{
  "mcpServers": {
    "a-share-finance": {
      "type": "streamableHttp",
      "url": "https://your-domain.example.com/mcp"
    }
  }
}
```

SSE:

```json
{
  "mcpServers": {
    "a-share-finance": {
      "type": "sse",
      "url": "https://your-domain.example.com/sse"
    }
  }
}
```

If installing from a Git repository, use:

```json
{
  "mcpServers": {
    "a-share-finance": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/fatpegion/financialagent.git#subdirectory=a-share-mcp-is-just-i-need",
        "a-share-finance-mcp"
      ],
      "env": {
        "A_SHARE_MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

## Troubleshooting

`No active SSE connection for session ...` means the client is sending MCP
messages through an SSE-style session, but the server side has no open SSE
connection for that session. Check these first:

- If the Bailian install mode is `uvx`, keep `A_SHARE_MCP_TRANSPORT=stdio`.
- If the Bailian install mode is `http` and the type is `sse`, the URL must end
  with `/sse`, and the server must run with `A_SHARE_MCP_TRANSPORT=sse`.
- If the Bailian install mode is `http` and the type is `streamableHttp`, the
  URL must end with `/mcp`, and the server must run with
  `A_SHARE_MCP_TRANSPORT=streamable-http`.
- Do not use `/messages/` as the service URL. It is only the internal POST path
  used by the SSE transport after `/sse` has opened a session.
