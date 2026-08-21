import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors } from "../../constants/theme";
import { useSessionStore } from "../../store/session";
import { useIsOnline } from "../../hooks/useIsOnline";
import { todayInTimezone } from "../../lib/dates";
import { computeDailyTotals, deleteLogEntryLocal, listLogsForDate } from "../../db/repo/logs";
import { getActiveTargetsLocal } from "../../db/repo/profile";
import type { LogEntryOut, MealType, NutrientTotals, UserTargetsOut } from "../../api/types";

const MEAL_LABELS: Record<MealType, string> = {
  breakfast: "Breakfast",
  lunch: "Lunch",
  dinner: "Dinner",
  snack: "Snack",
};
const MEAL_ORDER: MealType[] = ["breakfast", "lunch", "dinner", "snack"];

export default function DashboardScreen() {
  const userId = useSessionStore((s) => s.userId);
  const timezone = useSessionStore((s) => s.timezone);
  const isOnline = useIsOnline();

  const [date] = useState(() => todayInTimezone(timezone));
  const [entries, setEntries] = useState<LogEntryOut[]>([]);
  const [totals, setTotals] = useState<NutrientTotals | null>(null);
  const [targets, setTargets] = useState<UserTargetsOut | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    const logs = await listLogsForDate(userId, date);
    setEntries(logs);
    setTotals(await computeDailyTotals(logs));
    setTargets(await getActiveTargetsLocal(userId));
    setLoading(false);
  }, [userId, date]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  async function handleDelete(id: string) {
    await deleteLogEntryLocal(id);
    load();
  }

  const entriesByMeal: Record<MealType, LogEntryOut[]> = {
    breakfast: [],
    lunch: [],
    dinner: [],
    snack: [],
  };
  entries.forEach((e) => entriesByMeal[e.meal_type].push(e));

  return (
    <SafeAreaView style={styles.flex} edges={["bottom"]}>
      {!isOnline && (
        <View style={styles.offlineBanner}>
          <Text style={styles.offlineText}>Offline — logging locally, will sync when reconnected</Text>
        </View>
      )}
      <FlatList
        contentContainerStyle={styles.container}
        data={MEAL_ORDER}
        keyExtractor={(m) => m}
        ListHeaderComponent={
          <>
            <Text style={styles.dateLabel}>{date}</Text>
            {totals && (
              <View style={styles.card}>
                <TotalRow label="Calories" value={totals.calories_kcal} target={targets?.calories_kcal} unit="kcal" />
                <TotalRow label="Protein" value={totals.protein_g} target={targets?.protein_g} unit="g" />
                <TotalRow label="Carbs" value={totals.carbs_g} target={targets?.carbs_g} unit="g" />
                <TotalRow label="Fat" value={totals.fat_g} target={targets?.fat_g} unit="g" />
                {!targets && <Text style={styles.hint}>No targets yet — set them up on the web app.</Text>}
              </View>
            )}
          </>
        }
        renderItem={({ item: meal }) => (
          <View style={styles.mealSection}>
            <Text style={styles.mealTitle}>{MEAL_LABELS[meal]}</Text>
            {entriesByMeal[meal].length === 0 && <Text style={styles.hint}>Nothing logged</Text>}
            {entriesByMeal[meal].map((entry) => (
              <View key={entry.id} style={styles.entryRow}>
                <Text style={styles.entryText}>
                  {entry.food?.name ?? entry.recipe_name ?? "Unknown"}
                  {entry.quantity_g != null ? ` — ${entry.quantity_g}g` : ""}
                </Text>
                <TouchableOpacity onPress={() => handleDelete(entry.id)}>
                  <Text style={styles.removeText}>Remove</Text>
                </TouchableOpacity>
              </View>
            ))}
          </View>
        )}
        refreshing={loading}
        onRefresh={load}
      />
    </SafeAreaView>
  );
}

function TotalRow({ label, value, target, unit }: { label: string; value: number; target?: number; unit: string }) {
  return (
    <View style={styles.totalRow}>
      <Text style={styles.totalLabel}>{label}</Text>
      <Text style={styles.totalValue}>
        {Math.round(value)} {unit}
        {target != null ? ` / ${Math.round(target)} ${unit}` : ""}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  container: { padding: 16, gap: 8 },
  dateLabel: { color: colors.text, fontSize: 18, fontWeight: "700", marginBottom: 12 },
  card: { backgroundColor: colors.card, borderRadius: 12, padding: 16, marginBottom: 16, gap: 4 },
  totalRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 4,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  totalLabel: { color: colors.textMuted },
  totalValue: { color: colors.text, fontWeight: "600" },
  hint: { color: colors.textMuted, fontSize: 13 },
  mealSection: { marginBottom: 16 },
  mealTitle: { color: colors.text, fontWeight: "700", fontSize: 16, marginBottom: 6 },
  entryRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: colors.card,
    borderRadius: 8,
    padding: 10,
    marginBottom: 6,
  },
  entryText: { color: colors.text, flex: 1 },
  removeText: { color: colors.primary },
  offlineBanner: { backgroundColor: "#4a3c1a", padding: 8 },
  offlineText: { color: "#e0c26a", fontSize: 12, textAlign: "center" },
});
