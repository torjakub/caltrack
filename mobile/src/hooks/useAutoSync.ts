import { useEffect, useRef } from "react";
import { AppState } from "react-native";
import NetInfo from "@react-native-community/netinfo";
import { useSessionStore } from "../store/session";
import { runSync } from "../lib/sync";

/** Syncs automatically when the app comes to the foreground or when
 * connectivity is regained after being offline — on top of the manual
 * "Sync now" button in Settings. Silent by design (errors just mean the
 * next trigger retries); this is a background convenience, not something
 * the user needs to babysit. */
export function useAutoSync(): void {
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  const wasOffline = useRef(false);

  useEffect(() => {
    if (!isAuthenticated) return;

    const appStateSub = AppState.addEventListener("change", (state) => {
      if (state === "active") runSync();
    });

    const netInfoUnsub = NetInfo.addEventListener((state) => {
      const isOnline = !!state.isConnected && state.isInternetReachable !== false;
      if (isOnline && wasOffline.current) runSync();
      wasOffline.current = !isOnline;
    });

    runSync();

    return () => {
      appStateSub.remove();
      netInfoUnsub();
    };
  }, [isAuthenticated]);
}
