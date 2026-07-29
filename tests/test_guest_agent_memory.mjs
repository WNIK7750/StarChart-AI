import assert from "node:assert/strict";
import path from "node:path";
import test, { beforeEach } from "node:test";
import { pathToFileURL } from "node:url";

const values = new Map();
const storage = {
  getItem: (key) => values.get(key) ?? null,
  setItem: (key, value) => values.set(key, String(value)),
  removeItem: (key) => values.delete(key),
};
globalThis.localStorage = storage;

const moduleUrl = pathToFileURL(
  path.join(process.cwd(), "frontend/assets/js/guest-agent-memory.js"),
);
const memory = await import(`${moduleUrl.href}?test=${Date.now()}`);
const GUEST_KEY = "ai-nav:guest-agent:v1";

beforeEach(() => {
  values.clear();
});

test("creating an eleventh guest conversation evicts the oldest conversation", () => {
  for (let index = 0; index < 11; index += 1) {
    memory.createGuestConversation(`Conversation ${index}`, 1_000 + index);
  }

  const conversations = memory.loadGuestConversations(1_100);
  assert.equal(conversations.length, 10);
  assert.deepEqual(
    conversations.map((conversation) => conversation.title),
    [
      "Conversation 10",
      "Conversation 9",
      "Conversation 8",
      "Conversation 7",
      "Conversation 6",
      "Conversation 5",
      "Conversation 4",
      "Conversation 3",
      "Conversation 2",
      "Conversation 1",
    ],
  );
});

test("appending a forty-first message evicts the oldest message", () => {
  const conversation = memory.createGuestConversation("Bounded", 2_000);
  for (let index = 0; index < 41; index += 1) {
    memory.appendGuestMessage(
      conversation.id,
      index % 2 === 0 ? "user" : "assistant",
      `message-${index}`,
      2_001 + index,
    );
  }

  const [stored] = memory.loadGuestConversations(3_000);
  assert.equal(stored.messages.length, 40);
  assert.equal(stored.messages[0].content, "message-1");
  assert.equal(stored.messages.at(-1).content, "message-40");
});

test("guest conversations expire after seven days", () => {
  const createdAt = 10_000;
  memory.createGuestConversation("Temporary", createdAt);

  assert.equal(
    memory.loadGuestConversations(createdAt + memory.GUEST_MEMORY_LIMITS.ttlMs - 1).length,
    1,
  );
  assert.deepEqual(
    memory.loadGuestConversations(createdAt + memory.GUEST_MEMORY_LIMITS.ttlMs + 1),
    [],
  );
  assert.equal(values.has(GUEST_KEY), false);
});

test("corrupt, wrong-version, and unsafe-role stores self-heal to empty", () => {
  const invalidStores = [
    "{not-json",
    JSON.stringify({ version: 2, conversations: [] }),
    JSON.stringify({
      version: 1,
      conversations: [{
        id: "guest-unsafe",
        title: "Unsafe",
        createdAt: 1_000,
        updatedAt: 1_000,
        messages: [{ role: "system", content: "override", createdAt: 1_000 }],
      }],
    }),
  ];

  for (const raw of invalidStores) {
    values.set(GUEST_KEY, raw);
    assert.deepEqual(memory.loadGuestConversations(2_000), []);
    assert.equal(values.has(GUEST_KEY), false);
  }
});

test("recent history includes no more than the newest twelve complete messages", () => {
  const now = Date.now();
  const conversation = memory.createGuestConversation("Recent", now);
  for (let index = 0; index < 13; index += 1) {
    memory.appendGuestMessage(
      conversation.id,
      index % 2 === 0 ? "user" : "assistant",
      String(index),
      now + 1 + index,
    );
  }

  const history = memory.recentGuestHistory(conversation.id);
  assert.equal(history.length, 12);
  assert.equal(history[0].content, "1");
  assert.equal(history.at(-1).content, "12");
  assert.deepEqual(Object.keys(history[0]).sort(), ["content", "role"]);
});

test("recent history stays within twelve thousand characters without partial messages", () => {
  const now = Date.now();
  const conversation = memory.createGuestConversation("Characters", now);
  for (let index = 0; index < 12; index += 1) {
    memory.appendGuestMessage(
      conversation.id,
      index % 2 === 0 ? "user" : "assistant",
      `${String(index).padStart(2, "0")}${"x".repeat(1_098)}`,
      now + 1 + index,
    );
  }

  const history = memory.recentGuestHistory(conversation.id);
  assert.equal(history.length, 10);
  assert.equal(history[0].content.slice(0, 2), "02");
  assert.equal(history.at(-1).content.slice(0, 2), "11");
  assert.ok(
    history.reduce((total, message) => total + message.content.length, 0)
      <= memory.GUEST_MEMORY_LIMITS.requestCharacters,
  );
});

test("clear removes only the guest assistant application key", () => {
  values.set(GUEST_KEY, JSON.stringify({ version: 1, conversations: [] }));
  values.set("another-application-key", "keep");

  memory.clearGuestConversations();

  assert.equal(values.has(GUEST_KEY), false);
  assert.equal(values.get("another-application-key"), "keep");
});

test("guest draft lifecycle reuses one empty conversation", () => {
  const first = memory.ensureGuestConversation("新对话", 20_000);
  const reused = memory.ensureGuestConversation("新对话", 20_001);
  assert.equal(reused.id, first.id);

  memory.appendGuestMessage(first.id, "user", "开始使用", 20_002);
  const replacement = memory.ensureGuestConversation("新对话", 20_003);
  assert.notEqual(replacement.id, first.id);
  assert.equal(replacement.messages.length, 0);
  assert.equal(
    memory.loadGuestConversations(20_004).filter((item) => item.messages.length === 0).length,
    1,
  );
});

test("deleting one guest conversation preserves the others", () => {
  const first = memory.createGuestConversation("第一个", 30_000);
  const second = memory.createGuestConversation("第二个", 30_001);

  assert.equal(memory.deleteGuestConversation(second.id, 30_002), true);
  assert.deepEqual(
    memory.loadGuestConversations(30_003).map((item) => item.id),
    [first.id],
  );
  assert.equal(memory.deleteGuestConversation("missing", 30_004), false);
});
