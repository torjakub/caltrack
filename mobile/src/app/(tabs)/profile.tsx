import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { ActivityIndicator, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors } from "../../constants/theme";
import { useSessionStore } from "../../store/session";
import { useIsOnline } from "../../hooks/useIsOnline";
import { bootstrapAfterLogin } from "../../lib/bootstrap";
import { getActiveTargetsLocal, getProfileLocal } from "../../db/repo/profile";
import type { UserProfileOut, UserTargetsOut } from "../../api/types";

export default function ProfileScreen() {
  const userId = useSessionStore((s) => s.userId);
  const isOnline = useIsOnline();
  const [profile, setProfile] = useState<UserProfileOut | null>(null);
  const [targets, setTargets] = useState<UserTargetsOut | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    if (!userId) return;
    setProfile(await getProfileLocal(userId));
    setTargets(await getActiveTargetsLocal(userId));
  }, [userId]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  async function handleRefresh() {
    if (!isOnline) return;
    setRefreshing(true);
    try {
      await bootstrapAfterLogin();
      await load();
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <SafeAreaView style={styles.flex} edges={["bottom"]}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.hint}>
          Profile is edited from the web app for now — this screen mirrors the last synced data.
        </Text>

        <View style={styles.card}>
          <Row label="Sex" value={profile?.sex ?? "—"} />
          <Row label="Height" value={profile?.height_cm ? `${profile.height_cm} cm` : "—"} />
          <Row label="Weight" value={profile?.weight_kg ? `${profile.weight_kg} kg` : "—"} />
          <Row label="Activity" value={profile?.activity_level ?? "—"} />
          <Row label="Goal" value={profile?.goal ?? "—"} />
          <Row label="Timezone" value={profile?.timezone ?? "—"} />
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Daily targets</Text>
          {targets ? (
            <>
              <Row label="Calories" value={`${targets.calories_kcal} kcal`} />
              <Row label="Protein" value={`${targets.protein_g} g`} />
              <Row label="Carbs" value={`${targets.carbs_g} g`} />
              <Row label="Fat" value={`${targets.fat_g} g`} />
            </>
          ) : (
            <Text style={styles.hint}>No targets set yet.</Text>
          )}
        </View>

        <TouchableOpacity
          style={[styles.button, !isOnline && styles.buttonDisabled]}
          onPress={handleRefresh}
          disabled={!isOnline || refreshing}
        >
          {refreshing ? (
            <ActivityIndicator color={colors.primaryText} />
          ) : (
            <Text style={styles.buttonText}>{isOnline ? "Refresh from server" : "Offline"}</Text>
          )}
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
  hint: { color: colors.textMuted, fontSize: 12 },
  card: { backgroundColor: colors.card, borderRadius: 12, padding: 16, gap: 4 },
  cardTitle: { color: colors.text, fontWeight: "700", marginBottom: 4 },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 4,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  rowLabel: { color: colors.textMuted },
  rowValue: { color: colors.text, fontWeight: "600" },
  button: { backgroundColor: colors.primary, borderRadius: 8, padding: 14, alignItems: "center" },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: colors.primaryText, fontWeight: "700" },
});
