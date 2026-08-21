import { useCallback, useEffect, useState } from "react";
import { useFocusEffect } from "expo-router";
import { ActivityIndicator, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors } from "../../constants/theme";
import { useSessionStore } from "../../store/session";
import { useIsOnline } from "../../hooks/useIsOnline";
import { todayInTimezone } from "../../lib/dates";
import { computeDailyTotals, deleteLogEntryLocal, listLogsForDate } from "../../db/repo/logs";
import { getActiveTargetsLocal } from "../../db/repo/profile";
import { getLlmStatus, analysisDaily, mealReview } from "../../api/llm";
import type { MealInsight, PeriodAnalysis } from "../../api/llm";
import { runSync } from "../../lib/sync";
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
  const [llmAvailable, setLlmAvailable] = useState(false);

  useEffect(() => {
    if (!isOnline) return;
    getLlmStatus()
      .then((s) => setLlmAvailable(s.available))
      .catch(() => setLlmAvailable(false));
  }, [isOnline]);

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
            {llmAvailable && <DailyAnalysisSection date={date} />}
          </>
        }
        renderItem={({ item: meal }) => (
          <View style={styles.mealSection}>
            <Text style={styles.mealTitle}>{MEAL_LABELS[meal]}</Text>
            {entriesByMeal[meal].length === 0 && <Text style={styles.hint}>Nothing logged</Text>}
            {entriesByMeal[meal].map((entry) => (
              <View key={entry.id} style={styles.entryCard}>
                <View style={styles.entryRow}>
                  <Text style={styles.entryText}>
                    {entry.food?.name ?? entry.recipe_name ?? "Unknown"}
                    {entry.quantity_g != null ? ` — ${entry.quantity_g}g` : ""}
                  </Text>
                  <TouchableOpacity onPress={() => handleDelete(entry.id)}>
                    <Text style={styles.removeText}>Remove</Text>
                  </TouchableOpacity>
                </View>
                {llmAvailable && <MealReviewButton logEntryId={entry.id} />}
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

function DailyAnalysisSection({ date }: { date: string }) {
  const [analysis, setAnalysis] = useState<PeriodAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze() {
    setLoading(true);
    setError(null);
    try {
      // The LLM endpoints only see server-side data — this device's own
      // entries may still be local-only, so sync first or the analysis
      // would silently miss whatever hasn't been pushed yet.
      await runSync();
      setAnalysis(await analysisDaily(date));
    } catch {
      setError("Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Daily analysis</Text>
      {!analysis && (
        <TouchableOpacity style={styles.smallButton} onPress={handleAnalyze} disabled={loading}>
          {loading ? <ActivityIndicator color={colors.primaryText} /> : <Text style={styles.smallButtonText}>Analyze today</Text>}
        </TouchableOpacity>
      )}
      {error && <Text style={styles.errorText}>{error}</Text>}
      {analysis && (
        <>
          <Text style={styles.entryText}>{analysis.summary}</Text>
          {analysis.suggestions.map((s, i) => (
            <Text key={i} style={styles.hint}>
              • {s.food}: {s.reason}
            </Text>
          ))}
        </>
      )}
    </View>
  );
}

function MealReviewButton({ logEntryId }: { logEntryId: string }) {
  const [insight, setInsight] = useState<MealInsight | null>(null);
  const [loading, setLoading] = useState(false);
  const [shown, setShown] = useState(false);

  async function handlePress() {
    setShown(true);
    if (insight) return;
    setLoading(true);
    try {
      // Same reasoning as DailyAnalysisSection — this entry may only exist
      // locally so far.
      await runSync();
      setInsight(await mealReview(logEntryId));
    } catch {
      setInsight({ summary: "Review failed.", positives: [], concerns: [], suggestions: [] });
    } finally {
      setLoading(false);
    }
  }

  return (
    <View>
      <TouchableOpacity onPress={handlePress}>
        <Text style={styles.reviewLink}>Review</Text>
      </TouchableOpacity>
      {shown && (loading ? <ActivityIndicator /> : <Text style={styles.hint}>{insight?.summary}</Text>)}
    </View>
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
  entryCard: {
    backgroundColor: colors.card,
    borderRadius: 8,
    padding: 10,
    marginBottom: 6,
    gap: 4,
  },
  entryRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  entryText: { color: colors.text, flex: 1 },
  removeText: { color: colors.primary },
  offlineBanner: { backgroundColor: "#4a3c1a", padding: 8 },
  offlineText: { color: "#e0c26a", fontSize: 12, textAlign: "center" },
  cardTitle: { color: colors.text, fontWeight: "700", marginBottom: 4 },
  smallButton: { backgroundColor: colors.primary, borderRadius: 8, padding: 10, alignItems: "center" },
  smallButtonText: { color: colors.primaryText, fontWeight: "700", fontSize: 13 },
  errorText: { color: colors.error, fontSize: 13 },
  reviewLink: { color: colors.primary, fontSize: 13, fontWeight: "600" },
});
