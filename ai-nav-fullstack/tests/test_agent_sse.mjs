import assert from "node:assert/strict";
import test from "node:test";

import { consumeAgentEventStream } from "../frontend/assets/js/agent-sse.js";

const encoder = new TextEncoder();

function responseFromChunks(chunks) {
  return new Response(new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)));
      controller.close();
    },
  }), {
    headers: { "Content-Type": "text/event-stream" },
  });
}

test("agent SSE parser handles split CRLF frames and preserves event order", async () => {
  const frames = [
    'event: response.started\r\ndata: {"event":"response.started","sequence":0,"requestId":"req-1","delta":null,"response":null}\r\n\r\n',
    'event: response.answer.delta\r\ndata: {"event":"response.answer.delta","sequence":1,"requestId":"req-1","delta":"你好","response":null}\r\n\r\n',
    'event: response.completed\r\ndata: {"event":"response.completed","sequence":2,"requestId":"req-1","delta":null,"response":{"answer":"你好"}}\r\n\r\n',
  ].join("");
  const events = [];
  await consumeAgentEventStream(
    responseFromChunks([frames.slice(0, 31), frames.slice(31, 117), frames.slice(117)]),
    async (event) => events.push(event),
  );
  assert.deepEqual(events.map((event) => event.event), [
    "response.started",
    "response.answer.delta",
    "response.completed",
  ]);
  assert.equal(events[1].delta, "你好");
  assert.equal(events[2].response.answer, "你好");
});

test("agent SSE parser rejects skipped sequences and incomplete streams", async () => {
  const invalid = [
    'event: response.started\ndata: {"event":"response.started","sequence":0,"requestId":"req-1"}\n\n',
    'event: response.answer.delta\ndata: {"event":"response.answer.delta","sequence":2,"requestId":"req-1","delta":"x"}\n\n',
  ].join("");
  await assert.rejects(
    consumeAgentEventStream(responseFromChunks([invalid]), async () => {}),
    (error) => error.code === "AGENT_STREAM_PROTOCOL_INVALID",
  );
});
