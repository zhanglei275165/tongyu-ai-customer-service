/*
 * 同宇 AI 客服 · 可嵌入挂件
 * ------------------------------------------------------------
 * 把下面这段 <script> 贴到你网站任意页面的 </body> 前即可：
 *
 *   <script src="http://你的客服服务器:8787/embed.js"
 *           data-server="http://你的客服服务器:8787"
 *           data-title="在线客服" data-lang="zh" async></script>
 *
 * 也可以不引外部脚本，直接把本文件内容内联进页面（更省一次请求）。
 * 它会自动在右下角渲染一个聊天气泡，访客点开即可对话， multilingual 自动跟随。
 */
(function () {
  var s = document.currentScript;
  var SERVER = (s && s.dataset.server) || (location.protocol + '//' + location.host);
  var TITLE = (s && s.dataset.title) || '在线客服';
  var LANG = (s && s.dataset.lang) || (navigator.language || 'zh').slice(0, 2);

  var css = `
  #ty-cs-wrap{position:fixed;right:20px;bottom:20px;z-index:2147483000;font-family:system-ui,'PingFang SC','Microsoft YaHei',sans-serif}
  #ty-cs-bubble{width:56px;height:56px;border-radius:50%;background:#c41e1e;color:#fff;border:none;cursor:pointer;font-size:24px;box-shadow:0 4px 14px rgba(0,0,0,.25)}
  #ty-cs-panel{display:none;position:absolute;right:0;bottom:68px;width:340px;height:480px;background:#fff;border-radius:14px;box-shadow:0 10px 40px rgba(0,0,0,.25);overflow:hidden;flex-direction:column}
  #ty-cs-panel.open{display:flex}
  #ty-cs-head{background:#c41e1e;color:#fff;padding:12px 14px;font-weight:600;display:flex;justify-content:space-between;align-items:center}
  #ty-cs-head button{background:none;border:none;color:#fff;font-size:18px;cursor:pointer}
  #ty-cs-msgs{flex:1;overflow-y:auto;padding:12px;background:#f6f6f6}
  #ty-cs-msgs div{margin:8px 0;max-width:80%;padding:8px 11px;border-radius:10px;line-height:1.5;white-space:pre-wrap;word-break:break-word}
  .ty-u{background:#e6f0ff;margin-left:auto}
  .ty-a{background:#fff;border:1px solid #eee}
  #ty-cs-input{display:flex;border-top:1px solid #eee}
  #ty-cs-input textarea{flex:1;border:none;resize:none;padding:10px;height:44px;font:inherit;outline:none}
  #ty-cs-input button{background:#c41e1e;color:#fff;border:none;padding:0 16px;cursor:pointer}
  `;
  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  var wrap = document.createElement('div');
  wrap.id = 'ty-cs-wrap';
  wrap.innerHTML = `
    <div id="ty-cs-panel">
      <div id="ty-cs-head"><span>${TITLE}</span><button id="ty-cs-close">×</button></div>
      <div id="ty-cs-msgs"><div class="ty-a">您好，我是 AI 客服，有什么可以帮您？</div></div>
      <div id="ty-cs-input">
        <textarea id="ty-cs-text" placeholder="输入您的问题…"></textarea>
        <button id="ty-cs-send">发送</button>
      </div>
    </div>
    <button id="ty-cs-bubble">💬</button>`;
  document.body.appendChild(wrap);

  var panel = wrap.querySelector('#ty-cs-panel');
  var msgs = wrap.querySelector('#ty-cs-msgs');
  var text = wrap.querySelector('#ty-cs-text');

  wrap.querySelector('#ty-cs-bubble').onclick = function () { panel.classList.toggle('open'); };
  wrap.querySelector('#ty-cs-close').onclick = function () { panel.classList.remove('open'); };

  function addMsg(role, content) {
    var d = document.createElement('div');
    d.className = role === 'user' ? 'ty-u' : 'ty-a';
    d.textContent = content;
    msgs.appendChild(d);
    msgs.scrollTop = msgs.scrollHeight;
    return d;
  }

  function send() {
    var q = text.value.trim();
    if (!q) return;
    text.value = '';
    addMsg('user', q);
    var ack = addMsg('ai', '…');
    var buf = '';
    var es = new EventSource(SERVER + '/api/chat?m=' + encodeURIComponent(q) + '&lang=' + LANG);
    es.onmessage = function (ev) {
      if (ev.data === '[DONE]') { es.close(); return; }
      try {
        var p = JSON.parse(ev.data);
        var c = (p.message && p.message.content) || '';
        buf += c;
        ack.textContent = buf || '…';
        msgs.scrollTop = msgs.scrollHeight;
      } catch (e) {}
    };
    es.onerror = function () { es.close(); if (!buf) ack.textContent = '（连接失败，请稍后再试）'; };
  }

  wrap.querySelector('#ty-cs-send').onclick = send;
  text.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });
})();
