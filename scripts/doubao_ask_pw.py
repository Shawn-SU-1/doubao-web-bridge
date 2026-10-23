# -*- coding: utf-8 -*-
"""doubao_ask_pw.py —— Playwright 独立版，不依赖灵犀 / Codex。

用本机已安装的 Edge（或 Chrome）打开豆包网页版，用登录账号的额度问答。

首次运行：会弹出浏览器，若未登录请在窗口里扫码登录一次。
登录态保存在 ../profile/ 目录，之后免登录。

用法：
  pip install playwright
  python doubao_ask_pw.py "你的问题"
  python doubao_ask_pw.py "问题" --model 快速
  python doubao_ask_pw.py "问题" --channel chrome
  python doubao_ask_pw.py "问题" --show        # 显示浏览器窗口（默认显示，便于扫码）

注意：本脚本为实验版本，写入与读取策略与灵犀版一致（已逐条验证），
但 Playwright 环境的完整登录态流程未经端到端实测，首次使用请留意输出。
"""
import sys, os, time, json, argparse

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print('ERROR: 未安装 playwright，请先执行： pip install playwright')
    sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE_DIR = os.path.abspath(os.path.join(HERE, '..', 'profile'))
CHAT_URL = 'https://www.doubao.com/chat/'

JS_READY = "return !!document.querySelector('.tiptap.ProseMirror');"

JS_LOGIN_STATE = """() => {
  const loginBtn = [...document.querySelectorAll('button')]
    .some(b => (b.innerText || '').trim() === '登录');
  const pm = !!document.querySelector('.tiptap.ProseMirror');
  return JSON.stringify({login: loginBtn, editor: pm});
}"""

JS_PASTE = """(q) => {
  const pm = document.querySelector('.tiptap.ProseMirror');
  if (!pm) return JSON.stringify({err: 'NO_PM'});
  pm.focus();
  const dt = new DataTransfer();
  dt.setData('text/plain', q);
  pm.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
  return JSON.stringify({ok: pm.innerHTML.indexOf(q.slice(0, 6)) >= 0});
}"""

JS_SEND = """() => {
  const bs = [...document.querySelectorAll('button')].filter(b => {
    const c = (b.className || '').toString();
    const r = b.getBoundingClientRect();
    return r.width > 0 && (c.includes('send-msg-btn') || c.includes('bg-dbx-fill-highlight'));
  });
  if (!bs.length) return 'NO_SEND';
  bs[bs.length - 1].click();
  return 'CLICKED';
}"""

JS_READ = """() => {
  const t = [...document.querySelectorAll('[data-testid="message_text_content"]')];
  return JSON.stringify({n: t.length, last: t.length ? t[t.length - 1].innerText : ''});
}"""

JS_MODEL_CUR = """() => {
  const m = document.querySelector('[data-testid="chat_input_action_model"]');
  return m ? m.innerText.trim() : '';
}"""

JS_MODEL_PICK = """(name) => {
  const it = [...document.querySelectorAll('[role=menuitem]')]
    .find(e => (e.innerText || '').trim() === name);
  if (!it) return 'NO_ITEM';
  it.click();
  return 'CLICKED';
}"""


def log(msg, verbose):
    if verbose:
        print(msg, file=sys.stderr, flush=True)


def js_obj(raw):
    """page.evaluate 有时返回已解析对象，有时是字符串，统一成 dict"""
    if isinstance(raw, dict):
        return raw
    try:
        v = json.loads(raw)
        return v if isinstance(v, dict) else {'value': v}
    except Exception:
        return {'value': raw}


def wait_login(page, verbose, timeout=180):
    """未登录时提示用户扫码，轮询直到编辑器可用"""
    t0 = time.time()
    told = False
    while time.time() - t0 < timeout:
        st = js_obj(page.evaluate(JS_LOGIN_STATE))
        if not st.get('login') and st.get('editor'):
            return True
        if not told:
            print('检测到豆包未登录。请在打开的浏览器窗口里扫码登录，登录后会自动继续……', flush=True)
            told = True
        time.sleep(2)
    return False


def set_model(page, want, verbose):
    cur = page.evaluate(JS_MODEL_CUR)
    if (cur or '').strip() == want:
        log(f'模型已是 {want}', verbose)
        return True
    # 打开下拉必须真实点击（JS click 无效）
    el = page.query_selector('[data-testid="chat_input_action_model"]')
    if not el:
        log('未找到模型按钮', verbose)
        return False
    box = el.bounding_box()
    if box:
        page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    else:
        el.click()
    time.sleep(1.3)
    res = page.evaluate(JS_MODEL_PICK, want)
    time.sleep(1.0)
    now = (page.evaluate(JS_MODEL_CUR) or '').strip()
    log(f'模型切换 {res} -> {now}', verbose)
    return now == want


def ask(question, model='专家', timeout=150, verbose=False, channel='msedge', headless=False):
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            channel=channel,
            headless=headless,
            viewport={'width': 1280, 'height': 900},
        )
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(CHAT_URL, wait_until='domcontentloaded')
            time.sleep(3)

            if not wait_login(page, verbose):
                print('ERROR: 等待登录超时，请在浏览器窗口完成登录后重试', file=sys.stderr)
                return None

            for _ in range(10):
                if page.evaluate(JS_READY):
                    break
                time.sleep(1)

            if model:
                set_model(page, model, verbose)

            base = js_obj(page.evaluate(JS_READ))
            log(f'基线消息数 {base.get("n")}', verbose)

            # 写入（判据看 innerHTML）
            r = js_obj(page.evaluate(JS_PASTE, question))
            if not r.get('ok'):
                time.sleep(1.0)
                r = js_obj(page.evaluate(JS_PASTE, question))
                if not r.get('ok'):
                    print(f'ERROR: 写入失败 {r}', file=sys.stderr)
                    return None
            log(f'已写入 {r}', verbose)
            time.sleep(0.8)

            s = page.evaluate(JS_SEND)
            if s != 'CLICKED':
                print(f'ERROR: 发送失败 {s}', file=sys.stderr)
                return None
            log('已发送，等待回答…', verbose)

            # 轮询：文本变化 + 连续两次稳定；排除自己的问题与旧文本
            base_last = (base.get('last') or '').strip()
            qkey = question.strip()[:12]
            last, stable, answer = '', 0, ''
            t0 = time.time()
            while time.time() - t0 < timeout:
                time.sleep(2.5)
                st = js_obj(page.evaluate(JS_READ))
                txt = (st.get('last') or '').strip()
                fresh = bool(txt) and txt != base_last and not txt.startswith(qkey)
                if fresh:
                    if txt == last:
                        stable += 1
                    else:
                        stable = 0
                    last, answer = txt, txt
                    if stable >= 2:
                        break
                else:
                    log(f'  [{int(time.time()-t0)}s] 等待中 n={st.get("n")}', verbose)
            return answer
        finally:
            ctx.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    ap.add_argument('--model', choices=['快速', '专家'], default='专家')
    ap.add_argument('--timeout', type=int, default=150)
    ap.add_argument('--channel', default='msedge', choices=['msedge', 'chrome', 'chromium'])
    ap.add_argument('--show', action='store_true', help='显示浏览器窗口（默认已显示）')
    ap.add_argument('--headless', action='store_true', help='无头模式（首次登录不要用）')
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args()

    ans = ask(a.question, a.model, a.timeout, a.verbose, a.channel, a.headless)
    if ans is None:
        print('ERROR: 调用失败（加 --verbose 看原因）')
        return 1
    print(ans)
    return 0


if __name__ == '__main__':
    sys.exit(main())
