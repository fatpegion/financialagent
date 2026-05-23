# FinancialAgent

FinancialAgent is a stock investment analysis project with:

- lightweight Alibaba Cloud Bailian high-code adapter;
- optional OpenAI-compatible LLM generation, tested with DeepSeek-compatible endpoints;
- A-share MCP tools backed by Baostock;
- local training and test scripts for sentiment and risk models.

## Bailian High-Code App

Build the high-code wheel from the repository root:

```powershell
python setup.py bdist_wheel
```

Upload:

```text
dist/financialagent_bailian-0.1.7-py3-none-any.whl
```

Runtime routes:

- `GET /health`
- `POST /process`
- `POST /chat`

Typical environment variables:

```text
FINANCIAL_AGENT_USE_LLM=1
OPENAI_COMPATIBLE_API_KEY=<your-key>
OPENAI_COMPATIBLE_BASE_URL=https://api.deepseek.com
OPENAI_COMPATIBLE_MODEL=deepseek-v4-flash
```

Optional external data endpoint:

```text
FINANCIAL_AGENT_DATA_ENDPOINT=https://your-real-data-endpoint.example.com/analyze
FINANCIAL_AGENT_DATA_METHOD=POST
FINANCIAL_AGENT_DATA_TIMEOUT=8
```

Optional Bailian MCP tool endpoint:

```text
DASHSCOPE_API_KEY=<your-bailian-api-key>
FINANCIAL_AGENT_USE_MCP=1
FINANCIAL_AGENT_MCP_URL=https://dashscope.aliyuncs.com/api/v1/mcps/<mcpCode>/mcp
FINANCIAL_AGENT_MCP_TIMEOUT=20
```

If `FINANCIAL_AGENT_MCP_URL` is not set, the adapter uses the current A-share
MCP endpoint configured for this project. MCP failures are non-fatal, so
`/process` still returns a normal answer if the tool is temporarily unavailable.

## Bailian MCP Service

The A-share MCP package lives in:

```text
a-share-mcp-is-just-i-need
```

After this repository is pushed to GitHub, Bailian can install it directly with
`uvx`:

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

Use `uvx + stdio` for this Python MCP service. Do not configure it as a remote
SSE URL unless you have separately deployed a long-running HTTP MCP server.
