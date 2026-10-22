import { API_URL } from './config';
import type { SkillScore } from './resume';

export type Stage = 'under' | 'fresh' | 'working';

/** Index of the "Which one sounds like you?" answer -> backend stage. */
export const stageForWho: Stage[] = ['under', 'fresh', 'working'];

export interface ExperienceEntry {
  title: string;
  organisation?: string | null;
  start?: string | null;
  end?: string | null;
  summary?: string | null;
}

export interface ProfileIn {
  email?: string | null;
  name: string;
  stage: Stage;
  concerns: string;
  skills: SkillScore[];
  experience: ExperienceEntry[];
}

export interface Profile extends ProfileIn {
  profile_id: string;
}

export async function createProfile(body: ProfileIn): Promise<Profile> {
  const res = await fetch(`${API_URL}/profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Profile request failed (${res.status})`);
  return res.json();
}

/** Thrown when the profile id no longer exists on the backend. */
export class ProfileNotFound extends Error {}

export async function updateProfile(id: string, body: Partial<Omit<ProfileIn, 'email'>>): Promise<Profile> {
  const res = await fetch(`${API_URL}/profile/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (res.status === 404) throw new ProfileNotFound(`No profile ${id}`);
  if (!res.ok) throw new Error(`Profile update failed (${res.status})`);
  return res.json();
}

export async function getProfile(id: string): Promise<Profile> {
  const res = await fetch(`${API_URL}/profile/${encodeURIComponent(id)}`);
  if (res.status === 404) throw new ProfileNotFound(`No profile ${id}`);
  if (!res.ok) throw new Error(`Profile request failed (${res.status})`);
  return res.json();
}

/** A failed email sync step, with a message that can be shown to the user as is. */
export class SyncError extends Error {}

async function syncPost(path: string, body: object, notFound?: string): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/profile/${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch {
    throw new SyncError('Couldn’t reach Jobee. Check your connection and try again.');
  }
  if (res.ok) return res;
  const detail = await res.json().then((b) => (typeof b?.detail === 'string' ? b.detail : null)).catch(() => null);
  if (res.status === 429) throw new SyncError('Too many tries. Wait a minute, then try again.');
  if (res.status === 404) throw new SyncError(notFound ?? detail ?? 'Jobee couldn’t find your profile. Go back and finish the questions again.');
  if (res.status === 409) throw new SyncError(detail ?? 'That email is already linked to another profile.');
  if (res.status === 400 || res.status === 422) throw new SyncError(detail ?? 'That didn’t work. Check it and try again.');
  throw new SyncError('Something went wrong. Try again in a moment.');
}

/** Step 1 of syncing an email: Supabase emails a one-time code. */
export async function sendSyncCode(profileId: string, email: string): Promise<void> {
  await syncPost('sync', { profile_id: profileId, email });
}

/** Step 2: confirm the code; the email is then saved on the profile. */
export async function verifySyncCode(profileId: string, email: string, token: string): Promise<Profile> {
  return (await syncPost('sync/verify', { profile_id: profileId, email, token })).json();
}

/** Step 1 of logging in: a one-time code is emailed if a profile is synced with that email. */
export async function sendLoginCode(email: string): Promise<void> {
  await syncPost('login', { email });
}

/** Step 2: confirm the code; the matching profile comes back. */
export async function verifyLoginCode(email: string, token: string): Promise<Profile> {
  return (await syncPost('login/verify', { email, token })).json();
}

const PROFILE_COOKIE = 'jobee_profile_id';
const ONE_YEAR = 60 * 60 * 24 * 365;

export function saveProfileId(id: string) {
  document.cookie = `${PROFILE_COOKIE}=${encodeURIComponent(id)}; Max-Age=${ONE_YEAR}; Path=/; SameSite=Lax`;
}

export function readProfileId(): string | null {
  const hit = document.cookie.split('; ').find((c) => c.startsWith(`${PROFILE_COOKIE}=`));
  return hit ? decodeURIComponent(hit.slice(PROFILE_COOKIE.length + 1)) : null;
}
