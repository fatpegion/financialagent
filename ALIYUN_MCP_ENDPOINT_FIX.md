# FinancialAgent MCP / Endpoint Deployment Notes

## What caused `unresolved address`

`MCP服务网络异常: unresolved address (dns resolution failed)` means Bailian tried
to connect to an HTTP MCP URL whose domain cannot be resolved. This usually
happens when the config still contains a placeholder such as:

```text
https://your-mcp-domain.example.com/mcp
```

or when the URL is an internal/private address that Bailian FC cannot resolve.

## Recommended MCP deployment for this repository

The A-share tool service is a Python MCP server, so use script deployment with
`uvx` and `stdio`, not HTTP, unless you already have a real public MCP URL.

Use this shape in Bailian MCP service config:

```json
{
  "mcpServers": {
    "a-share-finance": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from",
        "https://your-oss-bucket.oss-cn-beijing.aliyuncs.com/a_share_finance_mcp-0.1.1-py3-none-any.whl",
        "a-share-finance-mcp"
      ],
      "env": {
        "A_SHARE_MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

Replace the OSS URL with the real public or signed URL of the wheel:

```text
D:\Pycharm\Financialagent\a-share-mcp-is-just-i-need\dist\a_share_finance_mcp-0.1.1-py3-none-any.whl
```

You can upload it with the helper script:

```powershell
Copy-Item D:\Pycharm\Financialagent\oss_upload.env.example D:\Pycharm\Financialagent\oss_upload.env
# Edit D:\Pycharm\Financialagent\oss_upload.env locally, then run:
D:\Pycharm\Financialagent\scripts\upload_mcp_wheel_to_oss.ps1
```

The script prints a signed URL that can be placed after `--from`.

If the package is published to PyPI, the config can be shorter:

```json
{
  "mcpServers": {
    "a-share-finance": {
      "type": "stdio",
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

## If using an HTTP MCP service

Only use HTTP mode after you have deployed a long-running remote MCP server.
Do not use placeholder domains.

Streamable HTTP:

```json
{
  "mcpServers": {
    "a-share-finance": {
      "type": "streamableHttp",
      "url": "https://your-real-domain.example.com/mcp"
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
      "url": "https://your-real-domain.example.com/sse"
    }
  }
}
```

`/messages/` is not the service URL. It is only used internally by SSE after
the `/sse` connection exists.

## Optional endpoint integration in the high-code Agent

Version `financialagent-bailian==0.1.3` can call a normal data endpoint before
asking DeepSeek/Qwen to write the final report.

Configure these environment variables in Bailian high-code app:

```text
FINANCIAL_AGENT_USE_LLM=1
OPENAI_COMPATIBLE_API_KEY=<your model key>
OPENAI_COMPATIBLE_BASE_URL=https://api.deepseek.com
OPENAI_COMPATIBLE_MODEL=deepseek-v4-flash
FINANCIAL_AGENT_DATA_ENDPOINT=https://your-real-data-endpoint.example.com/analyze
FINANCIAL_AGENT_DATA_METHOD=POST
FINANCIAL_AGENT_DATA_TIMEOUT=8
```

Optional auth:

```text
FINANCIAL_AGENT_DATA_TOKEN=<bearer token>
FINANCIAL_AGENT_DATA_API_KEY=<api key>
```

The endpoint receives JSON:

```json
{
  "query": "用户原始问题",
  "company_name": "识别出的公司名",
  "stock_code": "600519",
  "market": "sh",
  "analysis_result": {}
}
```

It may return plain text or JSON with one of these fields:

```text
context, data, result, response, text, content
```

The Agent will include that returned content in the LLM prompt. If the endpoint
is unavailable, the main `/process` API still returns normally.
