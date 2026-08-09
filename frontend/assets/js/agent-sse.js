const ALLOWED_EVENTS = new Set([
  "response.started",
  "agent.progress",
  "response.answer.delta",
  "response.completed",
]);
const MAX_BUFFER_CHARS = 1_000_000;

function protocolError(message) {
  const error = new Error(message);
  error.code = "AGENT_STREAM_PROTOCOL_INVALID";
  return error;
}

function parseBlock(block, state) {
  let eventName = "";
  const dataLines = [];
  block.split("\n").forEach((line) => {
    if (line.startsWith("event:")) eventName = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
    else if (line && !line.startsWith(":")) throw protocolError("流式事件包含未知字段");
  });
  if (!ALLOWED_EVENTS.has(eventName) || !dataLines.length) {
    throw protocolError("流式事件类型或数据无效");
  }

  let payload;
  try {
    payload = JSON.parse(dataLines.join("\n"));
  } catch {
    throw protocolError("流式事件不是有效 JSON");
  }
  if (
    payload?.event !== eventName
    || payload.sequence !== state.nextSequence
    || typeof payload.requestId !== "string"
    || !payload.requestId
  ) {
    throw protocolError("流式事件顺序或请求标识无效");
  }
  if (state.requestId && payload.requestId !== state.requestId) {
    throw protocolError("流式事件请求标识发生变化");
  }
  state.requestId ||= payload.requestId;
  state.nextSequence += 1;

  if (eventName === "response.started") {
    if (state.started || payload.delta != null || payload.response != null) {
      throw protocolError("流式开始事件无效");
    }
    state.started = true;
  } else if (eventName === "agent.progress") {
    if (!state.started || state.completed || !payload.progress || payload.delta != null || payload.response != null) {
      throw protocolError("Agent 进度事件无效");
    }
  } else if (eventName === "response.answer.delta") {
    if (!state.started || state.completed || typeof payload.delta !== "string" || !payload.delta) {
      throw protocolError("流式回答片段无效");
    }
  } else {
    if (!state.started || state.completed || !payload.response || payload.delta != null) {
      throw protocolError("流式完成事件无效");
    }
    state.completed = true;
  }
  return payload;
}

export async function consumeAgentEventStream(response, onEvent, { signal } = {}) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const state = {
    started: false,
    completed: false,
    requestId: "",
    nextSequence: 0,
  };
  let buffer = "";
  try {
    while (true) {
      if (signal?.aborted) throw signal.reason || new DOMException("Aborted", "AbortError");
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      buffer = buffer.replaceAll("\r\n", "\n");
      if (buffer.length > MAX_BUFFER_CHARS) throw protocolError("流式响应超过缓冲区限制");

      let boundary = buffer.indexOf("\n\n");
      while (boundary >= 0) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        if (block.trim()) await onEvent(parseBlock(block, state));
        boundary = buffer.indexOf("\n\n");
      }
      if (done) break;
    }
    if (buffer.trim() || !state.completed) throw protocolError("流式响应未正常完成");
  } catch (error) {
    await reader.cancel(error).catch(() => {});
    throw error;
  } finally {
    reader.releaseLock();
  }
}
