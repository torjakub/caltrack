import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import * as Device from "expo-device";
import { colors } from "../../constants/theme";
import { useSessionStore } from "../../store/session";
import { useIsOnline } from "../../hooks/useIsOnline";

export default function SettingsScreen() {
  const serverBaseUrl = useSessionStore((s) => s.serverBaseUrl);
  const deviceId = useSessionStore((s) => s.deviceId);
  const logout = useSessionStore((s) => s.logout);
  const isOnline = useIsOnline();

  return (
    <SafeAreaView style={styles.flex} edges={["bottom"]}>
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.card}>
          <Row label="Server" value={serverBaseUrl ?? "—"} />
          <Row label="Device" value={Device.deviceName ?? "Unknown device"} />
          <Row label="Device ID" value={deviceId.slice(0, 8) + "…"} />
          <Row label="Connectivity" value={isOnline ? "Online" : "Offline"} />
        </View>

        <Text style={styles.hint}>
          Sync with the server isn't built yet — everything logged here stays on this device for now.
        </Text>

        <TouchableOpacity style={styles.button} onPress={logout}>
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
  card: { backgroundColor: colors.card, borderRadius: 12, padding: 16, gap: 4 },
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
  button: { backgroundColor: colors.card, borderWidth: 1, borderColor: colors.error, borderRadius: 8, padding: 14, alignItems: "center" },
  buttonText: { color: colors.error, fontWeight: "700" },
});
