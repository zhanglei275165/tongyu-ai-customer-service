# -*- coding: utf-8 -*-
"""
同宇 AI 客服 (Tongyu AI Customer Service)
==========================================
一个**通用、独立、零依赖**的网站 AI 客服后端。任何人都可以在自己的网站上套用：

  · 配置驱动：改 config.json 即可换成你自己的公司/产品/语言/提示词，不碰代码。
  · 多语言：根据用户语言自动切中/英/俄系统提示词（可在配置里增删任意语言）。
  · 流式对话：SSE 逐字返回，前端开箱即用（自带一个可嵌入的聊天挂件）。
  · 留资捕获：访客留的联系方式自动存到 leads.jsonl，方便跟进。
  · 可选 RAG：在 knowledge/ 放 .md 资料，客服回答优先引用你的资料、不瞎编。
  · 大脑可换：默认对接本地「同宇引擎」(仿 Ollama, 11434)，也能一行配置换成
    OpenAI / 通义 / SiliconFlow 等任意 OpenAI 兼容 /api/chat 端点。
  · 纯标准库：python server.py 即可运行，无需 pip 安装任何东西。

启动：
    python server.py
默认端口 8787 -> http://127.0.0.1:8787
浏览器打开即可看到带聊天挂件的演示站；把 widget/embed.js 那段 <script> 贴到
你自己的网页里，就能让任意网站直接用这个客服。

许可证：MIT（你可基于它做闭源商业产品，也可上架应用商店）。
"""
import os
import re
import json
import time
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")
KNOWLEDGE_DIR = os.path.join(HERE, "knowledge")
LEADS_PATH = os.path.join(HERE, "leads.jsonl")
PORT = int(os.environ.get("PORT", "8787"))

# ---------------- 配置 ----------------
def load_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # 没有 config.json 也能跑（用内置默认），但建议复制 config.example.json
        return {}

CONFIG = load_config()

# 大脑端点：默认本地同宇引擎（仿 Ollama），可改成任意 OpenAI 兼容 /api/chat
# 注意：同宇引擎暴露的是 /api/generate；官方 Ollama 与 OpenAI 兼容端点用 /api/chat 或 /v1/chat/completions。
# 这里默认指向 /api/generate，开箱即可对接同宇引擎（也兼容官方 Ollama 的 /api/generate）。
CHAT_URL = os.environ.get("CHAT_URL") or CONFIG.get(
    "chat_url", "http://127.0.0.1:11434/api/generate")
# 自动判断走哪种协议：URL 里含 /chat 就用 OpenAI 兼容的 /api/chat（含 /v1/chat/completions）；
# 否则走同宇引擎/官方 Ollama 的 /api/generate（流式 NDJSON）。
USE_CHAT_API = bool(re.search(r"/chat", CHAT_URL))
MODEL = CONFIG.get("model", "qwen2.5-coder:3b")
CONTACT_EMAIL = CONFIG.get("contact_email", "")
CONTACT_WA = CONFIG.get("contact_whatsapp", "")
SITE_NAME = CONFIG.get("site_name", "我的网站")

# 多语言系统提示词模板：{ctx}=检索到的资料, {email}=联系邮箱, {wa}=WhatsApp
SYSTEM_PROMPTS = CONFIG.get("system_prompts") or {
    "zh": (
        "你是「{site}」的 AI 客服助手，用简体中文回答。\n"
        "你的职责：帮助访客了解产品、答疑、收集意向。\n"
        "1) 先弄清楚访客的需求与关键参数，再给方向，不要一上来就报一长串问题。\n"
        "2) 公司专属事实（具体型号/价格/案例/交货期/地址）只能依据下方【资料】；"
        "资料没有就直说『以实际确认为准』，并引导留姓名·公司·电话/邮箱·需求。\n"
        "3) 语气专业、务实、简短；不确定参数不编造。\n"
        "4) 鼓励留资：姓名、公司、电话/邮箱、需求。\n"
        "【资料】\n{ctx}"
    ),
    "en": (
        "You are the AI customer-service assistant for '{site}'. Reply in English.\n"
        "Your job: help visitors learn about the products, answer questions, capture intent.\n"
        "1) First understand the visitor's need and key parameters, then give direction; "
        "don't fire a long list of questions upfront.\n"
        "2) Company-specific facts (exact models / prices / cases / lead time / address) "
        "must come ONLY from [SOURCE] below. If absent, say 'subject to confirmation' and "
        "ask for name, company, phone/email, requirement.\n"
        "3) Professional, practical, concise. Don't invent specs.\n"
        "4) Encourage leads: name, company, phone/email, requirement.\n"
        "[SOURCE]\n{ctx}"
    ),
    "ru": (
        "Вы — ИИ-ассистент по обслуживанию клиентов «{site}». Отвечайте на русском.\n"
        "Ваша задача: помогать посетителям узнавать о продуктах, отвечать на вопросы, "
        "собирать заявки.\n"
        "1) Сначала выясните потребность и ключевые параметры, затем дайте направление; "
        "не задавайте сразу длинный список вопросов.\n"
        "2) Факты о компании (модели / цены / кейсы / сроки / адрес) — только из "
        "[ИСТОЧНИК] ниже. Если нет — скажите «уточняется» и попросите имя, компанию, "
        "телефон/email, задачу.\n"
        "3) Профессионально, практично, кратко. Не выдумывайте.\n"
        "4) Поощряйте контакты: имя, компания, телефон/email, задача.\n"
        "[ИСТОЧНИК]\n{ctx}"
    ),
}
LANG_PRIORITY = CONFIG.get("lang_priority", ["zh", "en", "ru"])
FALLBACK_LANG = LANG_PRIORITY[0]


