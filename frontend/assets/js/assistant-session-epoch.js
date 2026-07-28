function tokenIdentity(token) {
  const value = String(token || "");
  if (!value) return "";
  try {
    const encoded = value.split(".")[1];
    if (!encoded) return value;
    const normalized = encoded.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
    const bytes = Uint8Array.from(atob(padded), (character) => character.charCodeAt(0));
    const subject = JSON.parse(new TextDecoder().decode(bytes))?.sub;
    return typeof subject === "string" && subject ? subject : value;
  } catch {
    return value;
  }
}

export class AssistantSessionEpoch {
  constructor(token = "") {
    this.identity = tokenIdentity(token);
    this.epoch = 0;
    this.controllers = new Set();
  }

  transition(token = "") {
    const nextIdentity = tokenIdentity(token);
    if (nextIdentity === this.identity) return false;
    this.identity = nextIdentity;
    this.epoch += 1;
    const reason = new DOMException("Assistant identity changed", "AbortError");
    this.controllers.forEach((controller) => controller.abort(reason));
    return true;
  }

  beginOperation() {
    const controller = new AbortController();
    const capturedEpoch = this.epoch;
    let finished = false;
    this.controllers.add(controller);
    return Object.freeze({
      signal: controller.signal,
      isCurrent: () => (
        !finished
        && !controller.signal.aborted
        && capturedEpoch === this.epoch
      ),
      finish: () => {
        if (finished) return;
        finished = true;
        this.controllers.delete(controller);
      },
    });
  }
}
