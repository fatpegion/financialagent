# Main MCP server file
import logging
import os
from datetime import datetime

from mcp.server.fastmcp import FastMCP

# Import the interface and the concrete implementation
from src.data_source_interface import FinancialDataSource
from src.baostock_data_source import BaostockDataSource
from src.utils import setup_logging

# 导入各模块工具的注册函数
from src.tools.stock_market import register_stock_market_tools
from src.tools.financial_reports import register_financial_report_tools
from src.tools.indices import register_index_tools
from src.tools.market_overview import register_market_overview_tools
from src.tools.macroeconomic import register_macroeconomic_tools
from src.tools.date_utils import register_date_utils_tools
from src.tools.analysis import register_analysis_tools
from src.tools.news_crawler import register_news_crawler_tools

# --- Logging Setup ---
# Call the setup function from utils
# You can control the default level here (e.g., logging.DEBUG for more verbose logs)
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# --- Dependency Injection ---
# Instantiate the data source - easy to swap later if needed
active_data_source: FinancialDataSource = BaostockDataSource()

# --- Get current date for system prompt ---
current_date = datetime.now().strftime("%Y-%m-%d")

# --- FastMCP App Initialization ---
app = FastMCP(
    name="a-share-finance",
    instructions=(
        "Provides China A-share market, financial report, index, macroeconomic, "
        "trading-date and news tools. Use the latest trading-date tools before "
        "claiming that data is current. Tool outputs are for reference only and "
        "do not constitute investment advice."
    ),
    host=os.getenv("A_SHARE_MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("A_SHARE_MCP_PORT", os.getenv("PORT", "8000"))),
    streamable_http_path=os.getenv("A_SHARE_MCP_HTTP_PATH", "/mcp"),
    sse_path=os.getenv("A_SHARE_MCP_SSE_PATH", "/sse"),
    message_path=os.getenv("A_SHARE_MCP_MESSAGE_PATH", "/messages/"),
    stateless_http=_env_bool("A_SHARE_MCP_STATELESS_HTTP", False),
#     server_name="a_share_data_provider",
#     description=f"""今天是{current_date}。提供中国A股市场数据分析工具。此服务提供客观数据分析，用户需自行做出投资决策。数据分析基于公开市场信息，不构成投资建议，仅供参考。

# ⚠️ 重要说明:
# 1. 最新交易日不一定是今天，需要从 get_latest_trading_date() 获取
# 2. 请始终使用 get_latest_trading_date() 工具获取实际当前最近的交易日，不要依赖训练数据中的日期认知
# 3. 当分析"最近"或"近期"市场情况时，必须首先调用 get_market_analysis_timeframe() 工具确定实际的分析时间范围
# 4. 任何涉及日期的分析必须基于工具返回的实际数据，不得使用过时或假设的日期
# 5. 新增新闻爬虫功能，可以搜索公司、行业相关新闻，辅助投资决策
# """,
    # Specify dependencies for installation if needed (e.g., when using `mcp install`)
    # dependencies=["baostock", "pandas"]
)

# --- 注册各模块的工具 ---
register_stock_market_tools(app, active_data_source)
register_financial_report_tools(app, active_data_source)
register_index_tools(app, active_data_source)
register_market_overview_tools(app, active_data_source)
register_macroeconomic_tools(app, active_data_source)
register_date_utils_tools(app, active_data_source)
register_analysis_tools(app, active_data_source)
register_news_crawler_tools(app, active_data_source)

# --- Main Execution Block ---
def main() -> None:
    """Console entry point for cloud MCP runtimes.

    Bailian's uvx mode starts the MCP server as a subprocess, so stdio is the
    default transport. For a separately hosted HTTP service, set
    A_SHARE_MCP_TRANSPORT to either "sse" or "streamable-http" and make sure
    the Bailian service type matches the endpoint path.
    """
    import os

    transport = os.getenv("A_SHARE_MCP_TRANSPORT", "stdio")
    logger.info(
        f"Starting A-Share MCP Server via {transport}... Today is {current_date}")
    app.run(transport=transport)


if __name__ == "__main__":
    main()
