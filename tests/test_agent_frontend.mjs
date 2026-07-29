import assert from "node:assert/strict";
import fs from "node:fs";

const html = fs.readFileSync("frontend/assistant.html", "utf8");
const script = fs.readFileSync("frontend/assets/js/assistant-page.js", "utf8");
const search = fs.readFileSync("frontend/assets/js/site-search.js", "utf8");

assert.match(html, /id="assistantForm"/);
assert.match(html, /id="stopButton"/);
assert.match(html, /id="assistantStatus" role="status" aria-live="polite" aria-atomic="true"/);
assert.match(html, /id="stopButton"[^>]+aria-keyshortcuts="Escape"/);
assert.match(html, /id="sessionPanel"/);
assert.match(html, /id="longConversationPanel"/);
assert.match(html, /id="longConversationList" aria-label="长期对话列表"/);
assert.ok(
  html.indexOf('id="longConversationPanel"') < html.indexOf('id="sessionList"'),
  "长期对话必须显示在短期会话上方",
);
assert.match(html, /id="contextPanel"/);
assert.match(html, /id="newSessionButton"/);
assert.match(html, /id="mobileSessionsButton"/);
assert.match(html, /aria-controls="contextPanel"/);
assert.match(html, /id="closeSessionsButton"/);
assert.match(html, /id="drawerScrim"/);
assert.match(html, /id="sessionRenameDialog"/);
assert.match(html, /id="sessionRenameInput" maxlength="120"/);
assert.match(html, /id="assistantHeaderNav"/);
assert.match(html, /class="assistant-header-links"/);
assert.match(html, /class="sidebar-footer sidebar-footer-mobile"/);
assert.match(html, /data-page="assistant"/);
assert.match(html, /站内证据只读模式/);
assert.match(html, /今天想学什么？/);
assert.match(html, /data-prompt="RAG 怎么学？">RAG 怎么学？<\/button>/);
assert.doesNotMatch(html, /RAG 和微调应该先学哪个/);
assert.match(html, /回答基于站内公开证据。请勿输入密码、令牌或联系方式等敏感信息。/);
assert.match(html, /id="guestMemoryNotice"/);
assert.match(html, /游客记录仅保存在当前浏览器 7 天；登录不会自动导入/);
assert.match(html, /id="clearGuestHistoryButton"/);
assert.match(html, /data-settings-link/);
assert.doesNotMatch(html, /class="evidence-panel"/);
assert.doesNotMatch(html, /确定性只读模式|当前为确定性检索模式/);
assert.match(script, /getAccessToken/);
assert.match(script, /ai-nav-auth-changed/);
assert.match(script, /apiPost\("\/agent\/guest\/chat"/);
assert.match(script, /apiPost\("\/agent\/chat"/);
assert.match(script, /apiPostStream\("\/agent\/chat\/stream"/);
assert.match(script, /apiGet\("\/agent\/capabilities"/);
assert.match(script, /apiPost\("\/agent\/sessions"/);
assert.match(script, /apiGet\(\s*"\/agent\/long-conversations"/);
assert.match(
  script,
  /apiDelete\(conversationEndpoint\(sessionId\), \{ signal: operation\.signal \}\)/,
);
assert.match(script, /apiPatch\(conversationEndpoint\(sessionId\)/);
assert.match(script, /apiPost\(\s*`\/agent\/sessions\/\$\{sessionId\}\/upgrade`/);
assert.match(script, /AGENT_SESSION_UNSTARTED_EXISTS/);
assert.match(script, /AGENT_LONG_CONVERSATION_LIMIT_REACHED/);
assert.match(script, /sessionCreationBlocked = items\.some/);
assert.match(script, /dataset\.upgradeSessionId/);
assert.match(script, /dataset\.pinSessionId/);
assert.match(script, /dataset\.renameSessionId/);
assert.match(script, /session\.pinned \? "取消置顶" : "置顶"/);
assert.match(script, /payload\.sessionId = requestSessionId/);
assert.match(script, /available\.sessions === true/);
assert.match(script, /session-drawer-open/);
assert.match(script, /function openMobileSessions\(\)/);
assert.match(script, /closeSessionsButton\?\.focus\(\)/);
assert.match(script, /drawerScrim\?\.addEventListener/);
assert.match(script, /event\.key !== "Escape"/);
assert.match(script, /function stopActiveRequest\(\)/);
assert.match(script, /if \(activeController\)/);
assert.match(script, /closeMobileSessions\(\{ restoreFocus: true \}\)/);
assert.match(script, /mobileSessionsButton\?\.focus\(\)/);
assert.match(script, /consumeAgentEventStream/);
assert.match(script, /new AbortController\(\)/);
assert.match(script, /activeController\?\.abort/);
assert.match(script, /typeof globalThis\.crypto\?\.randomUUID === "function"/);
assert.match(script, /Date\.now\(\)\.toString\(36\)/);
assert.match(script, /"X-Request-Id": stableRequestId/);
assert.match(script, /dataset\.agentRetry/);
assert.match(script, /重新发送/);
assert.match(script, /retry: true/);
assert.match(script, /sessionId: requestSessionId/);
assert.match(script, /saveAgentWorkflow/);
assert.match(script, /if \(!isAuthenticatedMode\(\)\)/);
assert.match(script, /const guestDraft = !isAuthenticatedMode\(\)/);
assert.match(script, /button\.disabled = guestDraft \|\| !checkbox\.checked/);
assert.match(script, /游客可在本页创建和编辑草稿，但不能保存或归档/);
assert.match(script, /recentGuestHistory/);
assert.match(script, /appendGuestMessage/);
assert.match(script, /clearGuestConversations/);
assert.match(
  script,
  /if \(conversation\.messages\.length === 0\) \{\s*resetConversation\(\);\s*\} else \{\s*messages\.replaceChildren\(\);[\s\S]*conversation\.messages\.forEach/,
  "空游客会话必须恢复“今天想学什么？”欢迎区",
);
assert.match(script, /window\.confirm/);
assert.match(script, /input\.value = text/);
assert.match(script, /window\.addEventListener\("ai-nav-auth-changed"/);
assert.match(script, /const settingsLink = event\.target\.closest\("\[data-settings-link\]"\)/);
assert.match(script, /if \(!settingsLink \|\| isAuthenticatedMode\(\)\) return;/);
assert.match(script, /请先登录后进入设置/);
assert.doesNotMatch(script, /status === 401[\s\S]{0,400}\/agent\/guest\/chat/);
assert.match(script, /confirmed: true/);
assert.match(script, /保存前检查草稿/);
assert.match(script, /let stableKey = requestId\("agent"\)/);
assert.match(script, /let submittedPayload = null/);
assert.match(script, /saveAgentWorkflow\(submittedPayload, stableKey\)/);
assert.match(script, /重试同一次保存/);
assert.match(script, /WORKFLOW_IDEMPOTENCY_CONFLICT/);
assert.match(script, /safeInternalHref\(`\/settings\?workflow=\$\{encodeURIComponent\(workflowUid\)\}#workflows`\)/);
assert.match(script, /查看已保存的工作流/);
assert.match(script, /核对个人工作流/);
assert.match(script, /data-auth-trigger="login"/);
assert.match(script, /response\.meta\?\.mode === "provider"/);
assert.match(script, /response\.meta\?\.fallbackReason/);
assert.match(script, /createFrameBuffer/);
assert.match(script, /void loadSessionList\(\{[\s\S]*short:/);
assert.doesNotMatch(script, /await loadSessionList\(\);\s*if \(!operation\.isCurrent\(\)\) return;\s*\} else if \(!authenticatedRequest\)/);
assert.match(script, /sessionListRequestVersion = \{ short: 0, long: 0 \}/);
assert.match(script, /Promise\.allSettled\(\[/);
assert.match(script, /shortResult\.status === "fulfilled"/);
assert.match(script, /longResult\.status === "fulfilled"/);
assert.match(script, /document\.createDocumentFragment\(\)/);
assert.doesNotMatch(script, /tool-data\.js|learning-data\.js/);
assert.match(search, /url: "\/assistant"/);

console.log("agent frontend contract tests passed");
