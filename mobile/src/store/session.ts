import { eq } from "drizzle-orm";
import { create } from "zustand";
import { db } from "../db/client";
import { localMeta } from "../db/schema";
import { newUuid } from "../lib/uuid";
import { getToken, setRefreshToken, setToken } from "../api/client";

interface SessionState {
  hydrated: boolean;
  deviceId: string;
  userId: string | null;
  serverBaseUrl: string | null;
  timezone: string;
  isAuthenticated: boolean;
  hydrate: () => Promise<void>;
  setServerBaseUrl: (url: string) => Promise<void>;
  setLoggedIn: (params: {
    userId: string;
    accessToken: string;
    refreshToken?: string;
    timezone?: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
}

async function getOrCreateLocalMeta() {
  const rows = await db.select().from(localMeta).where(eq(localMeta.id, 1)).limit(1);
  if (rows.length > 0) return rows[0];

  const inserted = await db
    .insert(localMeta)
    .values({ id: 1, deviceId: newUuid(), timezone: "UTC" })
    .returning();
  return inserted[0];
}

export const useSessionStore = create<SessionState>((set, get) => ({
  hydrated: false,
  deviceId: "",
  userId: null,
  serverBaseUrl: null,
  timezone: "UTC",
  isAuthenticated: false,

  hydrate: async () => {
    const meta = await getOrCreateLocalMeta();
    const token = await getToken();
    set({
      hydrated: true,
      deviceId: meta.deviceId,
      userId: meta.userId ?? null,
      serverBaseUrl: meta.serverBaseUrl ?? null,
      timezone: meta.timezone ?? "UTC",
      isAuthenticated: !!token && !!meta.userId,
    });
  },

  setServerBaseUrl: async (url: string) => {
    await db.update(localMeta).set({ serverBaseUrl: url }).where(eq(localMeta.id, 1));
    set({ serverBaseUrl: url });
  },

  setLoggedIn: async ({ userId, accessToken, refreshToken, timezone }) => {
    await setToken(accessToken);
    if (refreshToken) await setRefreshToken(refreshToken);
    await db
      .update(localMeta)
      .set({ userId, ...(timezone ? { timezone } : {}) })
      .where(eq(localMeta.id, 1));
    set({ userId, isAuthenticated: true, ...(timezone ? { timezone } : {}) });
  },

  logout: async () => {
    await setToken(null);
    await setRefreshToken(null);
    await db.update(localMeta).set({ userId: null }).where(eq(localMeta.id, 1));
    set({ userId: null, isAuthenticated: false });
  },
}));

export function getDeviceId(): string {
  return useSessionStore.getState().deviceId;
}