# ---------------- 极简 RAG（纯 Python，无依赖） ----------------
KB_LOCK = threading.Lock()
KB_CACHE = []          # [(text, lang)]
KB_MTIME = 0

def reload_kb_if_needed():
    global KB_MTIME
    mtime = 0
    if os.path.isdir(KNOWLEDGE_DIR):
        for fn in os.listdir(KNOWLEDGE_DIR):
            if fn.endswith(".md"):
                mtime = max(mtime, os.path.getmtime(os.path.join(KNOWLEDGE_DIR, fn)))
    with KB_LOCK:
        if not KB_CACHE or mtime > KB_MTIME:
            docs = []
            for fn in os.listdir(KNOWLEDGE_DIR) if os.path.isdir(KNOWLEDGE_DIR) else []:
                if not fn.endswith(".md"):
                    continue
                try:
                    t = open(os.path.join(KNOWLEDGE_DIR, fn), encoding="utf-8").read()
                except Exception:
                    continue
                lang = "zh"
                if re.search(r"[A-Za-z]{20,}", t) and not re.search(r"[\u4e00-\u9fff]", t[:200]):
                    lang = "en"
                # 按段落切块
                for chunk in re.split(r"\n{1,}", t):
                    chunk = chunk.strip()
                    if len(chunk) > 20:
                        docs.append((chunk, lang))
            KB_CACHE[:] = docs
            KB_MTIME = mtime

def detect_lang(text):
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    if re.search(r"[а-яА-Я]{3,}", text):
        return "ru"
    return "en"

def retrieve(query, lang, top_k=3):
    reload_kb_if_needed()
    if not KB_CACHE:
        return []
    q = set(re.findall(r"[\w\u4e00-\u9fff]+", query.lower()))
    scored = []
    for text, dlang in KB_CACHE:
        if dlang != lang:
            continue
        d = set(re.findall(r"[\w\u4e00-\u9fff]+", text.lower()))
        overlap = len(q & d)
        if overlap:
            scored.append((overlap, text))
    scored.sort(key=lambda x: -x[0])
    return [t for _, t in scored[:top_k]]


# ---------------- 调用大脑 ----------------
def _stream_generate(model, prompt, sys_prompt):
    """同宇引擎 / Ollama 的 /api/generate 是流式的：每行一个 JSON {response:...}。"""
    body = json.dumps({
        "model": model,
        "prompt": (sys_prompt + "\n\n" + prompt) if sys_prompt else prompt,
        "stream": True,
        "options": {"temperature": 0.7, "top_p": 0.9, "repeat_penalty": 1.1,
                    "num_predict": 600},
    }).encode("utf-8")
    req = urllib.request.Request(CHAT_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        for raw in r:
            line = raw.decode("utf-8").strip()
            if not line:
                continue
            try:
                ch = json.loads(line)
            except Exception:
                continue
            piece = ch.get("response")
            if piece:
                yield piece

def _stream_chat(model, prompt, sys_prompt):
    """OpenAI 兼容 /api/chat：流式 SSE，每行 data: {choices:[{delta:{content}}]}。"""
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt},
        ],
        "stream": True,
        "temperature": 0.7,
    }).encode("utf-8")
    req = urllib.request.Request(CHAT_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        for raw in r:
            line = raw.decode("utf-8").strip()
            if not line or not line.startswith("data:"):
                continue
            payload = line[len("data:"):].strip()
            if payload == "[DONE]":
                break
            try:
                ch = json.loads(payload)
            except Exception:
                continue
            piece = ch.get("choices", [{}])[0].get("delta", {}).get("content")
            if piece:
                yield piece

def chat_stream(prompt, lang):
    sys_prompt = SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS[FALLBACK_LANG]).format(
        site=SITE_NAME,
        ctx="\n\n".join(retrieve(prompt, lang)) or "（暂无内部资料，凭通用知识回答）",
        email=CONTACT_EMAIL, wa=CONTACT_WA)
    if USE_CHAT_API:
        return _stream_chat(MODEL, prompt, sys_prompt)
    return _stream_generate(MODEL, prompt, sys_prompt)


