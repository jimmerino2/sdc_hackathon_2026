import { API_URL } from './config';

/** An HRD Corp-claimable course that teaches a skill, from HRD Corp's public BizMatch course list. */
export interface Programme {
  course_id: number;
  training_provider: string;
  course_name: string;
  scheme: string;
  certification: string | null;
  fee_rm: number;
  discount_pct: number;
  fee_after_discount_rm: number;
  /** A workshop a company books for its own staff; an individual can't enrol. */
  in_house: boolean;
  /** The day the list was read, YYYY-MM-DD. */
  fetched: string;
  source_url: string;
}

/** HRD Corp's public course list, where the fees come from. */
export const HRD_LIST_URL = 'https://bizmatch.hrdcorp.gov.my/bizmatch/public/index.php/courses';

const cache = new Map<string, Promise<Programme[]>>();

/** The HRD Corp-claimable courses for a skill (its O*NET name), best first. Fetched once per skill; a failure gives none and isn't kept. */
export function fetchProgrammes(skill: string): Promise<Programme[]> {
  let found = cache.get(skill);
  if (!found) {
    found = fetch(`${API_URL}/hrd/programmes?skill=${encodeURIComponent(skill)}&limit=5`)
      .then((res) => (res.ok ? (res.json() as Promise<Programme[]>) : []))
      .catch(() => []);
    cache.set(skill, found);
    found.then((list) => list.length || cache.delete(skill)); // an empty answer may be a hiccup: ask again next time
  }
  return found;
}
