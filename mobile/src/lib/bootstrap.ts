import * as profileApi from "../api/profile";
import { upsertProfileLocal, upsertTargetsLocal } from "../db/repo/profile";

/** One-time pull after login — profile and targets so the app has something
 * to show immediately, even before the user is back online again. Recipes
 * and the full sync loop land in M4; this is deliberately minimal. */
export async function bootstrapAfterLogin(): Promise<void> {
  const profile = await profileApi.getProfile();
  await upsertProfileLocal(profile);

  try {
    const targets = await profileApi.getTargets();
    await upsertTargetsLocal(targets);
  } catch {
    // No targets calculated yet — fine, dashboard just won't show a target line.
  }
}
