import assert from "node:assert/strict";
import test from "node:test";

import { createAuthSessionStore } from "../frontend/assets/js/auth-session-store-core.js";

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

test("one initialization is shared and publishes a single authenticated snapshot", async () => {
  const pending = deferred();
  let calls = 0;
  const store = createAuthSessionStore(() => {
    calls += 1;
    return pending.promise;
  });
  const statuses = [];
  store.subscribe((snapshot) => statuses.push(snapshot.status));

  const first = store.initialize();
  const second = store.initialize();
  assert.equal(first, second);
  pending.resolve({ user: { id: "usr_1", username: "alice" }, profile: {} });
  const snapshot = await first;

  assert.equal(calls, 1);
  assert.equal(snapshot.status, "authenticated");
  assert.equal(snapshot.user.username, "alice");
  assert.deepEqual(statuses, ["loading", "authenticated"]);
});

test("a slower obsolete resolution cannot overwrite a forced refresh", async () => {
  const oldRequest = deferred();
  const newRequest = deferred();
  const requests = [oldRequest, newRequest];
  const store = createAuthSessionStore(() => requests.shift().promise);

  const oldInitialization = store.initialize();
  await Promise.resolve();
  const newInitialization = store.initialize({ force: true });
  await Promise.resolve();
  newRequest.resolve({ user: { id: "usr_new", username: "new" }, profile: {} });
  await newInitialization;
  oldRequest.resolve({ user: { id: "usr_old", username: "old" }, profile: {} });
  await oldInitialization;

  assert.equal(store.getSnapshot().user.username, "new");
});

test("a failed restore settles as unauthenticated instead of staying loading", async () => {
  const store = createAuthSessionStore(async () => {
    throw new Error("expired session");
  });
  const snapshot = await store.initialize();
  assert.equal(snapshot.status, "unauthenticated");
  assert.equal(snapshot.user, null);
  assert.equal(snapshot.error.message, "expired session");
});
