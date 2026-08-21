import { useEffect, useState } from "react";
import { useRouter } from "expo-router";
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import * as ImagePicker from "expo-image-picker";
import { colors } from "../../constants/theme";
import { useSessionStore } from "../../store/session";
import { useIsOnline } from "../../hooks/useIsOnline";
import * as foodsApi from "../../api/foods";
import { getLlmStatus, ocrNutritionLabel } from "../../api/llm";
import { ApiError, NoServerConfiguredError } from "../../api/client";
import {
  cacheRemoteFood,
  createCustomFoodLocal,
  getFoodByBarcodeLocal,
  searchFoodsLocal,
} from "../../db/repo/foods";
import { createLogEntryLocal } from "../../db/repo/logs";
import type { FoodOut, MealType } from "../../api/types";

const MEALS: MealType[] = ["breakfast", "lunch", "dinner", "snack"];

export default function LogFoodScreen() {
  const router = useRouter();
  const userId = useSessionStore((s) => s.userId);
  const timezone = useSessionStore((s) => s.timezone);
  const isOnline = useIsOnline();

  const [query, setQuery] = useState("");
  const [barcode, setBarcode] = useState("");
  const [results, setResults] = useState<FoodOut[]>([]);
  const [selected, setSelected] = useState<FoodOut | null>(null);
  const [quantityG, setQuantityG] = useState("100");
  const [mealType, setMealType] = useState<MealType>("breakfast");
  const [error, setError] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const [showCustomForm, setShowCustomForm] = useState(false);

  if (!userId) {
    return (
      <SafeAreaView style={styles.flex} edges={["bottom"]}>
        <View style={styles.container}>
          <Text style={styles.hint}>Session not ready yet — pull to refresh or reopen the app.</Text>
        </View>
      </SafeAreaView>
    );
  }
  const activeUserId = userId;

  async function handleSearch() {
    if (!query.trim()) return;
    setError(null);
    setSearching(true);
    try {
      const local = await searchFoodsLocal(query.trim(), activeUserId);
      let combined = local;
      if (isOnline) {
        try {
          const remote = await foodsApi.searchFoodsRemote(query.trim());
          for (const food of remote) {
            await cacheRemoteFood(food);
          }
          const localIds = new Set(local.map((f) => f.id));
          combined = [...local, ...remote.filter((f) => !localIds.has(f.id))];
        } catch {
          // stay with local-only results if the remote call fails
        }
      }
      setResults(combined);
      if (combined.length === 0) {
        setError(isOnline ? "No results." : "No cached results — you're offline.");
      }
    } finally {
      setSearching(false);
    }
  }

  async function handleBarcodeSubmit() {
    if (!barcode.trim()) return;
    setError(null);
    setSearching(true);
    try {
      let food = await getFoodByBarcodeLocal(barcode.trim(), activeUserId);
      if (!food && isOnline) {
        try {
          food = await foodsApi.lookupBarcodeRemote(barcode.trim());
          await cacheRemoteFood(food);
        } catch (err) {
          if (err instanceof ApiError && err.status === 404) {
            setError("Product not found.");
          } else {
            setError("Lookup failed.");
          }
          return;
        }
      }
      if (!food) {
        setError(isOnline ? "Product not found." : "Not cached — you're offline.");
        return;
      }
      setSelected(food);
      setResults([]);
    } catch (err) {
      setError(err instanceof NoServerConfiguredError ? "No server configured." : "Lookup failed.");
    } finally {
      setSearching(false);
    }
  }

  async function handleLog() {
    if (!selected) return;
    const qty = Number(quantityG);
    if (!qty || qty <= 0) {
      setError("Enter a valid quantity.");
      return;
    }
    await createLogEntryLocal(
      { foodId: selected.id, quantityG: qty, mealType, loggedAt: new Date() },
      activeUserId,
      timezone
    );
    setSelected(null);
    setQuery("");
    setBarcode("");
    setQuantityG("100");
    router.navigate("/(tabs)");
  }

  if (selected) {
    return (
      <SafeAreaView style={styles.flex} edges={["bottom"]}>
        <View style={styles.container}>
          <Text style={styles.title}>{selected.name}</Text>
          {selected.nutrients && (
            <Text style={styles.hint}>
              {Math.round(selected.nutrients.calories_kcal)} kcal, {selected.nutrients.protein_g}g protein,{" "}
              {selected.nutrients.carbs_g}g carbs, {selected.nutrients.fat_g}g fat — per 100g
            </Text>
          )}
          <Text style={styles.label}>Quantity (g)</Text>
          <TextInput
            style={styles.input}
            keyboardType="numeric"
            value={quantityG}
            onChangeText={setQuantityG}
          />
          <Text style={styles.label}>Meal</Text>
          <View style={styles.mealRow}>
            {MEALS.map((m) => (
              <TouchableOpacity
                key={m}
                style={[styles.mealChip, mealType === m && styles.mealChipActive]}
                onPress={() => setMealType(m)}
              >
                <Text style={mealType === m ? styles.mealChipTextActive : styles.mealChipText}>{m}</Text>
              </TouchableOpacity>
            ))}
          </View>
          {error && <Text style={styles.error}>{error}</Text>}
          <View style={styles.actionsRow}>
            <TouchableOpacity style={styles.secondaryButton} onPress={() => setSelected(null)}>
              <Text style={styles.secondaryButtonText}>Back</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.button} onPress={handleLog}>
              <Text style={styles.buttonText}>Log it</Text>
            </TouchableOpacity>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.flex} edges={["bottom"]}>
      <FlatList
        contentContainerStyle={styles.container}
        data={results}
        keyExtractor={(f) => f.id}
        ListHeaderComponent={
          <>
            {!isOnline && <Text style={styles.offlineHint}>Offline — searching cached foods only.</Text>}
            <View style={styles.inlineForm}>
              <TextInput
                style={[styles.input, styles.flexInput]}
                placeholder="Search foods…"
                value={query}
                onChangeText={setQuery}
                onSubmitEditing={handleSearch}
              />
              <TouchableOpacity style={styles.button} onPress={handleSearch} disabled={searching}>
                <Text style={styles.buttonText}>Search</Text>
              </TouchableOpacity>
            </View>
            <View style={styles.inlineForm}>
              <TextInput
                style={[styles.input, styles.flexInput]}
                placeholder="Enter barcode…"
                keyboardType="numeric"
                value={barcode}
                onChangeText={setBarcode}
                onSubmitEditing={handleBarcodeSubmit}
              />
              <TouchableOpacity style={styles.button} onPress={handleBarcodeSubmit} disabled={searching}>
                <Text style={styles.buttonText}>Look up</Text>
              </TouchableOpacity>
            </View>
            {searching && <ActivityIndicator />}
            {error && <Text style={styles.error}>{error}</Text>}
            <TouchableOpacity onPress={() => setShowCustomForm((v) => !v)}>
              <Text style={styles.link}>{showCustomForm ? "Cancel" : "Can't find it? Add a custom food"}</Text>
            </TouchableOpacity>
            {showCustomForm && (
              <CustomFoodForm
                userId={activeUserId}
                onCreated={(food) => {
                  setSelected(food);
                  setShowCustomForm(false);
                }}
              />
            )}
          </>
        }
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.resultRow} onPress={() => setSelected(item)}>
            <Text style={styles.resultName}>{item.name}</Text>
            {item.brand && <Text style={styles.hint}>{item.brand}</Text>}
            {item.nutrients && (
              <Text style={styles.hint}>{Math.round(item.nutrients.calories_kcal)} kcal/100g</Text>
            )}
          </TouchableOpacity>
        )}
      />
    </SafeAreaView>
  );
}

