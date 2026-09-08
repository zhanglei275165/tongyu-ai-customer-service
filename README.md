# 同宇 AI 客服 (Tongyu AI Customer Service)

> 一个**通用、独立、零依赖**的网站 AI 客服。任何人搭的网站，贴一行 `<script>` 就能直接用。

![license](https://img.shields.io/badge/license-MIT-green)
![deps](https://img.shields.io/badge/dependencies-none-blue)

## 它解决什么问题

很多小团队想给网站加个 AI 客服，但被「要买 SaaS、要填 Key、数据出公网、绑定某家大模型」劝退。

同宇 AI 客服反过来：

- ✅ **通用**：配置驱动，改 `config.json` 换成你自己的公司/产品/语言/提示词，**不碰代码**。
- ✅ **独立**：纯 Python 标准库，`python server.py` 直接跑，不装任何第三方包。
- ✅ **可嵌任意网站**：把 `widget/embed.js` 那段 `<script>` 贴到你网页，右下角就有一个聊天气泡。
- ✅ **多语言**：中 / 英 / 俄自动识别，可在配置里增删任意语言。
- ✅ **留资捕获**：访客留的联系方式自动存 `leads.jsonl`，方便销售跟进。
- ✅ **可选 RAG**：在 `knowledge/` 放 `.md` 资料，客服优先引用你的资料、不乱编。
- ✅ **大脑可换**：默认对接本地「同宇引擎」(仿 Ollama, 11434)，也能一行配置换成
  OpenAI / 通义 / SiliconFlow 等任意 OpenAI 兼容端点。低配电脑 + 本地模型也能跑。

## 快速开始

```bash
# 1) 准备配置（把示例复制成正式配置）
cp config.example.json config.json
# 2) 编辑 config.json：站点名、联系方式、系统提示词（可选 knowledge/ 资料）
# 3) 启动（默认 8787 端口）
python server.py
```

浏览器打开 `http://127.0.0.1:8787` 即可看到带聊天挂件的演示站。

## 嵌到你自己的网站

在你网页的 `</body>` 前加一行：

```html
<script src="http://你的客服服务器:8787/embed.js"
        data-server="http://你的客服服务器:8787"
        data-title="在线客服" data-lang="zh" async></script>
```

刷新页面，右下角就出现客服气泡，访客点开即可对话。

> 上生产时建议把 `embed.js` 与 `server.py` 同源部署（或开好 CORS），端口用 80/443。

## 配置说明（config.json）

| 字段 | 说明 |
|---|---|
| `site_name` | 你的站点/公司名，会出现在提示词里 |
| `contact_email` / `contact_whatsapp` | 留资与提示词里的联系方式 |
| `chat_url` | 大脑端点。默认 `http://127.0.0.1:11434/api/generate`（同宇引擎；也兼容官方 Ollama 的 `/api/generate`）。若用 OpenAI / 通义 / SiliconFlow 等，填它们的 `/api/chat` 或 `/v1/chat/completions` 端点即可（服务端按 URL 自动识别协议） |
| `model` | 使用的模型名 |
| `lang_priority` | 支持的语言列表，如 `["zh","en","ru"]` |
| `system_prompts` | 各语言的系统提示词模板，支持 `{site}` `{ctx}`(资料) `{email}` `{wa}` 占位符 |

## 目录结构

```
tongyu-ai-customer-service/
├── server.py              # 客服后端（零依赖，SSE 流式 + 留资 + 可选 RAG）
├── config.example.json    # 配置模板
├── widget/
│   ├── embed.js           # 可嵌入任意网站的聊天挂件
│   └── demo.html          # 演示站
├── knowledge/             # 放 .md 资料即启用 RAG（可选）
├── leads.jsonl            # 留资记录（运行时生成）
├── README.md
└── LICENSE
```

## 关于「上架应用商店」

本项目采用 **MIT 许可证**：你可以基于它做闭源商业产品、打包成 App 上架应用商店，
**无需开源你的衍生品**，只需保留原 MIT 版权声明即可。换言之——开源这套内核，
不影响你以后把它做成自己的付费/上架产品。

## 许可证

[MIT](LICENSE)
