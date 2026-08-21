import { useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { Stack } from "expo-router";
import { useMigrations } from "drizzle-orm/expo-sqlite/migrator";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { db } from "../db/client";
import migrations from "../db/migrations/migrations";
import { seedNutrientReference } from "../db/seed";
import { useSessionStore } from "../store/session";

export default function RootLayout() {
  const { success: migrationsDone, error: migrationError } = useMigrations(db, migrations);
  const [seeded, setSeeded] = useState(false);
  const hydrate = useSessionStore((s) => s.hydrate);
  const hydrated = useSessionStore((s) => s.hydrated);

  useEffect(() => {
    if (!migrationsDone) return;
    seedNutrientReference()
      .then(() => hydrate())
      .then(() => setSeeded(true));
  }, [migrationsDone, hydrate]);

  if (migrationError) {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>Database setup failed: {migrationError.message}</Text>
      </View>
    );
  }

  if (!migrationsDone || !seeded || !hydrated) {
    return (
      <View style={styles.center}>
        <ActivityIndicator />
      </View>
    );
  }

  // Screens themselves redirect based on isAuthenticated (see (tabs)/_layout.tsx
  // and login.tsx) — conditionally omitting Stack.Screen entries here doesn't
  // reliably block navigation to an already-resolved route.
  return (
    <SafeAreaProvider>
      <Stack screenOptions={{ headerShown: false }} />
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  error: { color: "#c0392b", padding: 24, textAlign: "center" },
});
