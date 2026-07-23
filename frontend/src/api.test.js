import { describe, expect, test, vi } from "vitest";

import {
  SESSION_EXPIRED_EVENT,
  adminUrl,
  apiRoot,
  apiDocsUrl,
  buildPlatformUrl,
  clearSession,
  expireSession,
  getSession,
  saveSession,
} from "./api.js";

function memoryStorage() {
  const values = new Map();

  return {
    getItem: vi.fn((key) => values.get(key) ?? null),
    setItem: vi.fn((key, value) => values.set(key, value)),
    removeItem: vi.fn((key) => values.delete(key)),
  };
}

describe("founder session storage", () => {
  test("saves, reads, and clears a session", () => {
    const storage = memoryStorage();
    const session = { access: "access-token", refresh: "refresh-token" };

    saveSession(session, storage);
    expect(getSession(storage)).toEqual(session);

    clearSession(storage);
    expect(getSession(storage)).toBeNull();
  });

  test("returns null for malformed stored JSON", () => {
    const storage = {
      getItem: () => "{not-json",
    };

    expect(getSession(storage)).toBeNull();
  });

  test("expiry clears storage and emits the session event", () => {
    const storage = memoryStorage();
    saveSession({ access: "token" }, storage);

    const events = [];
    class FakeEvent {
      constructor(type) {
        this.type = type;
      }
    }
    const target = {
      Event: FakeEvent,
      dispatchEvent: vi.fn((event) => events.push(event.type)),
    };

    expireSession(storage, target);

    expect(getSession(storage)).toBeNull();
    expect(events).toEqual([SESSION_EXPIRED_EVENT]);
  });
});

describe("environment-safe platform links", () => {
  test("uses a same-origin API path by default", () => {
    expect(apiRoot).toBe("/api/v1");
  });

  test("builds stable admin and API documentation URLs", () => {
    expect(new URL(adminUrl).pathname).toBe("/admin/");
    expect(new URL(apiDocsUrl).pathname).toBe("/api/docs/");
    expect(buildPlatformUrl("/admin/")).toBe(adminUrl);
  });
});
