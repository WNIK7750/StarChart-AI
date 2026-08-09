import { withPublicBasePath } from "./public-path.js";

const ALLOWED_PAGES = new Set(["home", "learn", "tools"]);
const SESSION_STORAGE_KEY = "ai-nav:quick-assistant-session:v1";
const GEOMETRY_STORAGE_KEY = "ai-nav:quick-assistant-geometry:v1";
const SAFE_SESSION_ID = /^(?:ags_|agl_)[a-f0-9]{32}$|^guest-[a-zA-Z0-9-]{8,80}$/;
const PANEL_ASPECT_RATIO = 7 / 12;
const PANEL_MARGIN = 12;
const MIN_PANEL_WIDTH = 340;
const MAX_PANEL_WIDTH = 560;

function readStoredSession() {
  try {
    const sessionId = globalThis.sessionStorage?.getItem(SESSION_STORAGE_KEY) || "";
    return SAFE_SESSION_ID.test(sessionId) ? sessionId : "";
  } catch {
    return "";
  }
}

function storeSession(sessionId) {
  try {
    if (SAFE_SESSION_ID.test(sessionId || "")) {
      globalThis.sessionStorage?.setItem(SESSION_STORAGE_KEY, sessionId);
    }
    else globalThis.sessionStorage?.removeItem(SESSION_STORAGE_KEY);
  } catch {
    // The launcher remains usable when browser storage is unavailable.
  }
}

function clamp(value, minimum, maximum) {
  return Math.min(Math.max(value, minimum), maximum);
}

function readStoredGeometry() {
  try {
    const geometry = JSON.parse(globalThis.sessionStorage?.getItem(GEOMETRY_STORAGE_KEY) || "null");
    return geometry
      && ["left", "top", "width"].every((key) => Number.isFinite(geometry[key]))
      ? geometry
      : null;
  } catch {
    return null;
  }
}

function storeGeometry({ left, top, width }) {
  try {
    globalThis.sessionStorage?.setItem(
      GEOMETRY_STORAGE_KEY,
      JSON.stringify({ left, top, width }),
    );
  } catch {
    // Window movement remains available when browser storage is unavailable.
  }
}

function createIcon(path) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  const shape = document.createElementNS("http://www.w3.org/2000/svg", "path");
  shape.setAttribute("d", path);
  svg.appendChild(shape);
  return svg;
}

function ensureStylesheet() {
  if (document.querySelector('link[data-assistant-launcher-style="true"]')) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = withPublicBasePath("/assets/css/assistant-launcher.css");
  link.dataset.assistantLauncherStyle = "true";
  document.head.appendChild(link);
}

