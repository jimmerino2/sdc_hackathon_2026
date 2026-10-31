import { API_URL } from './config';

export interface SdgGoal {
  sdg: number;
  name: string;
}

/** One SDG target (a sub-goal like 8.2), with how the work serves it. */
export interface SdgTargetNote {
  code: string;
  sdg: number;
  text: string;
}

/** A target's text starts lowercase in the data; shown with a capital. */
export const capFirst = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/** A measurable goal a role could work towards. */
export interface RoleGoal {
  sdg: number | null;
  text: string;
}

/** The SDGs one of a role's skills serves. */
export interface SkillSdg {
  skill_id: string;
  skill_name: string;
  /** 'skill', 'knowledge' or 'tech'. */
  skill_type: string;
  main: SdgGoal;
  relevant: SdgGoal[];
  targets: SdgTargetNote[];
}

/** The SDGs and targets a role's work serves, and those of its skills. */
export interface RoleSdg {
  onet_code: string;
  main: SdgGoal;
  relevant: SdgGoal[];
  /** Main goal's targets first. */
  targets: SdgTargetNote[];
  /** Null if the role has no goal on record. */
  goal?: RoleGoal | null;
  skills: SkillSdg[];
}

/** The role's SDGs and targets; null if the role has none on record. */
export async function fetchRoleSdg(onetCode: string): Promise<RoleSdg | null> {
  const res = await fetch(`${API_URL}/sdg/roles/${encodeURIComponent(onetCode)}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`SDG request failed (${res.status})`);
  return res.json();
}

let skillsByName: Promise<Map<string, SkillSdg>> | undefined;
/** Every skill's SDG targets by skill name, fetched once. An empty map if the request fails, so chips just show no tooltip. */
export function fetchSkillSdgs(): Promise<Map<string, SkillSdg>> {
  skillsByName ??= fetch(`${API_URL}/sdg/skills`)
    .then((r) => (r.ok ? (r.json() as Promise<SkillSdg[]>) : []))
    .catch(() => [] as SkillSdg[])
    .then((list) => new Map(list.map((s) => [s.skill_name, s])));
  return skillsByName;
}
