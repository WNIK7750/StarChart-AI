function frozenSnapshot({ status, user = null, profile = {}, error = null, revision }) {
  return Object.freeze({ status, user, profile, error, revision });
}

export function createAuthSessionStore(resolveSession) {
  let revision = 0;
  let attemptVersion = 0;
  let inFlight = null;
  let snapshot = frozenSnapshot({ status: "loading", revision });
  const listeners = new Set();

  function publish(next) {
    revision += 1;
    snapshot = frozenSnapshot({ ...next, revision });
    listeners.forEach((listener) => listener(snapshot));
    return snapshot;
  }

  function getSnapshot() {
    return snapshot;
  }

  function subscribe(listener) {
    listeners.add(listener);
    listener(snapshot);
    return () => listeners.delete(listener);
  }

  function initialize({ force = false } = {}) {
    if (inFlight && !force) return inFlight;
    const attempt = ++attemptVersion;
    if (snapshot.status !== "authenticated" && snapshot.status !== "loading") {
      publish({ status: "loading", user: null, profile: {}, error: null });
    }
    const request = Promise.resolve()
      .then(() => resolveSession())
      .then(({ user = null, profile = {} } = {}) => {
        if (attempt !== attemptVersion) return snapshot;
        return user
          ? publish({ status: "authenticated", user, profile, error: null })
          : publish({ status: "unauthenticated", user: null, profile: {}, error: null });
      })
      .catch((error) => {
        if (attempt !== attemptVersion) return snapshot;
        return publish({ status: "unauthenticated", user: null, profile: {}, error });
      })
      .finally(() => {
        if (attempt === attemptVersion) inFlight = null;
      });
    inFlight = request;
    return request;
  }

  function setUnauthenticated(error = null) {
    attemptVersion += 1;
    inFlight = null;
    return publish({ status: "unauthenticated", user: null, profile: {}, error });
  }

  return Object.freeze({ getSnapshot, subscribe, initialize, setUnauthenticated });
}
