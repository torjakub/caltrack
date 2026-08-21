import { Redirect, Tabs } from "expo-router";
import { Text } from "react-native";
import { colors } from "../../constants/theme";
import { useSessionStore } from "../../store/session";
import { useAutoSync } from "../../hooks/useAutoSync";

function Icon({ label, focused }: { label: string; focused: boolean }) {
  return <Text style={{ fontSize: 20, opacity: focused ? 1 : 0.5 }}>{label}</Text>;
}

export default function TabsLayout() {
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  useAutoSync();

  if (!isAuthenticated) {
    return <Redirect href="/login" />;
  }

  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: colors.card },
        headerTintColor: colors.text,
        tabBarStyle: { backgroundColor: colors.card, borderTopColor: colors.border },
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Dashboard",
          tabBarIcon: ({ focused }) => <Icon label="📊" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="log"
        options={{
          title: "Log food",
          tabBarIcon: ({ focused }) => <Icon label="➕" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Profile",
          tabBarIcon: ({ focused }) => <Icon label="👤" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: "Settings",
          tabBarIcon: ({ focused }) => <Icon label="⚙️" focused={focused} />,
        }}
      />
    </Tabs>
  );
}
