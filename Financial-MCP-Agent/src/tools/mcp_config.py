import sys

SERVER_CONFIGS = {
    "a_share_mcp_v2": {
        "command": sys.executable,    # 使用当前Python解释器路径，确保依赖包可用
        "args": [
            "D:/Pycharm/Financialagent/a-share-mcp-is-just-i-need/mcp_server.py"
        ],
        "transport": "stdio",
    }
}