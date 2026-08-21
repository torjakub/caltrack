import { useCallback, useState } from "react";
import { useFocusEffect, useRouter } from "expo-router";
import { ActivityIndicator, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors } from "../constants/theme";
import { listUnresolvedConflicts } from "../db/repo/conflicts";
import type { StagedConflict } from "../db/repo/conflicts";
import { resolveConflict } from "../lib/sync";

const HIDDEN_FIELDS = new Set(["id", "user_id"]);

export default function ConflictsScreen() {
  const router = useRouter();
  const [conflicts, setConflicts] = useState<StagedConflict[]>([]);
  const [loading, setLoading] = useState(true);
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setConflicts(await listUnresolvedConflicts());
    setLoading(false);
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  async function handleResolve(conflict: StagedConflict, resolution: "mine" | "theirs") {
    setResolvingId(conflict.id);
    try {
      await resolveConflict(conflict, resolution);
      await load();
    } finally {
      setResolvingId(null);
    }
  }

  if (loading) {
    return (
      <SafeAreaView style={styles.flex}>
        <View style={styles.center}>
          <ActivityIndicator />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.flex} edges={["bottom"]}>
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>Sync conflicts</Text>
          <TouchableOpacity onPress={() => router.back()}>
            <Text style={styles.link}>Close</Text>
          </TouchableOpacity>
        </View>

        {conflicts.length === 0 && (
          <Text style={styles.hint}>No conflicts — everything's in sync.</Text>
        )}

        {conflicts.map((conflict) => (
          <ConflictCard
            key={conflict.id}
            conflict={conflict}
            resolving={resolvingId === conflict.id}
            onResolve={(resolution) => handleResolve(conflict, resolution)}
          />
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

function ConflictCard({
  conflict,
  resolving,
  onResolve,
}: {
  conflict: StagedConflict;
  resolving: boolean;
  onResolve: (resolution: "mine" | "theirs") => void;
}) {
  const allFields = Array.from(new Set([...Object.keys(conflict.mine), ...Object.keys(conflict.theirs)])).filter(
    (f) => !HIDDEN_FIELDS.has(f)
  );
  const changedFields = allFields.filter(
    (f) => JSON.stringify(conflict.mine[f]) !== JSON.stringify(conflict.theirs[f])
  );

  return (
    <View style={styles.card}>
      <Text style={styles.entityLabel}>{conflict.entityType.replace("_", " ")}</Text>
      <Text style={styles.hint}>This was edited on two devices before they could sync.</Text>

      <View style={styles.diffTable}>
        <View style={styles.diffRow}>
          <Text style={[styles.diffCell, styles.diffHeader]}> </Text>
          <Text style={[styles.diffCell, styles.diffHeader]}>This device</Text>
          <Text style={[styles.diffCell, styles.diffHeader]}>Server</Text>
        </View>
        {changedFields.map((field) => (
          <View key={field} style={styles.diffRow}>
            <Text style={[styles.diffCell, styles.fieldName]}>{field}</Text>
            <Text style={[styles.diffCell, styles.mineValue]}>{formatValue(conflict.mine[field])}</Text>
            <Text style={[styles.diffCell, styles.theirsValue]}>{formatValue(conflict.theirs[field])}</Text>
          </View>
        ))}
      </View>

      <View style={styles.actionsRow}>
        <TouchableOpacity
          style={[styles.button, styles.mineButton]}
          onPress={() => onResolve("mine")}
          disabled={resolving}
        >
          <Text style={styles.buttonText}>Keep this device's version</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.button, styles.theirsButton]}
          onPress={() => onResolve("theirs")}
          disabled={resolving}
        >
          <Text style={styles.buttonText}>Keep server's version</Text>
        </TouchableOpacity>
      </View>
      {resolving && <ActivityIndicator style={{ marginTop: 8 }} />}
    </View>
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  return String(value);
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  container: { padding: 16, gap: 16 },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  title: { color: colors.text, fontSize: 20, fontWeight: "700" },
  link: { color: colors.primary },
  hint: { color: colors.textMuted, fontSize: 13 },
  card: { backgroundColor: colors.card, borderRadius: 12, padding: 16, gap: 8 },
  entityLabel: { color: colors.text, fontWeight: "700", fontSize: 16, textTransform: "capitalize" },
  diffTable: { marginTop: 8, gap: 2 },
  diffRow: { flexDirection: "row", gap: 4 },
  diffCell: { flex: 1, fontSize: 13, color: colors.text, paddingVertical: 4 },
  diffHeader: { color: colors.textMuted, fontWeight: "700", fontSize: 12 },
  fieldName: { color: colors.textMuted, flex: 0.8 },
  mineValue: { color: colors.primary, fontWeight: "600" },
  theirsValue: { color: colors.text },
  actionsRow: { flexDirection: "row", gap: 8, marginTop: 8 },
  button: { flex: 1, borderRadius: 8, padding: 12, alignItems: "center" },
  mineButton: { backgroundColor: colors.primary },
  theirsButton: { backgroundColor: colors.border },
  buttonText: { color: colors.primaryText, fontWeight: "700", fontSize: 12, textAlign: "center" },
});
