# 豆包额度命令行工具

用你豆包账号（体验套餐）的额度，在命令行里一问一答。灵犀、Codex、任何能执行 shell 的程序都能调它。

## 用法

```bash
python doubao_ask.py "你的问题"                 # 新开对话再问，默认专家模式
python doubao_ask.py "问题" --same              # 接着当前对话问，保留上下文
python doubao_ask.py "问题" --raw               # 只输出答案正文，供程序/管道消费
python doubao_ask.py "问题" --timeout 240       # 复杂问题延长等待
python doubao_ask.py "问题" --model 专家      # 切到专家模式（更强，更耗额度）
python doubao_ask.py "问题" --model 快速      # 切回快速模式（省额度）
python doubao_ask.py "问题" --verbose           # 把进度日志输出到 stderr，便于排查
```

**默认静默**：进度日志全部丢弃，stdout 只有答案正文；失败时 stdout 输出一行 ERROR。
这样调用方（灵犀 / Codex）的上下文里只有「命令 + 答案」，不会被日志淹没。

不传 `--model` 时**默认使用专家模式**（脚本会先确认并切换，日志显示 `ALREADY:专家` 或 `CLICKED -> 专家`）。要省额度就显式传 `--model 快速`。

Windows 下可直接双击/调用 `doubao.bat "问题"`。

实测耗时：简单问题约 20~30 秒（含浏览器往返与等待生成）。

## 运行条件

1. **Edge 进程在运行** —— `browser` CLI 只负责连接，源码里没有任何启动浏览器的逻辑。脚本会尝试拉起 `msedge.exe`，但插件能否挂到新进程不保证
2. **灵犀浏览器插件在线** —— 插件模式，不通就报 `session_unhealthy` / 504
3. **豆包已登录** —— 额度跟登录账号走
4. 豆包标签页**不需要**手动开（脚本会自动 navigate 到 `/chat/`），也**不需要**在前台或可见，后台/最小化均可

## 实现要点（改代码前必读）

这不是官方 API，是驱动网页界面，所以踩过的坑必须保留：

1. **输入框是 tiptap/ProseMirror 富文本 + 一层重叠的 IME textarea**
   - 写 `textarea.value`、`execCommand('insertText')` 都会被 IME 层截走
   - 唯一稳的写入方式是构造 `ClipboardEvent('paste')` 派发给 `.tiptap.ProseMirror`
2. **清空和写入不能同批执行**
   - `execCommand('selectAll')` + `delete` 之后紧接着 paste，会被 ProseMirror 忽略
   - 必须分两次 CLI 调用，中间留 0.8 秒
3. **写入成功的判据要用「paste 同批读到的 innerText 长度」**
   - 跨调用再读会因渲染滞后读到空，误判失败后会重复写入（问题文本被写两遍）
4. **新对话用 URL 导航 `https://www.doubao.com/chat/`**
   - 点侧栏「新对话」无效：那个元素是 DIV，派发鼠标事件接不上
5. **回答读取用 `[data-testid="message_text_content"]`**
   - 取最后一条；判定用「文本变化 + 连续 2 次稳定」，不要用消息条数（会因页面清理而漂移）
6. **发送按钮 class 含 `send-msg-btn`**（有内容态）或 `bg-dbx-fill-highlight`（空态），只在右下角
7. **模型切换：打开菜单必须真实鼠标点击**
   - 按钮是 `[data-testid="chat_input_action_model"]`，当前值就是它的 innerText（快速 / 专家）
   - 用 JS `click()` 打不开这个下拉，必须走 CDP 真实点击（`cli.py click --element-index`）
   - 菜单项是 `[role=menuitem]`，这两项上 JS click 有效
   - 菜单项没有 aria-checked，判断当前选中只能读按钮文本

## 已知限制

- 每问都要走一遍真实浏览器，20~30 秒起步，不适合高频/批量
- 豆包前端一改版（class 名、testid、编辑器框架）就可能失效，需要重新摸选择器
- 依赖灵犀浏览器插件；插件会话超时（`session_unhealthy`）时要重载插件
- 不是 API：没有并发、没有流式、没有 function calling，Codex 不能拿它当模型后端
- 会消耗你豆包账号的对话额度；**专家模式明显更耗额度**，日常问答用快速即可
- 模型选择是账号级持久设置，切过去不会自动切回，需要显式 `--model 快速`

## 给 Codex 用

Codex 有 shell 能力，可把它当一次性工具调用：

```
需要问豆包时执行：python "本目录绝对路径\doubao_ask.py" "问题" --raw
```

把这条写进项目的 `AGENTS.md` 即可。注意它不适合放在 Codex 的 agent 主循环里（每轮 20~30 秒会拖垮整体速度），只适合偶尔借用豆包的中文能力。

## 文件

- `doubao_ask.py` —— 主程序
- `doubao.bat` —— Windows 命令行包装