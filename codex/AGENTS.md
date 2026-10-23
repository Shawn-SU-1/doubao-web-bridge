# 豆包网页额度协议（Codex / 任意浏览器工具通用）

用本机浏览器里已登录的豆包网页版回答问题，不消耗 API 额度。

本文件是**操作协议**，不含代码依赖：只要你的 agent 能驱动浏览器并能执行 JavaScript，就能照着做。适用于 Codex（Chrome 插件 / Playwright MCP / Chrome DevTools MCP）、Cursor、Claude Code、Cline 等任何情形。

---

## 前置条件

| 条件 | 说明 |
|---|---|
| 浏览器已登录 `doubao.com` | 额度跟登录账号走；未登录时页面只有「登录」按钮，此时必须停下让用户扫码，不要代填账号 |
| agent 有浏览器工具 | 需要能「导航 / 执行 JS」两个能力 |
| 不要求窗口在前台 | 后台标签页即可 |

Codex 的浏览器工具都满足：Chrome 插件支持 raw CDP，Playwright MCP 有 `browser_evaluate`，Chrome DevTools MCP 有 `evaluate_script`。

---

## 流程总览

```
1. 导航到 https://www.doubao.com/chat/     ← 每次新对话，避免上下文污染
2. 等待输入框就绪（约 2~4 秒）
3. 写入问题
4. 点击发送
5. 每 2~3 秒读一次消息列表，直到出现「不是问题本身」的新文本且连续两次不变
6. 返回最后一条消息文本
```

**单次耗时 20~30 秒**，不要设短超时。

---

## 步骤 1：导航

```
https://www.doubao.com/chat/
```

不要带 query 参数，不要复用上一次的对话 URL（否则上下文会累积、额度浪费、答案被前文干扰）。需要追问时才保留当前对话。

## 步骤 2：等输入框就绪

执行 JS，返回 true 才能继续：

```js
return !!document.querySelector('.tiptap.ProseMirror');
```

不返回 true 就等 1 秒重试，最多 10 次。

## 步骤 3：写入问题（两种方式，优先第一种）

### 方式 A：工具自带的输入能力（首选）

豆包输入框是 **tiptap / ProseMirror 富文本**，不是 textarea。支持 contenteditable 的工具可以直接填：

- Playwright：`page.fill('.tiptap.ProseMirror', text)` 或 `locator.fill(text)`
- 一般浏览器工具：先 `click` 该元素，再 `type` / `keyboard.type`

真实键盘事件最稳，能正确触发 React 状态。

> 说明：方式 A 是在 Playwright 的 `fill` 支持 contenteditable 这一能力上推断的，**未在真实 Codex 环境实测**（本机未装 Codex）。如果 fill 后页面没有反应，直接用方式 B，它在浏览器页面里逐字验证过。

### 方式 B：paste 事件（A 不生效时用）

```js
const pm = document.querySelector('.tiptap.ProseMirror');
const q = '这里放问题文本';
pm.focus();
const dt = new DataTransfer();
dt.setData('text/plain', q);
pm.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
return JSON.stringify({ok: pm.innerHTML.indexOf(q.slice(0, 6)) >= 0});
```

- **判据必须看 `innerHTML`，不能看 `innerText`**：页面未渲染时 `innerText` 是空的，会误判失败并重复写入，导致问题文本被写两遍
- 返回 `ok:false` 才重试；不要在 `ok:true` 时重写

### 不要用的方式

- ❌ `textarea.value = text` —— 页面里有个和编辑器完全重叠的 IME `textarea`，写它无效
- ❌ `document.execCommand('insertText')` —— 焦点会被 IME 层抢走，内容进不去（除非确认 textarea 不存在）
- ❌ 一次性「清空 + 写入」：`execCommand('selectAll')` + `delete` 之后同批执行 paste 会被忽略，两者必须分开两次调用

## 步骤 4：发送

```js
const bs = [...document.querySelectorAll('button')].filter(b => {
  const c = (b.className || '').toString();
  const r = b.getBoundingClientRect();
  return r.width > 0 && (c.includes('send-msg-btn') || c.includes('bg-dbx-fill-highlight'));
});
if (!bs.length) return 'NO_SEND';
bs[bs.length - 1].click();
return 'CLICKED';
```

- 按钮在输入框右下角；有内容时 class 含 `send-msg-btn`，空态时含 `bg-dbx-fill-highlight`
- 如果工具的 Enter 键是真实键盘事件，按 Enter 也可以；合成的 KeyboardEvent 不保证生效

## 步骤 5：读取答案

```js
const t = [...document.querySelectorAll('[data-testid="message_text_content"]')];
return JSON.stringify({
  n: t.length,
  last: t.length ? t[t.length - 1].innerText : ''
});
```

判定规则：

1. 发送前先记一次 `n` 和 `last`
2. 发送后轮询，`last` 必须**既不是自己问的问题**、**也不是发送前那条旧文本**
3. 连续两次读到相同内容才算生成完成

**不要用消息条数判完成**，条数会因页面清理、是否新建对话而漂移；用文本变化判断。

## 步骤 6（可选）：切换模型

豆包输入框右下角有模型选择器，两档：**快速** / **专家**。

**读当前值：**

```js
const m = document.querySelector('[data-testid="chat_input_action_model"]');
return m ? m.innerText.trim() : '';
```

**打开菜单必须用真实鼠标点击**（JS `click()` 打不开这个下拉）。先取坐标：

```js
const m = document.querySelector('[data-testid="chat_input_action_model"]');
const r = m.getBoundingClientRect();
return JSON.stringify({x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2)});
```

然后用 CDP `Input.dispatchMouseEvent` 在该坐标依次发 `mousePressed` / `mouseReleased`，或用工具的 click 原语点这个元素。

**选中菜单项**（子菜单项用 JS click 有效）：

```js
const it = [...document.querySelectorAll('[role=menuitem]')]
  .find(e => (e.innerText || '').trim() === '专家');
if (!it) return 'NO_ITEM';
it.click();
return 'CLICKED';
```

- 菜单项没有 `aria-checked`，判断当前选中只能读按钮文本
- 模型是账号级持久设置，切过去不会自动切回

---

## 已知陷阱清单

| 现象 | 原因 |
|---|---|
| 问题被写了两遍 | 用 `innerText` 判写入成功，实际内容已在 `innerHTML` 中 |
| 点了发送没反应 | 发送按钮选择器只匹配了空态 class |
| 读到的是上一轮的答案 | 没有记发送前的基线文本 |
| 读到「我先核实…」这类短句 | 专家模式会先输出思考块，它也算 `message_text_content`；等生成结束再取最后一条 |
| 内容写不进去 | 用了 `textarea.value` 或 `execCommand` |
| 菜单打不开 | 用了 JS click，必须真实鼠标事件 |
| `nav` 到 `/chat/` 后仍带着旧对话 | 用的是 `?id=xxx` 形式的 URL |

## 额度说明

- 消耗的是豆包账号的对话额度，不是 token；专家模式明显更耗
- 批量场景应主动切「快速」，或改成一次性把多个问题合并在一个 prompt 里

## 边界与免责

- **非官方工具，与豆包 / 字节跳动无任何关联、未获授权。** 自动化访问可能违反《豆包用户协议》，账号有被限流或封禁风险，由使用者自担；不得用于商业转售、批量抓取或规避风控
- **这不是官方 API**：没有流式、没有并发、没有 function calling
- 豆包前端改版（class 名、`data-testid`、编辑器框架）就会失效，需要重新定位选择器
- 不要用于需要精确复现的任务；需要 API 级可靠性时应该引导用户走火山方舟
