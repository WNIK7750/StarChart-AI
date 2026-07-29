const GUEST_MEMORY_KEY = "ai-nav:guest-agent:v1";
const SCHEMA_VERSION = 1;
const SAFE_ROLES = new Set(["user", "assistant"]);
const MAX_STORED_MESSAGE_CHARACTERS = 6000;

export const GUEST_MEMORY_LIMITS = Object.freeze({
  conversations: 10,
  messagesPerConversation: 40,
  ttlMs: 7 * 24 * 60 * 60 * 1000,
  requestMessages: 12,
  requestCharacters: 12000,
});

function storage() {
  return globalThis.localStorage;
}

function removeStore() {
  try {
    storage()?.removeItem(GUEST_MEMORY_KEY);
  } catch {
    // A disabled browser store behaves like empty guest memory.
  }
}

function saveConversations(conversations) {
  if (!conversations.length) {
    removeStore();
    return;
  }
  try {
    storage()?.setItem(GUEST_MEMORY_KEY, JSON.stringify({
      version: SCHEMA_VERSION,
      conversations,
    }));
  } catch {
    // Guest chat remains usable for the current request if storage is unavailable.
  }
}

function isFiniteTimestamp(value) {
  return Number.isFinite(value) && value >= 0;
}

function isSafeMessage(message) {
  return Boolean(
    message
    && SAFE_ROLES.has(message.role)
    && typeof message.content === "string"
    && message.content.length > 0
    && message.content.length <= MAX_STORED_MESSAGE_CHARACTERS
    && isFiniteTimestamp(message.createdAt),
  );
}

function isSafeConversation(conversation) {
  return Boolean(
    conversation
    && typeof conversation.id === "string"
    && conversation.id.length > 0
    && typeof conversation.title === "string"
    && conversation.title.length > 0
    && conversation.title.length <= 120
    && isFiniteTimestamp(conversation.createdAt)
    && isFiniteTimestamp(conversation.updatedAt)
    && conversation.updatedAt >= conversation.createdAt
    && Array.isArray(conversation.messages)
    && conversation.messages.every(isSafeMessage),
  );
}

function parseConversations() {
  let raw;
  try {
    raw = storage()?.getItem(GUEST_MEMORY_KEY);
  } catch {
    return [];
  }
  if (!raw) return [];
  try {
    const stored = JSON.parse(raw);
    if (
      stored?.version !== SCHEMA_VERSION
      || !Array.isArray(stored.conversations)
      || !stored.conversations.every(isSafeConversation)
    ) {
      removeStore();
      return [];
    }
    return stored.conversations;
  } catch {
    removeStore();
    return [];
  }
}

function normalizeConversations(conversations, now) {
  const oldestAllowed = now - GUEST_MEMORY_LIMITS.ttlMs;
  return conversations
    .filter((conversation) => conversation.updatedAt > oldestAllowed)
    .map((conversation) => ({
      id: conversation.id,
      title: conversation.title,
      createdAt: conversation.createdAt,
      updatedAt: conversation.updatedAt,
      messages: conversation.messages
        .slice(-GUEST_MEMORY_LIMITS.messagesPerConversation)
        .map((message) => ({
          role: message.role,
          content: message.content,
          createdAt: message.createdAt,
        })),
    }))
    .sort((left, right) => right.updatedAt - left.updatedAt)
    .slice(0, GUEST_MEMORY_LIMITS.conversations);
}

function newConversationId() {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return `guest-${globalThis.crypto.randomUUID()}`;
  }
  return `guest-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function loadGuestConversations(now = Date.now()) {
  const parsed = parseConversations();
  const normalized = normalizeConversations(parsed, now);
  if (JSON.stringify(parsed) !== JSON.stringify(normalized)) {
    saveConversations(normalized);
  }
  return normalized;
}

export function createGuestConversation(title, now = Date.now()) {
  const conversation = {
    id: newConversationId(),
    title: String(title || "").trim().slice(0, 120) || "新对话",
    createdAt: now,
    updatedAt: now,
    messages: [],
  };
  const conversations = normalizeConversations(
    [conversation, ...loadGuestConversations(now)],
    now,
  );
  saveConversations(conversations);
  return conversation;
}

export function ensureGuestConversation(title = "新对话", now = Date.now()) {
  const conversations = loadGuestConversations(now);
  const draft = conversations.find((conversation) => conversation.messages.length === 0);
  if (!draft) return createGuestConversation(title, now);
  const withoutDuplicateDrafts = conversations.filter(
    (conversation) => conversation.messages.length > 0 || conversation.id === draft.id,
  );
  if (withoutDuplicateDrafts.length !== conversations.length) {
    saveConversations(withoutDuplicateDrafts);
  }
  return draft;
}

export function deleteGuestConversation(conversationId, now = Date.now()) {
  const conversations = loadGuestConversations(now);
  const remaining = conversations.filter(
    (conversation) => conversation.id !== conversationId,
  );
  if (remaining.length === conversations.length) return false;
  saveConversations(remaining);
  return true;
}

export function appendGuestMessage(conversationId, role, content, now = Date.now()) {
  if (!SAFE_ROLES.has(role)) throw new TypeError("Guest message role is not allowed");
  const normalizedContent = String(content || "").trim().slice(0, MAX_STORED_MESSAGE_CHARACTERS);
  if (!normalizedContent) throw new TypeError("Guest message content is required");

  const conversations = loadGuestConversations(now);
  const conversation = conversations.find((item) => item.id === conversationId);
  if (!conversation) throw new Error("Guest conversation was not found");
  conversation.messages = [
    ...conversation.messages,
    { role, content: normalizedContent, createdAt: now },
  ].slice(-GUEST_MEMORY_LIMITS.messagesPerConversation);
  conversation.updatedAt = now;
  const normalized = normalizeConversations(conversations, now);
  saveConversations(normalized);
  return normalized.find((item) => item.id === conversationId) || null;
}

export function recentGuestHistory(conversationId, maxMessages = 12) {
  const conversation = loadGuestConversations()
    .find((item) => item.id === conversationId);
  if (!conversation) return [];

  const limit = Math.min(
    Math.max(0, Number.isFinite(maxMessages) ? Math.floor(maxMessages) : 0),
    GUEST_MEMORY_LIMITS.requestMessages,
  );
  const history = [];
  let characters = 0;
  for (const message of conversation.messages.slice(-limit).reverse()) {
    if (characters + message.content.length > GUEST_MEMORY_LIMITS.requestCharacters) break;
    history.unshift({ role: message.role, content: message.content });
    characters += message.content.length;
  }
  return history;
}

export function clearGuestConversations() {
  removeStore();
}
