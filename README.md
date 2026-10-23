# 豆包网页额度桥

用本机浏览器里**已登录的豆包网页版**回答问题，不消耗 API 额度。

> ⚠️ **非官方工具，与豆包 / 字节跳动无任何关联，未获授权。** 这是对网页界面的自动化，不是 API；可能违反《豆包用户协议》，**有账号被限流或封禁的风险，全部责任由使用者自负**。使用前请先读[免责声明](#️-免责声明)。

```bash
git clone https://github.com/Shawn-SU-1/doubao-web-bridge
cd doubao-web-bridge
```

## ⚠️ 免责声明

**本项目为个人编写的非官方工具，与豆包、字节跳动、火山引擎无任何关联，未获其授权或认可。**

- **是界面自动化，不是 API**：自动化访问可能违反《豆包用户协议》，账号可能被限流、限制功能或封禁，**风险与后果由使用者自行承担**
- **只用你自己的额度**：只调用你本人已登录、已获授权的账号；不含任何绕过登录、鉴权、计费的手段，不提供、不共享、不代充任何账号或额度
- **禁止用途**：商业转售、代客刷量、批量抓取、规避风控、生成违法内容、冒充官方服务
- **无担保**：按「现状」提供，前端改版即失效；因使用或无法使用本工具造成的任何直接或间接损失，作者不承担责任
- **合规自负**：请自行确认符合当地法律法规与平台服务条款；官方若有异议，请立即停止使用并删除

完整版（含英文）见 [`DISCLAIMER.md`](DISCLAIMER.md)。

## 三种用法，按你的环境挑

| 你的环境 | 用哪个 | 依赖 |
|---|---|---|
| **Codex**（Chrome 插件 / Playwright MCP / Chrome DevTools MCP）<br>Cursor / Claude Code / Cline | [`codex/AGENTS.md`](codex/AGENTS.md) 操作协议 | 零依赖，只需浏览器工具能执行 JS |
| 任何装了 Python 的机器 | `scripts/doubao_ask_pw.py`（Playwright 版） | `pip install playwright` + 本机 Edge/Chrome |
| **灵犀**（WPS 灵犀） | [`SKILL.md`](SKILL.md) + `scripts/doubao_ask.py` | 依赖灵犀自带的 browser 技能与插件 |

三条路径干的是同一件事，区别只是「谁来做那几步」：

- **Codex 路线**：把协议喂给 agent，它用自己的浏览器工具执行 JS，自己轮询等答案
- **Playwright 路线**：脚本自己启动浏览器并跑完整流程，不需要任何 agent 框架
- **灵犀路线**：依赖灵犀的浏览器 CLI，封装成一条命令

## Codex 怎么用（推荐先看这个）

### 1. 确认浏览器工具

任选其一：

```bash
# Playwright MCP
codex mcp add playwright npx "@playwright/mcp@latest"

# 或 Chrome DevTools MCP（Node 22+）
codex mcp add chrome-devtools npx "chrome-devtools-mcp@latest"
```

Codex 自带的 Chrome 插件也够用（支持 raw CDP）。

### 2. 放协议文件

把 `codex/AGENTS.md` 放到你的项目根目录，改名为 `AGENTS.md`，或合并进已有的 `AGENTS.md`。

### 3. 直接用

```
按 AGENTS.md 的豆包协议，问豆包：用一句话说明什么是幂等
```

### 前提

- 浏览器里已经登录 `doubao.com`（额度跟账号走）
- 未登录时 agent 必须停下让你扫码，不能代登录

## 独立运行（Playwright，不需要灵犀也不需要 Codex）

```bash
pip install playwright            # 不用 playwright install，直接用系统 Edge

python scripts/doubao_ask_pw.py "你的问题"
```

首次运行会弹出浏览器窗口，**未登录时请在里面扫码登录一次**，登录态保存在 `profile/` 目录，之后免登录。

| 参数 | 说明 |
|---|---|
| `--model 快速` | 省额度（默认专家） |
| `--channel chrome` | 默认 `msedge`，可换成 `chrome` 或 `chromium` |
| `--headless` | 无头模式（首次登录不要用） |
| `--verbose` | 输出进度日志 |

状态说明：核心读写逻辑与灵犀版完全一致，已在真实页面逐条验证；Playwright 路径已验证能启动浏览器、打开豆包、识别登录态，但**带登录态走完整问答的流程未做端到端实测**，首次使用请留意输出。

## 灵犀怎么用

```bash
python scripts/doubao_ask.py "你的问题"              # 默认专家模式
python scripts/doubao_ask.py "问题" --model 快速      # 省额度
python scripts/doubao_ask.py "问题" --same           # 接着当前对话追问
python scripts/doubao_ask.py "问题" --verbose        # 排查用
```

默认静默：stdout 只有答案正文，失败时输出一行 `ERROR:`。

**运行条件**

| 条件 | 必需 | 说明 |
|---|---|---|
| Edge 进程在运行 | 是 | 脚本会尝试用 `msedge.exe` 拉起，但插件能否跟上不保证 |
| 灵犀浏览器插件在线 | 是 | 插件模式，断了报 `session_unhealthy` |
| 豆包已登录 | 是 | |
| 豆包标签页存在 | 否 | 脚本自动打开 `/chat/` |
| 窗口在前台 | 否 | 后台标签页即可 |

## 目录结构

```
.
├── README.md            # 本文件
├── DISCLAIMER.md        # 免责声明（完整版，含英文）
├── SKILL.md             # 灵犀技能入口
├── reference.md         # 实现细节与踩坑记录
├── scripts/
│   ├── doubao_ask.py    # 灵犀版（封装成一条命令）
│   ├── doubao_ask_pw.py # Playwright 独立版（不依赖灵犀）
│   └── doubao.bat       # Windows 命令行包装
└── codex/
    └── AGENTS.md        # Codex / 通用浏览器 agent 的操作协议
```

## 核心难点（自己实现也会踩）

1. 输入框是 **tiptap / ProseMirror** 富文本，且叠了一层完全重叠的 IME `textarea`。写 `textarea.value` 或 `execCommand('insertText')` 都会被截走
2. 写入判据看 **`innerHTML`**，不能看 `innerText`——未渲染时后者为空，误判会导致问题被写两遍
3. 「清空」和「写入」必须分成两次调用，同批执行时 paste 被忽略
4. 读答案用 `[data-testid="message_text_content"]`，**按文本变化判完成**，不要按消息条数
5. 专家模式会先输出思考块，它同样占用 `message_text_content`，要等生成结束取最后一条
6. 模型下拉必须**真实鼠标点击**打开，JS `click()` 无效；菜单项反过来 JS click 可用

细节和排查过程见 [`reference.md`](reference.md)。

## 已知限制

- 单次 20~30 秒，不适合批量与高频
- 消耗账号对话额度，专家模式更耗
- 无并发、无流式、无 function calling
- 依赖豆包前端结构，改版即失效

## License

MIT。使用前请阅读 [免责声明](DISCLAIMER.md)——本项目为非官方工具，账号风险自负。
