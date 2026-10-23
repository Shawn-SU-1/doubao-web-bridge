# -*- coding: utf-8 -*-
"""doubao_ask.py —— 用你账号的额度驱动豆包网页版一问一答。

免责：非官方工具，与豆包/字节跳动无关联、未获授权；自动化访问可能违反《豆包用户协议》，
账号有被限流或封禁的风险，由使用者自行承担。仅可调用你自己已登录、已获授权的账号额度。
详见仓库根目录 DISCLAIMER.md。

用法：
  python doubao_ask.py "你的问题"              # 新开一个对话再问
  python doubao_ask.py "问题" --same           # 接着当前对话问（保留上下文）
  python doubao_ask.py "问题" --raw            # 只输出回答正文，便于程序/管道调用
  python doubao_ask.py "问题" --timeout 180

技术要点（踩过的坑，别改回去）：
1. 输入框是 tiptap/ProseMirror 富文本 + 一个重叠的 IME textarea。程序化写 value 或
   execCommand('insertText') 会被 IME 层截走 → 必须用 paste 事件直接派发给编辑器。
   实测 paste 事件是最稳的写入方式。
2. 发送按钮 class 含 'send-msg-btn'（有内容时）或 'bg-dbx-fill-highlight'（空态），
   位置在输入框右下角；只按 class 匹配会漏，配合坐标兜底。
3. 读答案用 [data-testid="message_text_content"]；发送前记下条数，发送后必须
   条数增加 >=2（用户消息 + 回答）才算拿到新回答，否则会读到上一条旧回复。
"""
import sys, os, json, time, subprocess, argparse

# SKILL_PATH_BASH 只在灵犀会话里有；在普通终端 / Codex 里跑没有这个变量，
# 回退到技能实际安装位置，否则脚本无法脱离灵犀独立使用。
SKILL_ROOT = os.environ.get('SKILL_PATH_BASH') or os.path.join(
    os.environ.get('APPDATA', ''), 'WPS 灵犀', 'serverdir', 'target_skills')
CLI = os.path.join(SKILL_ROOT, 'browser', 'scripts', 'cli.py')

def cli(*args, timeout=180):
    r = subprocess.run([sys.executable, CLI, *args],
                       capture_output=True, text=True, encoding='utf-8', errors='replace',
                       timeout=timeout)
    return r.returncode, (r.stdout or ''), (r.stderr or '')

def body(out):
    """取 CLI 输出 --- 之后的返回正文"""
    if '---' in out:
        parts = out.split('---')
        if len(parts) >= 2:
            return parts[-1].strip()
    return out.strip()

EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def browser_alive():
    """browser CLI 能否连上浏览器（插件模式：需要 Edge 已运行且插件在线）"""
    try:
        rc, out, err = cli('tabs_list', timeout=30)
    except Exception:
        return False
    return rc == 0 and 'Browser Pages' in out


def ensure_browser():
    """尽力保证浏览器可用。

    注意：browser CLI 自身只负责连接，不会启动浏览器（源码里无启动逻辑），
    所以 Edge 没开时必须由这边拉起。“能否连上”取决于插件是否随新进程就绪，
    做不到时返回 STARTED_NO_CONNECT，由调用方决定是否重试。
    """
    if browser_alive():
        return 'ALIVE'
    for exe in EDGE_PATHS:
        if os.path.exists(exe):
            try:
                subprocess.Popen([exe], close_fds=True)
            except Exception:
                return 'EDGE_START_FAIL'
            for _ in range(10):
                time.sleep(2)
                if browser_alive():
                    return 'STARTED'
            return 'STARTED_NO_CONNECT'
    return 'NO_EDGE'


def find_target():
    rc, out, err = cli('tabs_list')
    cur, blocks = None, []
    for line in out.splitlines():
        if '- Target ID:' in line and '`' in line:
            cur = line.split('`')[1]
        elif '- URL:' in line and cur:
            url = line.split('](')[-1].rstrip(')') if '](' in line else line
            blocks.append((cur, url)); cur = None
    for t, u in blocks:
        if 'doubao.com' in u:
            return t
    rc, out, err = cli('navigate', '--url', 'https://www.doubao.com/chat/')
    for line in out.splitlines():
        if line.strip().startswith('TargetId:'):
            return line.split(':', 1)[1].strip()
    return None

def js_str(s):
    return json.dumps(s, ensure_ascii=False)

def new_chat(target):
    """新对话：点侧栏入口无效（DIV 上接不到事件），改用导航到 /chat/ 根路径，
    实测能拿到干净会话（消息数归 0）。"""
    rc, out, err = cli('navigate', '--target-id', target, '--url', 'https://www.doubao.com/chat/')
    return 'NAV_OK' if rc == 0 else 'NAV_FAIL'

