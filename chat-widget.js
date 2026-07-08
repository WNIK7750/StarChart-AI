/**
 * chat-widget.js — AI 助手浮窗
 * SSE 流式 + 双模型路由 + 智能模式开关 + 快捷提问 + 多轮记忆 + 断线重连
 */
;(function () {
  "use strict";

  // ========== 配置 ==========
  const API_BASE = "";
  const STREAM_ENDPOINT = "/chat/stream";
  const HISTORY_KEY = "cw_history";
  const MAX_HISTORY = 20;
  const MAX_RETRIES = 2;
  const RETRY_DELAY = [1000, 2500];

  // ========== 快捷问题 ==========
  const DEFAULT_QUESTIONS = [
    "最近有什么新出的AI工具？",
    "推荐几个免费的代码补全工具",
    "帮我推荐图片生成工具",
    "有没有好用的AI写作助手？",
    "免费的视频生成工具有哪些？",
  ];

  const PREDICTION_RULES = [
    { keywords: ["代码","编程","开发","写代码"], questions: ["有免费的吗？","对比一下这几个工具","哪个更适合新手？"] },
    { keywords: ["图片","绘画","图像","画图","生成图"], questions: ["哪个生成质量最高？","有完全免费的吗？","手机端能用吗？"] },
    { keywords: ["视频","动画"], questions: ["免费的推荐一下","哪个操作最简单？","生成速度快的是哪个？"] },
    { keywords: ["写作","文案","文字","文章"], questions: ["支持中文吗？","和专业写手比怎么样？","有免费方案吗？"] },
    { keywords: ["聊天","对话","助手"], questions: ["和ChatGPT比哪个好？","有开源替代吗？","哪个有免费额度？"] },
    { keywords: ["音频","音乐","语音"], questions: ["免费的有哪些？","哪个音质最好？","支持中文配音吗？"] },
    { keywords: ["搜索","检索","查找"], questions: ["免费的推荐","和百度搜索区别？","能搜学术论文吗？"] },
    { keywords: ["免费","开源","不要钱","便宜"], questions: ["除了这个还有哪些免费的？","开源里哪个社区最活跃？","免费版有限制吗？"] },
    { keywords: ["对比","比较","区别"], questions: ["哪个性价比最高？","新手推荐哪个？","它们各有什么优缺点？"] },
  ];

  // ========== 状态 ==========
  let isOpen = false;
  let isLoading = false;
  let history = [];
  let currentMode = loadMode();

  // ========== 历史持久化 ==========
  function loadHistory() {
    try {
      const raw = localStorage.getItem(HISTORY_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
  }
  function saveHistory() {
    try {
      const trimmed = history.slice(-MAX_HISTORY);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(trimmed));
    } catch (e) { /* quota exceeded, silently skip */ }
  }
  function clearHistory() {
    history = [];
    try { localStorage.removeItem(HISTORY_KEY); } catch (e) {}
    const box = document.getElementById("cwMessages");
    box.innerHTML = "";
    renderWelcome();
    renderQuickQuestions(DEFAULT_QUESTIONS);
  }

  // ========== 模式持久化 ==========
  function loadMode() {
    try { return localStorage.getItem("cw_mode") || "auto"; } catch(e) { return "auto"; }
  }
  function saveMode(m) {
    currentMode = m;
    try { localStorage.setItem("cw_mode", m); } catch(e) {}
  }

  // ========== 获取页面主题 ==========
  function getPageTheme() {
    const html = document.documentElement;
    return html.getAttribute("data-theme") || "light";
  }

  // ========== 注入 HTML ==========
  function injectDOM() {
    if (document.getElementById("chatWidget")) return;

    const checked = currentMode === "reasoning" ? " checked" : "";
    const toggleLabel = currentMode === "reasoning" ? "推理" : "智能";
    const theme = getPageTheme();
    const headerBg = theme === "geek" ? "linear-gradient(135deg, #2d6a4f, #40916c)" : "linear-gradient(135deg, #6366f1, #8b5cf6)";

    const container = document.createElement("div");
    container.id = "chatWidget";
    container.innerHTML =
      '<button class="cw-trigger" id="cwTrigger" title="AI 助手">' +
        '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
          '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>' +
        '</svg>' +
      '</button>' +
      '<aside class="cw-panel" id="cwPanel">' +
        '<div class="cw-header">' +
          '<label class="cw-mode-toggle" id="cwModeToggle" title="切换智能/推理模式">' +
            '<input type="checkbox" id="cwModeCheckbox"' + checked + '>' +
            '<span class="cw-toggle-track"><span class="cw-toggle-thumb"></span></span>' +
            '<span class="cw-toggle-label" id="cwToggleLabel">' + toggleLabel + '</span>' +
          '</label>' +
          '<span class="cw-title">AI 助手</span>' +
          '<div style="display:flex;align-items:center;gap:8px">' +
            '<button class="cw-clear" id="cwClear" title="清空对话" style="background:none;border:none;color:rgba(255,255,255,0.7);font-size:12px;cursor:pointer;padding:0 4px;">清空</button>' +
            '<button class="cw-close" id="cwClose" title="关闭">&times;</button>' +
          '</div>' +
        '</div>' +
        '<div class="cw-messages" id="cwMessages"></div>' +
        '<div class="cw-quick-questions" id="cwQuickQuestions">' +
          '<div class="cq-scroll" id="cqScroll"></div>' +
        '</div>' +
        '<div class="cw-input-wrap">' +
          '<textarea class="cw-input" id="cwInput" rows="1" placeholder="输入你的问题..."></textarea>' +
          '<button class="cw-send" id="cwSend" title="发送">' +
            '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>' +
          '</button>' +
        '</div>' +
      '</aside>';

    document.body.appendChild(container);
  }

  // ========== 快捷问题 ==========
  function renderQuickQuestions(questions) {
    const scroll = document.getElementById("cqScroll");
    if (!scroll) return;
    scroll.innerHTML = "";
    questions.slice(0, 9).forEach(function(q) {
      var btn = document.createElement("button");
      btn.className = "cq-btn";
      btn.textContent = q;
      btn.addEventListener("click", function() {
        document.getElementById("cwInput").value = q;
        sendMessage();
      });
      scroll.appendChild(btn);
    });
    var wrap = document.getElementById("cwQuickQuestions");
    wrap.style.display = questions.length ? "block" : "none";
  }

  function predictQuestions(userMessage) {
    var msg = userMessage.toLowerCase();
    var candidates = new Set();
    for (var i = 0; i < PREDICTION_RULES.length; i++) {
      var rule = PREDICTION_RULES[i];
      for (var j = 0; j < rule.keywords.length; j++) {
        if (msg.indexOf(rule.keywords[j]) !== -1) {
          rule.questions.forEach(function(q) { candidates.add(q); });
          break;
        }
      }
    }
    var result = Array.from(candidates).slice(0, 9);
    return result.length ? result : DEFAULT_QUESTIONS;
  }

  // ========== 欢迎消息 ==========
  function renderWelcome() {
    var box = document.getElementById("cwMessages");
    var wrapper = document.createElement("div");
    wrapper.className = "cw-msg cw-msg-bot";
    var span = document.createElement("span");
    span.textContent = "你好！我是 AI 导航助手，可以帮你查找和推荐 AI 工具。试试问我\"有什么免费的代码补全工具？\"";
    wrapper.appendChild(span);
    box.appendChild(wrapper);
  }

  // ========== 恢复历史 ==========
  function restoreHistory() {
    var saved = loadHistory();
    if (!saved.length) {
      renderWelcome();
      return;
    }
    var box = document.getElementById("cwMessages");
    box.innerHTML = "";
    saved.forEach(function(msg) {
      var wrapper = document.createElement("div");
      wrapper.className = "cw-msg cw-msg-" + msg.role;
      var span = document.createElement("span");
      if (msg.role === "user") {
        span.textContent = msg.content;
      } else {
        span.innerHTML = renderMd(msg.content);
      }
      wrapper.appendChild(span);
      box.appendChild(wrapper);
    });
    history = saved;
    scrollToBottom(box);
  }

  // ========== 面板开关 ==========
  function toggle() {
    var panel = document.getElementById("cwPanel");
    isOpen = !isOpen;
    panel.classList.toggle("cw-open", isOpen);
    document.getElementById("cwTrigger").classList.toggle("cw-active", isOpen);
    if (isOpen) {
      document.getElementById("cwInput").focus();
      if (history.length === 0) renderQuickQuestions(DEFAULT_QUESTIONS);
    }
  }

  // ========== 模式切换 ==========
  function onModeChange() {
    var cb = document.getElementById("cwModeCheckbox");
    var label = document.getElementById("cwToggleLabel");
    var newMode = cb.checked ? "reasoning" : "auto";
    saveMode(newMode);
    label.textContent = newMode === "reasoning" ? "推理" : "智能";
  }

  // ========== 消息渲染 ==========
  function appendMessage(content, role) {
    var box = document.getElementById("cwMessages");
    var wrapper = document.createElement("div");
    wrapper.className = "cw-msg cw-msg-" + role;
    var span = document.createElement("span");
    span.textContent = content || "";
    wrapper.appendChild(span);
    box.appendChild(wrapper);
    scrollToBottom(box);
    return span;
  }

  function appendBotMessage() {
    var box = document.getElementById("cwMessages");
    var wrapper = document.createElement("div");
    wrapper.className = "cw-msg cw-msg-bot";
    var modelTag = document.createElement("div");
    modelTag.className = "cw-model-tag";
    wrapper.appendChild(modelTag);
    var contentSpan = document.createElement("span");
    wrapper.appendChild(contentSpan);
    box.appendChild(wrapper);
    scrollToBottom(box);
    return { wrapper: wrapper, contentSpan: contentSpan, modelTag: modelTag };
  }

  function appendErrorMessage(msg) {
    var box = document.getElementById("cwMessages");
    var wrapper = document.createElement("div");
    wrapper.className = "cw-msg cw-msg-bot cw-msg-error";
    var span = document.createElement("span");
    span.innerHTML = msg;
    wrapper.appendChild(span);
    box.appendChild(wrapper);
    scrollToBottom(box);
  }

  // ========== 轻量 Markdown 渲染 ==========
  function renderMd(text) {
    if (!text) return "";
    var html = text
      // 转义 HTML 特殊字符（先处理，防止 XSS）
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      // 代码块 ``` ... ```
      .replace(/```[\s\S]*?```/g, function(m) {
        return '<pre style="background:rgba(128,128,128,0.15);padding:8px 10px;border-radius:6px;font-size:12px;overflow-x:auto;margin:6px 0;">' + m.slice(3, -3).trim() + '</pre>';
      })
      // 行内代码 `...`
      .replace(/`([^`]+)`/g, '<code style="background:rgba(128,128,128,0.2);padding:1px 5px;border-radius:3px;font-size:12px;">$1</code>')
      // 标题 ### / ##
      .replace(/^### (.+)$/gm, '<strong style="font-size:14px;display:block;margin:10px 0 4px;">$1</strong>')
      .replace(/^## (.+)$/gm, '<strong style="font-size:15px;display:block;margin:12px 0 4px;">$1</strong>')
      // 加粗 **text**
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      // 分隔线 ---
      .replace(/^---$/gm, '<hr style="border:none;border-top:1px solid rgba(128,128,128,0.2);margin:8px 0;">')
      // 无序列表 - item
      .replace(/^- (.+)$/gm, '<span style="display:block;padding-left:12px;margin:2px 0;">• $1</span>')
      // 表格行 | ... | （简单处理：加换行和间距）
      .replace(/\|/g, '<span style="opacity:0.5">|</span>')
      // 普通换行
      .replace(/\n/g, '<br>');
    return html;
  }

  function scrollToBottom(el) {
    requestAnimationFrame(function() { el.scrollTop = el.scrollHeight; });
  }

  // ========== 错误消息映射 ==========
  function getErrorMessage(status, rawErr) {
    if (rawErr && rawErr.name === "TypeError" && rawErr.message.indexOf("fetch") !== -1) {
      return "网络连接失败，请检查网络后<button class=\"cw-retry-btn\">重试</button>";
    }
    if (status === 429) return "请求太频繁了，请稍后再试";
    if (status === 502 || status === 503) return "服务暂时不可用，正在自动重试...";
    if (status >= 500) return "服务器异常（" + status + "），请稍后重试";
    return "请求失败：" + (rawErr ? rawErr.message : "未知错误");
  }

  // ========== SSE 流式发送（带重连） ==========
  async function sendMessage(retryCount) {
    retryCount = retryCount || 0;
    var input = document.getElementById("cwInput");
    var text;

    // 首次调用时读取输入
    if (retryCount === 0) {
      text = input.value.trim();
      if (!text || isLoading) return;
      input.value = "";
      autoResize(input);

      appendMessage(text, "user");
      history.push({ role: "user", content: text });
      saveHistory();
      renderQuickQuestions(predictQuestions(text));
    } else {
      // 重试时取最后一条用户消息
      var lastUser = null;
      for (var i = history.length - 1; i >= 0; i--) {
        if (history[i].role === "user") { lastUser = history[i]; break; }
      }
      text = lastUser ? lastUser.content : "";
    }

    isLoading = true;
    var sendBtn = document.getElementById("cwSend");
    sendBtn.classList.add("cw-loading");

    var bot = appendBotMessage();
    bot.modelTag.textContent = retryCount > 0 ? "正在重试（" + retryCount + "/" + MAX_RETRIES + "）..." : "正在连接...";
    bot.contentSpan.innerHTML = '<span class="cw-dots"><i></i><i></i><i></i></span>';

    try {
      var resp = await fetch(API_BASE + STREAM_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          history: history.filter(function(h) { return h.role !== "assistant" || h.content.length > 0; }).slice(0, -1),
          mode: currentMode,
        }),
      });

      if (!resp.ok) {
        if (resp.status === 502 || resp.status === 503) {
          if (retryCount < MAX_RETRIES) {
            bot.modelTag.textContent = "";
            bot.contentSpan.textContent = "";
            bot.wrapper.remove();
            isLoading = false;
            sendBtn.classList.remove("cw-loading");
            await sleep(RETRY_DELAY[retryCount]);
            return sendMessage(retryCount + 1);
          }
        }
        var errMsg = getErrorMessage(resp.status, null);
        bot.modelTag.textContent = "";
        bot.contentSpan.innerHTML = errMsg;
        bindRetryButtons();
        throw new Error("HTTP " + resp.status);
      }

      var reader = resp.body.getReader();
      var decoder = new TextDecoder();
      var buffer = "";
      var fullReply = "";
      var modelTagSet = false;

      while (true) {
        var streamResult = await reader.read();
        if (streamResult.done) break;

        buffer += decoder.decode(streamResult.value, { stream: true });
        var parts = buffer.split("\n\n");
        buffer = parts.pop();

        for (var p = 0; p < parts.length; p++) {
          var line = parts[p].trim();
          if (line.indexOf("data: ") !== 0) continue;

          var jsonStr = line.slice(6);
          if (jsonStr === "[DONE]") continue;

          try {
            var chunk = JSON.parse(jsonStr);

            if (chunk.type === "model") {
              var label = "模型：" + chunk.name;
              if (chunk.is_reasoning) label += "（思考中...）";
              bot.modelTag.textContent = label;
              modelTagSet = true;
            } else if (chunk.type === "token") {
              fullReply += chunk.content;
              bot.contentSpan.innerHTML = renderMd(fullReply);
              scrollToBottom(document.getElementById("cwMessages"));
            } else if (chunk.type === "done") {
              if (!modelTagSet) bot.modelTag.textContent = "回复完成";
            }
          } catch (e) { /* ignore JSON parse errors */ }
        }
      }

      // SSE 流正常结束但无内容
      if (!fullReply && !modelTagSet) {
        if (retryCount < MAX_RETRIES) {
          bot.wrapper.remove();
          await sleep(RETRY_DELAY[retryCount]);
          isLoading = false;
          sendBtn.classList.remove("cw-loading");
          return sendMessage(retryCount + 1);
        }
        bot.modelTag.textContent = "";
        bot.contentSpan.textContent = "暂无回复，请尝试换个问题";
      }

      if (fullReply) {
        history.push({ role: "assistant", content: fullReply });
        saveHistory();
        if (history.length <= 2) renderQuickQuestions(predictQuestions(fullReply));
      }

    } catch (err) {
      console.error("[chat-widget]", err.message);
      if (retryCount < MAX_RETRIES && (err.name === "TypeError" || err.message.indexOf("Failed to fetch") !== -1)) {
        bot.wrapper.remove();
        await sleep(RETRY_DELAY[retryCount]);
        isLoading = false;
        sendBtn.classList.remove("cw-loading");
        return sendMessage(retryCount + 1);
      }

      bot.modelTag.textContent = "";
      bot.contentSpan.innerHTML = getErrorMessage(0, err);
      bindRetryButtons();
    } finally {
      isLoading = false;
      sendBtn.classList.remove("cw-loading");
    }
  }

  function sleep(ms) {
    return new Promise(function(resolve) { setTimeout(resolve, ms); });
  }

  // ========== 重试按钮绑定 ==========
  function bindRetryButtons() {
    var btns = document.querySelectorAll(".cw-retry-btn");
    for (var i = 0; i < btns.length; i++) {
      btns[i].onclick = sendMessage;
    }
  }

  // ========== 输入框 ==========
  function autoResize(el) {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  }

  // ========== 主题监听 ==========
  function watchTheme() {
    var observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(m) {
        if (m.attributeName === "data-theme") {
          updatePanelTheme();
        }
      });
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  }

  function updatePanelTheme() {
    var theme = getPageTheme();
    var header = document.querySelector(".cw-header");
    if (!header) return;
    if (theme === "geek") {
      header.style.background = "linear-gradient(135deg, #2d6a4f, #40916c)";
    } else {
      header.style.background = "";
    }
  }

  // ========== 初始化 ==========
  function init() {
    injectDOM();

    document.getElementById("cwTrigger").addEventListener("click", toggle);
    document.getElementById("cwClose").addEventListener("click", toggle);
    document.getElementById("cwClear").addEventListener("click", function(e) {
      e.stopPropagation();
      if (confirm("确定清空所有对话记录吗？")) clearHistory();
    });
    document.getElementById("cwModeCheckbox").addEventListener("change", onModeChange);

    var input = document.getElementById("cwInput");
    document.getElementById("cwSend").addEventListener("click", function() { sendMessage(0); });

    input.addEventListener("keydown", function(e) {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(0); }
    });

    input.addEventListener("input", function() { autoResize(this); });

    restoreHistory();
    if (history.length === 0) renderQuickQuestions(DEFAULT_QUESTIONS);

    watchTheme();
    updatePanelTheme();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
