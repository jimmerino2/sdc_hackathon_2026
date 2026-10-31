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
  skills: SkillSdg[];
}

/** The role's SDGs and targets; null if the role has none on record. */
export async function fetchRoleSdg(onetCode: string): Promise<RoleSdg | null> {
  const res = await fetch(`${API_URL}/sdg/roles/${encodeURIComponent(onetCode)}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`SDG request failed (${res.status})`);
  return res.json();
}
