import { API_URL } from './config';

/** Someone on the leaderboard. Their picture is their companion bee. */
export interface Player {
  profile_id: string;
  name: string;
  bee: string;
  pollen: number;
  /** 1 = most pollen. */
  rank: number;
  is_me: boolean;
}

export interface Friend {
  profile_id: string;
  name: string;
  bee: string;
  /** Their email with the domain hidden, e.g. "jun@...". */
  email_hint: string;
  friendship_id: string;
}

/** A request waiting for the learner to accept. */
export interface Incoming {
  friendship_id: string;
  name: string;
  bee: string;
  email: string;
}

/** A request the learner sent that hasn't been accepted. */
export interface Sent {
  friendship_id: string;
  email: string;
  /** False: nobody has an account with this email yet. */
  signed_up: boolean;
}

export interface Social {
  /** The learner's own pollen. */
  pollen: number;
  /** The learner and their friends, most pollen first. */
  leaderboard: Player[];
  friends: Friend[];
  incoming: Incoming[];
  sent: Sent[];
}

/** A failed social request, with a message that can be shown to the user as is. */
export class SocialError extends Error {}

async function call(path: string, init?: RequestInit): Promise<Social> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/social${path}`, init);
  } catch {
    throw new SocialError('Couldn’t reach Jobee. Check your connection and try again.');
  }
  if (res.ok) return res.json();
  // The backend words its 4xx errors for the learner (a bad email, already friends, …).
  const detail = await res.json().then((b) => (typeof b?.detail === 'string' ? b.detail : null)).catch(() => null);
  throw new SocialError(res.status < 500 && detail ? detail : 'Something went wrong on our side. Try again in a moment.');
}

const json = (body: unknown): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export const fetchSocial = (profileId: string) => call(`?profile_id=${encodeURIComponent(profileId)}`);

/** Ask someone to be friends by email. They need a Jobee account, now or later. */
export const sendFriendRequest = (profileId: string, email: string) => call('/requests', json({ profile_id: profileId, email }));

export const acceptFriendRequest = (profileId: string, friendshipId: string) =>
  call(`/requests/${encodeURIComponent(friendshipId)}/accept`, json({ profile_id: profileId }));

/** Decline a request, cancel one the learner sent, or unfriend. */
export const removeFriendship = (profileId: string, friendshipId: string) =>
  call(`/requests/${encodeURIComponent(friendshipId)}?profile_id=${encodeURIComponent(profileId)}`, { method: 'DELETE' });
