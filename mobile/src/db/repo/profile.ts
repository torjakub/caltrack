import { desc, eq } from "drizzle-orm";
import { db } from "../client";
import { userProfile, userTargets } from "../schema";
import type { UserProfileOut, UserTargetsOut } from "../../api/types";

export async function upsertProfileLocal(remote: UserProfileOut): Promise<void> {
  const existing = await db.select().from(userProfile).where(eq(userProfile.userId, remote.user_id)).limit(1);
  const row = {
    userId: remote.user_id,
    displayName: remote.display_name,
    dateOfBirth: remote.date_of_birth,
    sex: remote.sex,
    heightCm: remote.height_cm,
    weightKg: remote.weight_kg,
    activityLevel: remote.activity_level,
    goal: remote.goal,
    weeklyGoalRateKg: remote.weekly_goal_rate_kg,
    timezone: remote.timezone,
    updatedAt: remote.updated_at,
  };
  if (existing.length > 0) {
    await db.update(userProfile).set(row).where(eq(userProfile.userId, remote.user_id));
  } else {
    await db.insert(userProfile).values({ id: remote.id, ...row });
  }
}

export async function getProfileLocal(userId: string): Promise<UserProfileOut | null> {
  const [row] = await db.select().from(userProfile).where(eq(userProfile.userId, userId)).limit(1);
  if (!row) return null;
  return {
    id: row.id,
    user_id: row.userId,
    display_name: row.displayName,
    date_of_birth: row.dateOfBirth,
    sex: row.sex as UserProfileOut["sex"],
    height_cm: row.heightCm,
    weight_kg: row.weightKg,
    activity_level: row.activityLevel as UserProfileOut["activity_level"],
    goal: row.goal as UserProfileOut["goal"],
    weekly_goal_rate_kg: row.weeklyGoalRateKg,
    timezone: row.timezone,
    updated_at: row.updatedAt,
  };
}

export async function upsertTargetsLocal(remote: UserTargetsOut): Promise<void> {
  const existing = await db.select().from(userTargets).where(eq(userTargets.id, remote.id)).limit(1);
  const row = {
    userId: remote.user_id,
    effectiveDate: remote.effective_date,
    caloriesKcal: remote.calories_kcal,
    proteinG: remote.protein_g,
    carbsG: remote.carbs_g,
    fatG: remote.fat_g,
    fiberG: remote.fiber_g,
    source: remote.source,
    updatedAt: remote.updated_at,
  };
  if (existing.length > 0) {
    await db.update(userTargets).set(row).where(eq(userTargets.id, remote.id));
  } else {
    await db.insert(userTargets).values({ id: remote.id, ...row });
  }
}

export async function getActiveTargetsLocal(userId: string): Promise<UserTargetsOut | null> {
  const today = new Date().toISOString().slice(0, 10);
  const rows = await db
    .select()
    .from(userTargets)
    .where(eq(userTargets.userId, userId))
    .orderBy(desc(userTargets.effectiveDate), desc(userTargets.updatedAt));
  const active = rows.find((r) => r.effectiveDate <= today);
  if (!active) return null;
  return {
    id: active.id,
    user_id: active.userId,
    effective_date: active.effectiveDate,
    calories_kcal: active.caloriesKcal,
    protein_g: active.proteinG,
    carbs_g: active.carbsG,
    fat_g: active.fatG,
    fiber_g: active.fiberG,
    source: active.source as UserTargetsOut["source"],
    updated_at: active.updatedAt,
  };
}
