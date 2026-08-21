import { useCallback, useState } from "react";
import { useFocusEffect, useRouter } from "expo-router";
import { ActivityIndicator, Alert, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { eq } from "drizzle-orm";
import * as Device from "expo-device";
import { colors } from "../../constants/theme";
import { useSessionStore } from "../../store/session";
import { useIsOnline } from "../../hooks/useIsOnline";
import { db } from "../../db/client";
import { localMeta } from "../../db/schema";
import { runSync } from "../../lib/sync";
import { listUnresolvedConflicts } from "../../db/repo/conflicts";
import { resetLocalData } from "../../db/repo/maintenance";

export default function SettingsScreen() {
  const router = useRouter();
  const serverBaseUrl = useSessionStore((s) => s.serverBaseUrl);
  const deviceId = useSessionStore((s) => s.deviceId);
  const logout = useSessionStore((s) => s.logout);
  const isOnline = useIsOnline();

  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);
  const [conflictCount, setConflictCount] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);

  const load = useCallback(async () => {
    const [meta] = await db.select().from(localMeta).where(eq(localMeta.id, 1)).limit(1);
    setLastSyncedAt(meta?.lastSyncedAt ?? null);
    setConflictCount((await listUnresolvedConflicts()).length);
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  async function handleSyncNow() {
    setSyncing(true);
    setSyncMessage(null);
    const result = await runSync();
    setSyncing(false);
    if (result.ok) {
      setSyncMessage(
        result.conflictCount > 0
          ? `Synced — ${result.conflictCount} conflict${result.conflictCount > 1 ? "s" : ""} need resolving.`
          : "Synced."
      );
    } else {
      setSyncMessage(result.error ?? "Sync failed.");
    }
    await load();
  }

  function handleResetLocalData() {
    Alert.alert(
      "Reset local data?",
      "Deletes all foods, logs, and recipes cached on this device, then re-downloads whatever belongs to your account from the server. Use this if local data ever gets out of sync with your account (e.g. after switching servers or accounts on this device).",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Reset",
          style: "destructive",
          onPress: async () => {
            setResetting(true);
            setSyncMessage(null);
            await resetLocalData();
            const result = await runSync();
            setResetting(false);
            setSyncMessage(result.ok ? "Local data reset and re-synced." : result.error ?? "Reset failed.");
            await load();
          },
        },
      ]
    );
  }

  return (
    <SafeAreaView style={styles.flex} edges={["bottom"]}>
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.card}>
          <Row label="Server" value={serverBaseUrl ?? "—"} />
          <Row label="Device" value={Device.deviceName ?? "Unknown device"} />
          <Row label="Device ID" value={deviceId.slice(0, 8) + "…"} />
          <Row label="Connectivity" value={isOnline ? "Online" : "Offline"} />
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Sync</Text>
          <Row label="Last synced" value={lastSyncedAt ? new Date(lastSyncedAt).toLocaleString() : "Never"} />
          {conflictCount > 0 && (
            <TouchableOpacity style={styles.conflictBanner} onPress={() => router.push("/conflicts")}>
              <Text style={styles.conflictBannerText}>
                {conflictCount} conflict{conflictCount > 1 ? "s" : ""} need resolving →
              </Text>
            </TouchableOpacity>
          )}
          {syncMessage && <Text style={styles.hint}>{syncMessage}</Text>}
          <TouchableOpacity
            style={[styles.button, styles.primaryButton, !isOnline && styles.buttonDisabled]}
            onPress={handleSyncNow}
            disabled={!isOnline || syncing}
          >
            {syncing ? (
              <ActivityIndicator color={colors.primaryText} />
            ) : (
              <Text style={styles.primaryButtonText}>{isOnline ? "Sync now" : "Offline"}</Text>
            )}
          </TouchableOpacity>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Danger zone</Text>
          <Text style={styles.hint}>
            If local data ever looks wrong or incomplete for your account, resetting clears the local
            cache and re-downloads everything fresh from the server.
          </Text>
          <TouchableOpacity
            style={[styles.button, styles.dangerButton, !isOnline && styles.buttonDisabled]}
            onPress={handleResetLocalData}
            disabled={!isOnline || resetting}
          >
            {resetting ? (
              <ActivityIndicator color={colors.error} />
            ) : (
              <Text style={styles.buttonText}>Reset local data</Text>
            )}
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={[styles.button, styles.logoutButton]} onPress={logout}>
          <Text style={styles.buttonText}>Log out</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  container: { padding: 16, gap: 16 },
  card: { backgroundColor: colors.card, borderRadius: 12, padding: 16, gap: 8 },
  cardTitle: { color: colors.text, fontWeight: "700" },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 4,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  rowLabel: { color: colors.textMuted },
  rowValue: { color: colors.text, fontWeight: "600" },
  hint: { color: colors.textMuted, fontSize: 12 },
  button: { borderRadius: 8, padding: 14, alignItems: "center" },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: colors.error, fontWeight: "700" },
  primaryButton: { backgroundColor: colors.primary },
  primaryButtonText: { color: colors.primaryText, fontWeight: "700" },
  logoutButton: { backgroundColor: colors.card, borderWidth: 1, borderColor: colors.error },
  dangerButton: { backgroundColor: colors.card, borderWidth: 1, borderColor: colors.error },
  conflictBanner: { backgroundColor: "#4a3c1a", borderRadius: 8, padding: 10 },
  conflictBannerText: { color: "#e0c26a", fontWeight: "600", fontSize: 13 },
});
