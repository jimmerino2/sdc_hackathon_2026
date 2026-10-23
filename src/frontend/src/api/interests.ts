import { API_URL } from './config';

export interface SdgWeight {
  sdg: number;
  value: number;
}

/** Something a learner can be into, with the SDGs it serves behind the scenes. */
export interface Interest {
  id: number;
  interest: string;
  description: string;
  /** Lucide icon name, drawn with <Icon>. */
  icon: string;
  sdg: SdgWeight[];
}

/** One goal in the learner's SDG focus, from the interests they picked. */
export interface SdgFocus {
  sdg: number;
  name: string;
  /** Share of their interests that point at this goal; all goals add up to 1. */
  value: number;
}

/** One SDG a role serves, with the learner's interests it connects to. */
export interface SdgReason {
  sdg: number;
  name: string;
  /** How much of the role's work serves this goal. */
  value: number;
  /** The learner's interests that point at this goal; empty if none do. */
  interests: string[];
}

/** A failed request, with a message that can be shown to the user as is. */
export class InterestsError extends Error {}

export async function fetchInterests(): Promise<Interest[]> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/interests`);
  } catch {
    throw new InterestsError('Couldn’t reach Jobee. Check your connection and try again.');
  }
  if (!res.ok) throw new InterestsError('Jobee couldn’t load the interests just now. Try again in a moment.');
  return res.json();
}