function CustomFoodForm({ userId, onCreated }: { userId: string; onCreated: (food: FoodOut) => void }) {
  const [name, setName] = useState("");
  const [calories, setCalories] = useState("0");
  const [protein, setProtein] = useState("0");
  const [carbs, setCarbs] = useState("0");
  const [fat, setFat] = useState("0");
  const [llmAvailable, setLlmAvailable] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const isOnline = useIsOnline();

  useEffect(() => {
    if (!isOnline) return;
    getLlmStatus()
      .then((s) => setLlmAvailable(s.available))
      .catch(() => setLlmAvailable(false));
  }, [isOnline]);

  async function handleScanPhoto() {
    setScanError(null);
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      setScanError("Camera permission denied.");
      return;
    }
    const result = await ImagePicker.launchCameraAsync({ quality: 0.7 });
    if (result.canceled) return;

    setScanning(true);
    try {
      const parsed = await ocrNutritionLabel(result.assets[0].uri);
      if (parsed.name) setName(parsed.name);
      if (parsed.calories_kcal != null) setCalories(String(parsed.calories_kcal));
      if (parsed.protein_g != null) setProtein(String(parsed.protein_g));
      if (parsed.carbs_g != null) setCarbs(String(parsed.carbs_g));
      if (parsed.fat_g != null) setFat(String(parsed.fat_g));
    } catch {
      setScanError("Couldn't read that label — enter values manually.");
    } finally {
      setScanning(false);
    }
  }

  async function handleCreate() {
    if (!name.trim()) return;
    const food = await createCustomFoodLocal(
      {
        name: name.trim(),
        caloriesKcal: Number(calories) || 0,
        proteinG: Number(protein) || 0,
        carbsG: Number(carbs) || 0,
        fatG: Number(fat) || 0,
      },
      userId
    );
    onCreated(food);
  }

  return (
    <View style={styles.customCard}>
      {llmAvailable && (
        <TouchableOpacity style={styles.scanButton} onPress={handleScanPhoto} disabled={scanning}>
          {scanning ? (
            <ActivityIndicator color={colors.primaryText} />
          ) : (
            <Text style={styles.scanButtonText}>📷 Scan nutrition label</Text>
          )}
        </TouchableOpacity>
      )}
      {scanError && <Text style={styles.error}>{scanError}</Text>}
      <Text style={styles.label}>Name</Text>
      <TextInput style={styles.input} value={name} onChangeText={setName} />
      <Text style={styles.hint}>Nutrition values are per 100g</Text>
      <View style={styles.macroGrid}>
        <View style={styles.macroField}>
          <Text style={styles.label}>Calories</Text>
          <TextInput style={styles.input} keyboardType="numeric" value={calories} onChangeText={setCalories} />
        </View>
        <View style={styles.macroField}>
          <Text style={styles.label}>Protein (g)</Text>
          <TextInput style={styles.input} keyboardType="numeric" value={protein} onChangeText={setProtein} />
        </View>
        <View style={styles.macroField}>
          <Text style={styles.label}>Carbs (g)</Text>
          <TextInput style={styles.input} keyboardType="numeric" value={carbs} onChangeText={setCarbs} />
        </View>
        <View style={styles.macroField}>
          <Text style={styles.label}>Fat (g)</Text>
          <TextInput style={styles.input} keyboardType="numeric" value={fat} onChangeText={setFat} />
        </View>
      </View>
      <TouchableOpacity style={styles.button} onPress={handleCreate}>
        <Text style={styles.buttonText}>Create food</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.bg },
  container: { padding: 16, gap: 8 },
  title: { color: colors.text, fontSize: 20, fontWeight: "700" },
  label: { color: colors.textMuted, fontSize: 13, marginTop: 8 },
  hint: { color: colors.textMuted, fontSize: 12 },
  offlineHint: { color: "#e0c26a", fontSize: 12, marginBottom: 8 },
  input: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    padding: 10,
    color: colors.text,
  },
  flexInput: { flex: 1 },
  inlineForm: { flexDirection: "row", gap: 8, alignItems: "center", marginTop: 8 },
  button: { backgroundColor: colors.primary, borderRadius: 8, padding: 10, alignItems: "center" },
  buttonText: { color: colors.primaryText, fontWeight: "700" },
  secondaryButton: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    padding: 12,
    alignItems: "center",
  },
  secondaryButtonText: { color: colors.text, fontWeight: "600" },
  actionsRow: { flexDirection: "row", gap: 8, marginTop: 16 },
  error: { color: colors.error, fontSize: 13 },
  link: { color: colors.primary, marginTop: 12 },
  resultRow: {
    backgroundColor: colors.card,
    borderRadius: 8,
    padding: 12,
    marginBottom: 6,
  },
  resultName: { color: colors.text, fontWeight: "600" },
  mealRow: { flexDirection: "row", gap: 6, flexWrap: "wrap" },
  mealChip: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    paddingVertical: 6,
    paddingHorizontal: 12,
  },
  mealChipActive: { borderColor: colors.primary, backgroundColor: colors.primary },
  mealChipText: { color: colors.textMuted },
  mealChipTextActive: { color: colors.primaryText, fontWeight: "700" },
  customCard: {
    backgroundColor: colors.card,
    borderRadius: 12,
    padding: 12,
    marginTop: 8,
    gap: 4,
  },
  macroGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  scanButton: { backgroundColor: colors.primary, borderRadius: 8, padding: 10, alignItems: "center" },
  scanButtonText: { color: colors.primaryText, fontWeight: "700" },
  macroField: { width: "47%" },
});
