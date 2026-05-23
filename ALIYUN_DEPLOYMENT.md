# FinancialAgent 鐧剧偧楂樹唬鐮侀儴缃茶鏄?
杩欎釜鍖呮槸 FinancialAgent 鐨勮交閲忎簯绔叆鍙ｏ紝鐢ㄤ簬鐧剧偧楂樹唬鐮佸簲鐢ㄣ€傚畠涓嶄細鎶婃湰鍦?Qwen 鏉冮噸銆佽缁冩暟鎹€乣.env`銆佹棩蹇楀拰鍘嗗彶鎶ュ憡鎵撹繘 wheel锛岄伩鍏嶆瀯寤鸿秴鏃躲€?
## 鍏ュ彛

- 鍋ュ悍妫€鏌ワ細`GET /health`
- 瀵硅瘽鎺ュ彛锛歚POST /process`
- 鍏煎娴嬭瘯锛歚GET/POST /chat`
- 榛樿绔彛锛歚8080`

## 鐜鍙橀噺

鍦ㄧ櫨鐐煎簲鐢ㄩ厤缃噷璁剧疆锛?
```text
OPENAI_COMPATIBLE_API_KEY=浣犵殑妯″瀷API Key
OPENAI_COMPATIBLE_BASE_URL=https://api.deepseek.com
OPENAI_COMPATIBLE_MODEL=deepseek-v4-flash
FINANCIAL_AGENT_USE_LLM=1
```

MCP 工具接入（在高代码应用工具页添加 MCP 服务后，在代码中实际调用）：

```text
DASHSCOPE_API_KEY=<你的百炼 API Key>
FINANCIAL_AGENT_USE_MCP=1
FINANCIAL_AGENT_MCP_URL=https://dashscope.aliyuncs.com/api/v1/mcps/<mcpCode>/mcp
FINANCIAL_AGENT_MCP_TIMEOUT=20
```

当前适配器会优先调用 A 股 MCP 工具补充行情、基础信息、K 线、财务和新闻数据，再把工具结果传给模型生成报告。MCP 调用失败不会中断 `/process`。

濡傛灉涓嶉厤缃?API Key锛屾帴鍙ｄ粛鍙繑鍥炶鍒欏紩鎿庡垎鏋愮粨鏋滐紝鏂逛究鍏堥€氳繃 API 娴嬭瘯銆?
## 鏈湴鎵撳寘

鍦ㄩ」鐩牴鐩綍鎵ц锛?
```powershell
cd /d D:\Pycharm\Financialagent
python setup.py bdist_wheel
```

鐢熸垚鐨勬枃浠跺湪锛?
```text
D:\Pycharm\Financialagent\dist\financialagent_bailian-0.1.1-py3-none-any.whl
```

涓婁紶杩欎釜 `.whl` 鍒扮櫨鐐奸珮浠ｇ爜搴旂敤銆?
## API 娴嬭瘯杈撳叆

浣跨敤 POST锛屼笉瑕佺敤 GET 璋?`/process`锛?
```json
{
  "message": "璇峰垎鏋愯吹宸炶寘鍙?600519)鐨勬姇璧勪环鍊笺€佹柊闂绘儏鎰熷拰涓昏椋庨櫓"
}
```

杩斿洖閲屼細鍚屾椂鍖呭惈锛?
- `response`
- `text`
- `output[0].content[0].text`

杩欐牱鍏煎 API 娴嬭瘯鍜屾枃鏈綋楠屻€?
## 鍚庣画 MCP 鎺ュ叆

褰撳墠 wheel 鍏堜繚璇侀珮浠ｇ爜搴旂敤鑳界ǔ瀹氭瀯寤哄拰鍚姩銆傚畬鏁?MCP 宸ュ叿閾鹃渶瑕佸崟鐙鐞嗭細鎶?A 鑲?MCP 鏈嶅姟鏀规垚浜戠鍙惎鍔ㄧ殑杩滅▼ MCP 鎴栨妸闇€瑕佺殑 baostock 宸ュ叿鍐呰仈鍒拌交閲忓寘閲岋紝鍐嶅湪鐧剧偧 MCP 閰嶇疆涓帴鍏ャ€?