function quickAssistantMarkup(sessionId) {
  return `
    <div class="quick-assistant-native" data-assistant-quick-app data-initial-session="${sessionId}">
      <aside class="context-panel" id="contextPanel" aria-label="会话导航">
        <div class="sidebar-head">
          <div>
            <strong>对话记录</strong>
            <span>继续最近的学习讨论</span>
          </div>
          <button type="button" id="closeSessionsButton" class="sidebar-icon" aria-label="关闭会话列表">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg>
          </button>
        </div>
        <button type="button" id="newSessionButton" class="session-new" hidden>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
          <span>新建对话</span>
        </button>
        <div id="guestMemoryNotice" hidden>
          <p class="session-empty">游客记录在当前浏览器保存 7 天，登录后不会自动导入。</p>
          <button type="button" id="clearGuestHistoryButton" class="session-clear">清除游客历史</button>
        </div>
        <section class="session-panel" id="sessionPanel" hidden>
          <section class="session-group" id="longConversationPanel">
            <div class="session-heading"><h2>长期对话</h2></div>
            <div class="session-list" id="longConversationList" aria-label="长期对话列表"></div>
            <div class="session-empty" id="longConversationEmpty">还没有长期对话</div>
          </section>
          <section class="session-group session-group-short">
            <div class="session-heading"><h2>短期会话</h2></div>
            <div class="session-list" id="sessionList" aria-label="短期会话列表"></div>
            <div class="session-empty" id="sessionEmpty">还没有保存的会话</div>
          </section>
        </section>
        <div class="sidebar-footer">
          <span><i aria-hidden="true"></i>站内证据只读模式</span>
        </div>
      </aside>

      <button type="button" class="drawer-scrim" id="drawerScrim" aria-label="关闭会话列表" hidden></button>

      <section class="conversation" aria-label="AI 学习助手快捷对话">
        <header class="conversation-head">
          <div class="conversation-title">
            <button type="button" id="mobileSessionsButton" class="mobile-sessions-button" aria-controls="contextPanel" aria-expanded="false" aria-label="查看历史对话" title="查看历史对话" hidden>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7M3 4v5h5M12 7v5l3 2"/></svg>
            </button>
            <span class="assistant-mark" aria-hidden="true">A+</span>
            <div>
              <h1>AI 学习助手</h1>
              <span class="conversation-status" id="assistantStatus" role="status" aria-live="polite" aria-atomic="true">就绪</span>
            </div>
          </div>
          <div class="quick-head-actions">
            <button type="button" id="quickNewSessionButton" class="quick-head-button" aria-label="开启新对话" title="开启新对话">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
            </button>
            <button type="button" class="quick-login quick-head-button" data-auth-trigger="login" data-quick-login aria-label="登录" title="登录">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 21a7 7 0 0 0-14 0M12 13a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z"/></svg>
            </button>
            <a id="quickExpandButton" class="quick-head-button" href="${withPublicBasePath("/assistant")}" aria-label="在助手页中继续" title="在助手页中继续">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 5h5v5M19 5l-7 7M10 19H5v-5"/></svg>
            </a>
            <button type="button" id="quickCloseButton" class="quick-head-button" aria-label="关闭快捷对话" title="关闭快捷对话">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg>
            </button>
          </div>
        </header>

        <div class="messages" id="messages" aria-live="polite">
          <div class="welcome" id="welcome">
            <span class="welcome-mark" aria-hidden="true">A+</span>
            <h2>今天想学什么？</h2>
            <p>从一个具体问题开始。</p>
            <div class="suggestions">
              <button type="button" data-prompt="RAG 怎么学？">RAG 怎么学？</button>
              <button type="button" data-prompt="推荐免费优先的代码工具">推荐免费代码工具</button>
              <button type="button" data-prompt="带我去学习 Transformer">学习 Transformer</button>
              <button type="button" data-prompt="帮我做一个论文阅读工作流">论文阅读工作流</button>
            </div>
          </div>
        </div>

        <div class="composer-wrap">
          <form class="composer" id="assistantForm">
            <textarea id="assistantInput" rows="1" maxlength="4000" placeholder="询问学习路线、工具或工作流" aria-label="向助手提问" required></textarea>
            <button type="button" id="stopButton" class="stop-button" aria-label="停止生成" aria-keyshortcuts="Escape" title="停止生成" hidden>
              <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="1"/></svg>
            </button>
            <button type="submit" id="sendButton" aria-label="发送">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V5m0 0-6 6m6-6 6 6"/></svg>
            </button>
          </form>
          <p class="composer-note">回答基于站内公开证据，请勿输入敏感信息。</p>
        </div>
      </section>

      <dialog class="session-dialog" id="sessionRenameDialog" aria-labelledby="sessionRenameTitle">
        <form method="dialog" id="sessionRenameForm">
          <h2 id="sessionRenameTitle">修改对话标题</h2>
          <label for="sessionRenameInput">标题</label>
          <input type="text" id="sessionRenameInput" maxlength="120" required autocomplete="off">
          <p class="session-dialog-state" id="sessionRenameState" role="status" aria-live="polite"></p>
          <div class="session-dialog-actions">
            <button type="button" id="sessionRenameCancel">取消</button>
            <button type="submit" class="primary">保存</button>
          </div>
        </form>
      </dialog>
    </div>
    <div class="quick-resize-handle" data-quick-resize-handle role="separator" aria-label="等比例缩放快捷助手窗口" title="拖动以等比例缩放"></div>
  `;
}

