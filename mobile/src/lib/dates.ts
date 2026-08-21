// Mirrors server/app/routers/logs.py:_resolve_log_date and web's
// todayInTimezone — the calendar day a log belongs to (or "today") is
// resolved in the user's profile timezone, not the device's local zone or
// UTC, so day boundaries stay consistent across web/mobile/server.
export function resolveLogDate(loggedAt: Date, timezone: string): string {
  try {
    return new Intl.DateTimeFormat("en-CA", { timeZone: timezone }).format(loggedAt);
  } catch {
    return loggedAt.toISOString().slice(0, 10);
  }
}

export function todayInTimezone(timezone: string): string {
  return resolveLogDate(new Date(), timezone);
}
