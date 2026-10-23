# 豆包网页额度桥

用本机浏览器里**已登录的豆包网页版**回答问题，不消耗 API 额度。

> ⚠️ 这不是官方 API，是对豆包网页界面的自动化。没有流式、没有并发、没有 function calling；豆包前端改版就会失效。**自动化访问可能违反服务条款，账号风险自负。** 需要 API 级可靠性时请改用火山方舟。

```bash
git clone https://github.com/Shawn-SU-1/doubao-web-bridge
cd doubao-web-bridge
```

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

MIT
