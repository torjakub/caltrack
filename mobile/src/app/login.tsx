import { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { Redirect } from "expo-router";
import * as authApi from "../api/auth";
import { ApiError } from "../api/client";
import { bootstrapAfterLogin } from "../lib/bootstrap";
import { useSessionStore } from "../store/session";

export default function LoginScreen() {
  const serverBaseUrl = useSessionStore((s) => s.serverBaseUrl);
  const setServerBaseUrl = useSessionStore((s) => s.setServerBaseUrl);
  const setLoggedIn = useSessionStore((s) => s.setLoggedIn);
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);

  const [serverUrlInput, setServerUrlInput] = useState(serverBaseUrl ?? "");
  const [mode, setMode] = useState<"login" | "setup">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Redirect href="/" />;
  }

  const serverConfigured = !!serverBaseUrl;

  async function handleConnect() {
    let normalized = serverUrlInput.trim().replace(/\/$/, "");
    if (!normalized) return;
    if (!/^https?:\/\//i.test(normalized)) normalized = `http://${normalized}`;
    if (!/:\d+$/.test(normalized)) normalized = `${normalized}:8000`;
    await setServerBaseUrl(normalized);
  }

  async function handleSubmit() {
    setError(null);
    if (mode === "setup") {
      if (username.trim().length < 3) {
        setError("Username must be at least 3 characters.");
        return;
      }
      if (password.length < 8) {
        setError("Password must be at least 8 characters.");
        return;
      }
    }
    setSubmitting(true);
    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const tokens =
        mode === "login"
          ? await authApi.login(username, password)
          : await authApi.setup(username, password, timezone);
      const userId = authApi.decodeUserIdFromToken(tokens.access_token);
      await setLoggedIn({ userId, accessToken: tokens.access_token, timezone });
      await bootstrapAfterLogin();
    } catch (err) {
      if (err instanceof ApiError && mode === "setup" && err.status === 403) {
        setError("Setup already completed — switch to Log in below.");
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Could not reach the server. Check the server address.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>calTrack</Text>

        {!serverConfigured ? (
          <View style={styles.card}>
            <Text style={styles.label}>Server address</Text>
            <TextInput
              style={styles.input}
              placeholder="http://192.168.1.50:8000"
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
              value={serverUrlInput}
              onChangeText={setServerUrlInput}
            />
            <Text style={styles.hint}>Your home server's LAN address, e.g. from the Pi.</Text>
            <TouchableOpacity style={styles.button} onPress={handleConnect}>
              <Text style={styles.buttonText}>Continue</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.card}>
            <Text style={styles.hint}>Server: {serverBaseUrl}</Text>
            <TouchableOpacity onPress={() => setServerBaseUrl("")}>
              <Text style={styles.link}>Change server</Text>
            </TouchableOpacity>

            <View style={styles.tabs}>
              <TouchableOpacity
                style={[styles.tab, mode === "login" && styles.tabActive]}
                onPress={() => setMode("login")}
              >
                <Text style={mode === "login" ? styles.tabTextActive : styles.tabText}>Log in</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.tab, mode === "setup" && styles.tabActive]}
                onPress={() => setMode("setup")}
              >
                <Text style={mode === "setup" ? styles.tabTextActive : styles.tabText}>
                  First-time setup
                </Text>
              </TouchableOpacity>
            </View>

            <Text style={styles.label}>Username</Text>
            <TextInput
              style={styles.input}
              autoCapitalize="none"
              autoCorrect={false}
              value={username}
              onChangeText={setUsername}
            />
            <Text style={styles.label}>Password</Text>
            <TextInput
              style={styles.input}
              secureTextEntry
              value={password}
              onChangeText={setPassword}
            />

            {error && <Text style={styles.error}>{error}</Text>}

            <TouchableOpacity style={styles.button} onPress={handleSubmit} disabled={submitting}>
              {submitting ? (
                <ActivityIndicator color="#0b120d" />
              ) : (
                <Text style={styles.buttonText}>{mode === "login" ? "Log in" : "Create account"}</Text>
              )}
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: "#14171a" },
  container: { flexGrow: 1, justifyContent: "center", padding: 24 },
  title: { fontSize: 32, fontWeight: "700", color: "#eef2ee", textAlign: "center", marginBottom: 24 },
  card: { backgroundColor: "#1e2226", borderRadius: 12, padding: 20, gap: 12 },
  label: { color: "#9aa79d", fontSize: 13 },
  input: {
    backgroundColor: "#14171a",
    borderWidth: 1,
    borderColor: "#2c3238",
    borderRadius: 8,
    padding: 12,
    color: "#eef2ee",
  },
  hint: { color: "#9aa79d", fontSize: 12 },
  link: { color: "#4caf74", fontSize: 13 },
  button: {
    backgroundColor: "#4caf74",
    borderRadius: 8,
    padding: 14,
    alignItems: "center",
    marginTop: 8,
  },
  buttonText: { color: "#0b120d", fontWeight: "700" },
  tabs: { flexDirection: "row", gap: 8 },
  tab: {
    flex: 1,
    borderWidth: 1,
    borderColor: "#2c3238",
    borderRadius: 8,
    padding: 8,
    alignItems: "center",
  },
  tabActive: { borderColor: "#4caf74" },
  tabText: { color: "#9aa79d" },
  tabTextActive: { color: "#4caf74", fontWeight: "700" },
  error: { color: "#e57373", fontSize: 13 },
});
