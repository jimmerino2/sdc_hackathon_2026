import { API_URL } from './config';

export interface HiveMember {
  profile_id: string;
  name: string;
  bee: string;
  /** Stingers they have spent this round. */
  stings: number;
  is_me: boolean;
}

export interface HiveFight {
  fight_id: string;
  /** Robbee's HP, 100 down to 0; a kill resets it to 100. */
  hp: number;
  /** Rounds this party has won. */
  kills: number;
  /** Stings landed this round. */
  stings_dealt: number;
  /** Stings it takes to kill him from full HP. */
  stings_to_kill: number;
  max_party: number;
}

/** An invite to someone else's party. */
export interface HiveInvite {
  invite_id: string;
  from_name: string;
  from_bee: string;
  party_size: number;
  hp: number;
}

/** An invite the learner's party sent that hasn't been answered. */
export interface HiveOutgoing {
  invite_id: string;
  profile_id: string;
  name: string;
  bee: string;
}

/** A friend who can be invited. */
export interface HiveInvitable {
  profile_id: string;
  name: string;
  bee: string;
}

export interface HiveEvent {
  event_id: string;
  kind: 'sting' | 'twist' | 'defeat' | 'join' | 'leave';
  /** Who did it, to match the event to a bee in the party. */
  profile_id: string;
  name: string;
  is_me: boolean;
  challenge_title: string | null;
  /** Pollen it paid the actor; show it for the learner's own events. */
  pollen: number;
  created_at: string;
}

/** A kill the learner hasn't dismissed yet: its popup shows once. */
export interface HiveReward {
  reward_id: string;
  /** Kill pollen paid to the learner; 0 if they were in the party but didn't sting. */
  pollen: number;
  round: number;
  /** The party at the kill, one entry per member (1 to 4). */
  party: { name: string; bee: string }[];
}

export interface Hive {
  fight: HiveFight;
  /** The party, oldest member first. */
  members: HiveMember[];
  /** Unspent stingers. */
  stingers_available: number;
  pollen: number;
  invites: HiveInvite[];
  outgoing: HiveOutgoing[];
  /** Friends who aren't in the party and haven't been invited. */
  invitable: HiveInvitable[];
  /** Recent hits, newest first. */
  events: HiveEvent[];
  reward: HiveReward | null;
}

export interface StingResult {
  hive: Hive;
  /** This sting was the killing blow. */
  defeated: boolean;
  pollen: number;
  kill_pollen: number;
}

/** A failed hive request, with a message that can be shown to the user as is. */
export class HiveError extends Error {}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/hive${path}`, init);
  } catch {
    throw new HiveError('Couldn’t reach Jobee. Check your connection and try again.');
  }
  if (res.ok) return res.json();
  // The backend words its 4xx errors for the learner (out of stingers, party full, …).
  const detail = await res.json().then((b) => (typeof b?.detail === 'string' ? b.detail : null)).catch(() => null);
  throw new HiveError(res.status < 500 && detail ? detail : 'The hive didn’t answer. Try again in a moment.');
}

const post = (body: unknown): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export const fetchHive = (profileId: string) => call<Hive>(`?profile_id=${encodeURIComponent(profileId)}`);

/** Spend a stinger on Robbee: -20% HP and 500 pollen. */
export const sting = (profileId: string) => call<StingResult>('/sting', post({ profile_id: profileId }));

export const inviteFriend = (profileId: string, toProfileId: string) => call<Hive>('/invites', post({ profile_id: profileId, to_profile_id: toProfileId }));

/** Join the inviting party, replacing the learner's current fight. */
export const acceptInvite = (profileId: string, inviteId: string) => call<Hive>(`/invites/${encodeURIComponent(inviteId)}/accept`, post({ profile_id: profileId }));

/** Decline an invite, or cancel one the learner's party sent. */
export const removeInvite = (profileId: string, inviteId: string) =>
  call<Hive>(`/invites/${encodeURIComponent(inviteId)}?profile_id=${encodeURIComponent(profileId)}`, { method: 'DELETE' });

/** Leave the party for a fresh solo fight. */
export const leaveParty = (profileId: string) => call<Hive>('/leave', post({ profile_id: profileId }));

/** Dismiss a kill popup so it doesn't show again. */
export const markRewardSeen = (profileId: string, rewardId: string) => call<Hive>(`/rewards/${encodeURIComponent(rewardId)}/seen`, post({ profile_id: profileId }));