# ---------------- 留资 ----------------
def save_lead(rec):
    rec["_ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        os.makedirs(os.path.dirname(LEADS_PATH), exist_ok=True)
        with open(LEADS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ---------------- HTTP 服务 ----------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        p = self.path.split("?")[0].rstrip("/") or "/"
        if p in ("/", "/index.html"):
            self._serve_file(os.path.join(HERE, "widget", "demo.html"), "text/html; charset=utf-8")
        elif p == "/embed.js":
            self._serve_file(os.path.join(HERE, "widget", "embed.js"),
                             "application/javascript; charset=utf-8")
        elif p == "/health":
            self._json({"status": "ok", "model": MODEL, "chat_url": CHAT_URL,
                        "site": SITE_NAME, "kb_docs": len(KB_CACHE)})
        elif p == "/api/chat":
            # 供浏览器 EventSource 使用（SSE 仅支持 GET）
            qs = {}
            try:
                from urllib.parse import parse_qs
                qs = parse_qs(self.path.split("?", 1)[1])
            except Exception:
                pass
            message = (qs.get("m", [""])[0] or "").strip()
            lang = qs.get("lang", [""])[0] or detect_lang(message) or FALLBACK_LANG
            if not message:
                self._json({"reply": "（请输入您的需求）"})
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self._cors()
            self.end_headers()
            try:
                full = []
                for piece in chat_stream(message, lang):
                    full.append(piece)
                    self.wfile.write(
                        ("data: " + json.dumps({"message": {"content": piece}},
                                              ensure_ascii=False) + "\n\n").encode("utf-8"))
                    self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")
                if re.search(r"\d{6,}|@|\b微信\b|whatsapp", message, re.I):
                    save_lead({"need": message[:200], "lang": lang, "auto": True})
            except Exception as e:
                self.wfile.write(
                    ("data: " + json.dumps({"message": {"content": "（AI 暂时连不上：%s）" % e}},
                                          ensure_ascii=False) + "\n\n").encode("utf-8"))
                self.wfile.write(b"data: [DONE]\n\n")
        else:
            self.send_response(404)
            self._cors()
            self.end_headers()

    def do_POST(self):
        p = self.path.split("?")[0].rstrip("/")
        if p == "/api/chat":
            self._post_chat()
        elif p == "/api/lead":
            self._post_lead()
        else:
            self.send_response(404)
            self._cors()
            self.end_headers()

    # ---- 实现 ----
    def _serve_file(self, path, ctype):
        if not os.path.isfile(path):
            self.send_response(404)
            self._cors()
            self.end_headers()
            return
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def _post_chat(self):
        body = self._read_json()
        message = (body.get("message") or "").strip()
        lang = body.get("lang") or detect_lang(message)
        if lang not in SYSTEM_PROMPTS:
            lang = FALLBACK_LANG
        if not message:
            self._json({"reply": "（请输入您的需求）"})
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self._cors()
        self.end_headers()
        try:
            full = []
            for piece in chat_stream(message, lang):
                full.append(piece)
                self.wfile.write(
                    ("data: " + json.dumps({"message": {"content": piece}},
                                          ensure_ascii=False) + "\n\n").encode("utf-8"))
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            # 自动留资：消息里出现电话/邮箱/微信等则记录
            if re.search(r"\d{6,}|@|\b微信\b|whatsapp", message, re.I):
                save_lead({"need": message[:200], "lang": lang, "auto": True})
        except (ConnectionAbortedError, BrokenPipeError, OSError):
            # 客户端中途断开连接（关浏览器/curl 中断）属正常，静默退出，不刷 traceback
            return
        except Exception as e:
            try:
                self.wfile.write(
                    ("data: " + json.dumps({"message": {"content": "（AI 暂时连不上：%s）" % e}},
                                          ensure_ascii=False) + "\n\n").encode("utf-8"))
                self.wfile.write(b"data: [DONE]\n\n")
            except (ConnectionAbortedError, BrokenPipeError, OSError):
                pass

    def _post_lead(self):
        rec = self._read_json()
        save_lead(rec)
        self._json({"code": 0})


def main():
    reload_kb_if_needed()
    print("同宇 AI 客服 -> http://127.0.0.1:%d" % PORT)
    print("  站点: %s | 大脑: %s | 模型: %s" % (SITE_NAME, CHAT_URL, MODEL))
    print("  知识库文档数: %d | 支持语言: %s" % (len(KB_CACHE), ", ".join(SYSTEM_PROMPTS)))
    print("  把 widget/embed.js 的 <script> 贴到你网站即可接入。")
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    srv.serve_forever()


if __name__ == "__main__":
    main()
