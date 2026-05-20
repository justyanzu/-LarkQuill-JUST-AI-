# Routed Image Gen MCP (stdio)

OpenClaw 可用的 **stdio MCP 生图服务**：模型路由 + DeepSeek 多模态评审 + 最多 **3 轮** 生图迭代（熔断）。

## 能力

| 路由 | 模型 | 场景 |
|------|------|------|
| `premium` | `gpt-image-2`（OpenAI） | 中文海报排版、专业设计、清晰文字 |
| `standard` | `doubao-seedream-5.0-lite`（火山方舟） | 一般生图 |

`route_mode=auto` 时根据提示词关键词或 `needs_chinese_text` / `needs_poster_layout` / `needs_professional_design` 自动选路。

每轮生图后由 **DeepSeek `deepseek-v4-pro`** 看图评审；不合格则在原提示词上追加 `prompt_patch` 再生成，**最多 3 次**（硬熔断）。

## MCP 工具

- `preview_image_route` — 仅预览路由，不调付费 API
- `generate_image_iterative` — 完整「生图 → 评审 → 改 prompt → 再生」流程

## 安装

```bash
cd mcp-servers/routed-image-gen
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 API Key
```

## 本地试运行（stdio）

```bash
cd mcp-servers/routed-image-gen
set PYTHONPATH=src
python -m routed_image_gen
```

## OpenClaw 配置示例

在 OpenClaw 配置 `mcp.servers` 中增加（路径按本机修改）：

```json
{
  "mcp": {
    "servers": {
      "routed-image-gen": {
        "command": "python",
        "args": ["-m", "routed_image_gen"],
        "cwd": "D:/Agent/openclaw-main/openclaw-main/mcp-servers/routed-image-gen",
        "env": {
          "PYTHONPATH": "src",
          "OPENAI_API_KEY": "sk-...",
          "VOLCENGINE_API_KEY": "...",
          "DEEPSEEK_API_KEY": "sk-...",
          "IMAGE_GEN_OUTPUT_DIR": "D:/Agent/openclaw-main/openclaw-main/mcp-servers/routed-image-gen/generated-images"
        }
      }
    }
  }
}
```

或使用 `openclaw mcp set`（若已启用 `/mcp` 命令）。

## 环境变量

见 `.env.example`。

## 与 OpenClaw 主 Agent 的分工

- **迭代与评审**在本 MCP 内完成（调用 DeepSeek vision），OpenClaw 主模型只需在需要生图时调用 **`generate_image_iterative`** 一次。
- 返回 JSON 含 `final_image_path`、`final_image_url`（若有）、`history`；主 Agent 可将路径/链接发给用户或继续做对话。

## 测试

```bash
cd mcp-servers/routed-image-gen
PYTHONPATH=src python -m pytest tests/ -q
```
