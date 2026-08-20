import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import * as profileApi from "../api/profile";
import type { UserProfileOut, UserTargetsOut, ActivityLevel, Goal, Sex } from "../api/types";
import { ApiError } from "../api/client";

export function ProfilePage() {
  const [profile, setProfile] = useState<UserProfileOut | null>(null);
  const [targets, setTargets] = useState<UserTargetsOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    try {
      setProfile(await profileApi.getProfile());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load profile");
    }
    try {
      setTargets(await profileApi.getTargets());
    } catch {
      setTargets(null);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!profile) return;
    setError(null);
    setMessage(null);
    try {
      const updated = await profileApi.updateProfile({
        display_name: profile.display_name,
        date_of_birth: profile.date_of_birth,
        sex: profile.sex,
        height_cm: profile.height_cm,
        weight_kg: profile.weight_kg,
        activity_level: profile.activity_level,
        goal: profile.goal,
        weekly_goal_rate_kg: profile.weekly_goal_rate_kg,
        timezone: profile.timezone,
      });
      setProfile(updated);
      setMessage("Profile saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save profile");
    }
  }

  async function handleRecalculate() {
    setError(null);
    setMessage(null);
    try {
      setTargets(await profileApi.recalculateTargets());
      setMessage("Targets recalculated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to recalculate targets");
    }
  }

  if (!profile) return <div className="page">{error ? <p className="error">{error}</p> : "Loading…"}</div>;

  return (
    <div className="page">
      <h2>Profile</h2>
      <form onSubmit={handleSubmit} className="profile-form">
        <label>
          Sex
          <select
            value={profile.sex ?? ""}
            onChange={(e) => setProfile({ ...profile, sex: (e.target.value || null) as Sex | null })}
          >
            <option value="">—</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
          </select>
        </label>
        <label>
          Date of birth
          <input
            type="date"
            value={profile.date_of_birth ?? ""}
            onChange={(e) => setProfile({ ...profile, date_of_birth: e.target.value || null })}
          />
        </label>
        <label>
          Height (cm)
          <input
            type="number"
            value={profile.height_cm ?? ""}
            onChange={(e) =>
              setProfile({ ...profile, height_cm: e.target.value ? Number(e.target.value) : null })
            }
          />
        </label>
        <label>
          Weight (kg)
          <input
            type="number"
            value={profile.weight_kg ?? ""}
            onChange={(e) =>
              setProfile({ ...profile, weight_kg: e.target.value ? Number(e.target.value) : null })
            }
          />
        </label>
        <label>
          Activity level
          <select
            value={profile.activity_level ?? ""}
            onChange={(e) =>
              setProfile({ ...profile, activity_level: (e.target.value || null) as ActivityLevel | null })
            }
          >
            <option value="">—</option>
            <option value="sedentary">Sedentary</option>
            <option value="light">Light</option>
            <option value="moderate">Moderate</option>
            <option value="active">Active</option>
            <option value="very_active">Very active</option>
          </select>
        </label>
        <label>
          Goal
          <select
            value={profile.goal ?? ""}
            onChange={(e) => setProfile({ ...profile, goal: (e.target.value || null) as Goal | null })}
          >
            <option value="">—</option>
            <option value="lose">Lose weight</option>
            <option value="maintain">Maintain</option>
            <option value="gain">Gain weight</option>
          </select>
        </label>
        <label>
          Timezone (IANA name)
          <input
            value={profile.timezone}
            onChange={(e) => setProfile({ ...profile, timezone: e.target.value })}
          />
        </label>
        {error && <p className="error">{error}</p>}
        {message && <p className="success">{message}</p>}
        <button type="submit">Save profile</button>
      </form>

      <div className="targets-card">
        <h3>Daily targets</h3>
        {targets ? (
          <ul>
            <li>Calories: {targets.calories_kcal} kcal</li>
            <li>Protein: {targets.protein_g} g</li>
            <li>Carbs: {targets.carbs_g} g</li>
            <li>Fat: {targets.fat_g} g</li>
            <li className="hint">Source: {targets.source}</li>
          </ul>
        ) : (
          <p className="hint">No targets set yet.</p>
        )}
        <button onClick={handleRecalculate}>Recalculate from profile</button>
      </div>
    </div>
  );
}