export function initAssistantLauncher() {
  const page = document.body?.dataset.page || "";
  if (!ALLOWED_PAGES.has(page) || document.querySelector("[data-assistant-launcher]")) {
    return null;
  }

  ensureStylesheet();

  const root = document.createElement("div");
  root.className = "quick-assistant";
  root.dataset.assistantLauncher = "true";

  const panel = document.createElement("section");
  panel.className = "quick-assistant-panel";
  panel.id = "quickAssistantPanel";
  panel.hidden = true;
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-modal", "false");
  panel.setAttribute("aria-label", "AI 学习助手快捷对话");

  const launcher = document.createElement("button");
  launcher.type = "button";
  launcher.className = "quick-assistant-launcher";
  launcher.setAttribute("aria-controls", panel.id);
  launcher.setAttribute("aria-expanded", "false");
  launcher.setAttribute("aria-label", "打开 AI 学习助手");
  launcher.append(
    createIcon("M7.5 18.5 4 20l1-3.5A7.5 7.5 0 1 1 7.5 18.5Z"),
    createIcon("M7 7l10 10M17 7 7 17"),
  );

  let appReady = null;
  let geometryInitialized = false;

  const applyGeometry = ({ left, top, width }, { persist = false } = {}) => {
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const maxWidth = Math.max(
      240,
      Math.min(
        MAX_PANEL_WIDTH,
        viewportWidth - PANEL_MARGIN * 2,
        (viewportHeight - PANEL_MARGIN * 2) * PANEL_ASPECT_RATIO,
      ),
    );
    const safeWidth = clamp(width, Math.min(MIN_PANEL_WIDTH, maxWidth), maxWidth);
    const height = safeWidth / PANEL_ASPECT_RATIO;
    const safeLeft = clamp(left, PANEL_MARGIN, Math.max(PANEL_MARGIN, viewportWidth - safeWidth - PANEL_MARGIN));
    const safeTop = clamp(top, PANEL_MARGIN, Math.max(PANEL_MARGIN, viewportHeight - height - PANEL_MARGIN));
    panel.style.left = `${safeLeft}px`;
    panel.style.top = `${safeTop}px`;
    panel.style.width = `${safeWidth}px`;
    panel.style.height = `${height}px`;
    panel.style.right = "auto";
    panel.style.bottom = "auto";
    if (persist) storeGeometry({ left: safeLeft, top: safeTop, width: safeWidth });
  };

  const ensureGeometry = () => {
    if (geometryInitialized) return;
    geometryInitialized = true;
    const defaultWidth = Math.min(420, window.innerWidth - PANEL_MARGIN * 2);
    const defaultHeight = defaultWidth / PANEL_ASPECT_RATIO;
    const fallback = {
      left: window.innerWidth - defaultWidth - 24,
      top: window.innerHeight - defaultHeight - 96,
      width: defaultWidth,
    };
    applyGeometry(readStoredGeometry() || fallback);
  };

  const bindWindowControls = () => {
    const header = panel.querySelector(".conversation-head");
    const resizeHandle = panel.querySelector("[data-quick-resize-handle]");
    const quickNewSessionButton = panel.querySelector("#quickNewSessionButton");

    header?.addEventListener("pointerdown", (event) => {
      if (event.button !== 0 || event.target.closest("button,a,input,textarea")) return;
      const start = panel.getBoundingClientRect();
      const startX = event.clientX;
      const startY = event.clientY;
      header.setPointerCapture(event.pointerId);
      root.classList.add("is-dragging");
      const move = (moveEvent) => {
        applyGeometry({
          left: start.left + moveEvent.clientX - startX,
          top: start.top + moveEvent.clientY - startY,
          width: start.width,
        });
      };
      const finish = () => {
        header.removeEventListener("pointermove", move);
        header.removeEventListener("pointerup", finish);
        header.removeEventListener("pointercancel", finish);
        root.classList.remove("is-dragging");
        const current = panel.getBoundingClientRect();
        storeGeometry({ left: current.left, top: current.top, width: current.width });
      };
      header.addEventListener("pointermove", move);
      header.addEventListener("pointerup", finish);
      header.addEventListener("pointercancel", finish);
    });

    resizeHandle?.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      event.preventDefault();
      const start = panel.getBoundingClientRect();
      const startX = event.clientX;
      const startY = event.clientY;
      resizeHandle.setPointerCapture(event.pointerId);
      root.classList.add("is-resizing");
      const move = (moveEvent) => {
        const deltaX = moveEvent.clientX - startX;
        const deltaY = moveEvent.clientY - startY;
        const widthFromX = start.width + deltaX;
        const widthFromY = (start.height + deltaY) * PANEL_ASPECT_RATIO;
        const width = Math.abs(deltaX) >= Math.abs(deltaY * PANEL_ASPECT_RATIO)
          ? widthFromX
          : widthFromY;
        applyGeometry({ left: start.left, top: start.top, width });
      };
      const finish = () => {
        resizeHandle.removeEventListener("pointermove", move);
        resizeHandle.removeEventListener("pointerup", finish);
        resizeHandle.removeEventListener("pointercancel", finish);
        root.classList.remove("is-resizing");
        const current = panel.getBoundingClientRect();
        storeGeometry({ left: current.left, top: current.top, width: current.width });
      };
      resizeHandle.addEventListener("pointermove", move);
      resizeHandle.addEventListener("pointerup", finish);
      resizeHandle.addEventListener("pointercancel", finish);
    });

    quickNewSessionButton?.addEventListener("click", () => {
      panel.querySelector("#newSessionButton")?.click();
    });
  };

  const ensureApp = () => {
    if (appReady) return appReady;
    panel.innerHTML = quickAssistantMarkup(readStoredSession());
    appReady = import("./assistant-page.js")
      .then(() => {
        bindWindowControls();
        panel.querySelector("#assistantInput")?.focus();
      })
      .catch((error) => {
        console.error("Quick assistant initialization failed:", error);
        const messages = panel.querySelector("#messages");
        if (messages) {
          messages.innerHTML = '<div class="quick-load-error" role="alert"><strong>助手暂时无法加载</strong><span>请稍后重试，或前往完整助手页。</span></div>';
        }
      });
    return appReady;
  };

  const setOpen = (open, { restoreFocus = false } = {}) => {
    if (open) void ensureApp();
    panel.hidden = !open;
    root.classList.toggle("is-open", open);
    launcher.setAttribute("aria-expanded", String(open));
    launcher.setAttribute("aria-label", open ? "关闭 AI 学习助手" : "打开 AI 学习助手");
    document.body.classList.toggle("quick-assistant-open", open);
    if (open) {
      window.requestAnimationFrame(ensureGeometry);
      void appReady?.then(() => panel.querySelector("#assistantInput")?.focus());
    }
    else if (restoreFocus) launcher.focus();
  };

  launcher.addEventListener("click", () => {
    setOpen(panel.hidden);
  });

  window.addEventListener("ai-nav:quick-assistant-close", () => {
    setOpen(false, { restoreFocus: true });
  });
  window.addEventListener("ai-nav:quick-assistant-session", (event) => {
    storeSession(event.detail?.sessionId);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || panel.hidden) return;
    if (panel.contains(event.target)) return;
    event.preventDefault();
    setOpen(false, { restoreFocus: true });
  });

  window.addEventListener("resize", () => {
    if (!geometryInitialized) return;
    const current = panel.getBoundingClientRect();
    applyGeometry({ left: current.left, top: current.top, width: current.width });
  }, { passive: true });

  root.append(panel, launcher);
  document.body.appendChild(root);
  return { root, panel, launcher };
}