def count_and_last(target):
    js = """const t=[...document.querySelectorAll('[data-testid="message_text_content"]')];
return JSON.stringify({n:t.length,last:t.length?t[t.length-1].innerText:''});"""
    rc, out, err = cli('execute_script', '--target-id', target, '--script', js)
    raw = body(out)
    try:
        # 输出形如 {"n":6,"last":"..."} 或带引号转义的字符串
        if raw.startswith('"') and raw.endswith('"'):
            raw = json.loads(raw)
        return json.loads(raw)
    except Exception:
        return {'n': -1, 'last': ''}

def current_model(target):
    js = ("const m=document.querySelector('[data-testid=\"chat_input_action_model\"]');"
          "return m?(m.innerText||'').trim():'';")
    rc, out, err = cli('execute_script', '--target-id', target, '--script', js)
    return body(out).strip('"').strip()


def set_model(target, want):
    """切换模型（快速 / 专家）。
    打开菜单必须用真实鼠标点击（CDP），JS click 打不开这个下拉；
    菜单里的 menuitem 则用 JS click 即可。"""
    cur = current_model(target)
    if cur == want:
        return f'ALREADY:{cur}'
    rc, out, err = cli('get_interactive_elements', '--target-id', target)
    idx = None
    for line in out.splitlines():
        if '[:] button |' in line and ('快速' in line or '专家' in line):
            try:
                idx = int(line.split('[:]')[0].strip())
            except Exception:
                continue
    if idx is None:
        return 'NO_MODEL_BTN'
    cli('click', '--target-id', target, '--element-index', str(idx))
    time.sleep(1.3)
    js = ("const it=[...document.querySelectorAll('[role=menuitem]')]"
          ".find(e=>(e.innerText||'').trim()===W);"
          "if(!it)return 'NO_ITEM';it.click();return 'CLICKED';")
    js = js.replace('W', json.dumps(want, ensure_ascii=False))
    rc, out, err = cli('execute_script', '--target-id', target, '--script', js)
    res = body(out)
    time.sleep(1.2)
    return f'{res} -> {current_model(target)}'


def pm_text(target):
    js = "const pm=document.querySelector('.tiptap.ProseMirror');return pm?pm.innerText:'';"
    rc, out, err = cli('execute_script', '--target-id', target, '--script', js)
    return body(out).strip('"')


def click_input(target):
    """真实鼠标点击输入框。必须做：点击后那层 IME textarea 会消失，
    之后 paste 写入才能稳定生效（不点击时 paste 会被吞掉）。"""
    rc, out, err = cli('get_interactive_elements', '--target-id', target)
    idx = None
    for line in out.splitlines():
        if 'textarea' in line and '[k]' not in line and '[:]' in line:
            try:
                idx = int(line.split('[:]')[0].strip())
            except Exception:
                continue
    if idx is None:
        return 'NO_TA'
    rc, out, err = cli('click', '--target-id', target, '--element-index', str(idx))
    return 'CLICKED' if rc == 0 else 'CLICK_FAIL'


def clear_input(target):
    """清空必须在独立一次调用里做：execCommand(delete) 后同批的 paste 会被 ProseMirror 忽略，
    分两次调用则正常。"""
    js = ("const pm=document.querySelector('.tiptap.ProseMirror');if(!pm)return 'NO_PM';"
          "pm.focus();document.execCommand('selectAll',false,null);"
          "document.execCommand('delete',false,null);return 'CLEARED';")
    rc, out, err = cli('execute_script', '--target-id', target, '--script', js)
    return body(out)


def fill_question(target, question):
    # 判据看 innerHTML：paste 后 innerText 在未渲染时会读到空，innerHTML 则立即更新。
    js = """const pm=document.querySelector('.tiptap.ProseMirror');
if(!pm) return 'NO_PM';
const q=Q;
pm.focus();
const dt=new DataTransfer();
dt.setData('text/plain',q);
pm.dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true}));
return JSON.stringify({has:pm.innerHTML.indexOf(q.slice(0,6))>=0,html:pm.innerHTML.slice(0,70)});""".replace('Q', js_str(question))
    rc, out, err = cli('execute_script', '--target-id', target, '--script', js)
    return body(out)

def click_send(target):
    js = """const bs=[...document.querySelectorAll('button')].filter(b=>{
  const c=(b.className||'').toString(); const r=b.getBoundingClientRect();
  return r.width>0 && (c.includes('send-msg-btn') || c.includes('bg-dbx-fill-highlight'));
});
if(!bs.length) return 'NO_SEND';
bs[bs.length-1].click(); return 'CLICKED';"""
    rc, out, err = cli('execute_script', '--target-id', target, '--script', js)
    return body(out)

def ask(question, timeout=150, raw=False, same=False, model=None):
    br = ensure_browser()
    if br in ('NO_EDGE', 'EDGE_START_FAIL', 'STARTED_NO_CONNECT'):
        print(f'ERROR: 浏览器不可用（{br}）', file=sys.stderr); return None

    target = find_target()
    if not target:
        print('ERROR: 找不到豆包页面', file=sys.stderr); return None
    if not raw:
        print(f'[豆包] 页面 {target}', file=sys.stderr)

    if not same:
        r = new_chat(target)
        if not raw:
            print(f'[豆包] 新对话: {r}', file=sys.stderr)
        time.sleep(3.5)

    if model:
        mr = set_model(target, model)
        if not raw:
            print(f'[豆包] 模型: {mr}', file=sys.stderr)

    base = count_and_last(target)
    if not raw:
        print(f'[豆包] 现有消息 {base["n"]} 条', file=sys.stderr)

    # 写入三步，顺序不可换：
    # ① 若残留内容，先单独一次调用清空（清空和 paste 不能同批）
    # ② paste 事件写入问题
    # ③ 校验；仍为空则 click 输入框再写一次（click 会让 IME textarea 消失）
    cur = pm_text(target)
    if cur.strip():
        clear_input(target)
        time.sleep(0.8)

    # 判据必须用 paste 同批读到的 len：跨调用再读 innerText 会因渲染滞后误判为空，
    # 从而导致重复写入（曾出现问题文本被写两遍）。
    fr = fill_question(target, question)
    ok = ('NO_PM' not in fr) and ('"has":true' in fr.replace(' ', ''))

    if not ok:
        ci = click_input(target)
        time.sleep(1.0)
        fr = fill_question(target, question)
        ok = ('NO_PM' not in fr) and ('"has":true' in fr.replace(' ', ''))
        if not raw:
            print(f'[豆包] 二次写入 {fr} / {ci}', file=sys.stderr)
    if not ok:
        print(f'ERROR: 写入失败，编辑器为空 {fr}', file=sys.stderr); return None
    if not raw:
        print(f'[豆包] 已写入 {fr}', file=sys.stderr)
    time.sleep(0.6)

    cr = click_send(target)
    if 'NO_SEND' in cr:
        print('ERROR: 未找到发送按钮', file=sys.stderr); return None
    if not raw:
        print('[豆包] 已发送，等待回答...', file=sys.stderr)

    # 判定不依赖消息条数（条数会因页面清理/新对话与否而变化），改为文本比对：
    # 出现一条「不是自己的问题、也不是发送前那条旧文本」的新文本，且连续 2 次不变，即为新回答
    base_last = (base.get('last') or '').strip()
    qkey = question.strip()[:12]
    last, stable, answer = '', 0, ''
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(2.5)
        st = count_and_last(target)
        txt = (st.get('last') or '').strip()
        fresh = bool(txt) and txt != base_last and not txt.startswith(qkey)
        if fresh:
            if txt == last:
                stable += 1
            else:
                stable = 0
            last = txt
            answer = txt
            if stable >= 2:
                break
        else:
            if not raw:
                print(f'  [{int(time.time()-t0)}s] 等待中 n={st.get("n")}', file=sys.stderr)
    return answer

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    ap.add_argument('--timeout', type=int, default=150)
    ap.add_argument('--raw', action='store_true')
    ap.add_argument('--same', action='store_true')
    ap.add_argument('--model', choices=['快速', '专家'], default='专家',
                    help='模型：默认专家（更强，更耗额度）；传 快速 可省额度')
    ap.add_argument('--verbose', action='store_true',
                    help='输出进度日志到 stderr（默认静默，stdout 只有答案）')
    a = ap.parse_args()
    # 静默模式：把所有进度日志丢去 /dev/null，stdout 只留答案。
    # 这样调用方的上下文里只有「命令 + 答案」，不会被日志和诊断细节淹没。
    if not a.verbose:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')

    ans = ask(a.question, a.timeout, a.raw, a.same, a.model)
    if ans is None:
        # 失败时把提示写到 stdout，否则静默下调用方什么也看不到
        print('ERROR: 豆包调用失败（加 --verbose 看具体原因）')
        return 1
    print(ans)
    return 0

if __name__ == '__main__':
    sys.exit(main())