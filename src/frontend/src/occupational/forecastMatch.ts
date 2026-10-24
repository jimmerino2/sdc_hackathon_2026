import { fetchOccMeta, fetchSkills, type OccMeta, type SkillRow } from '../api/occupational';

/** The demand-forecast horizon shown on the roadmap, in months. */
export const ROADMAP_FORECAST_H = 6;
export const ROADMAP_FORECAST_COUNTRY = 'US';
const COUNTRY = ROADMAP_FORECAST_COUNTRY;

/** A role's demand forecast: which occupation x country it came from, and its rows keyed by normalized skill name. */
export interface RoleForecast {
  occupation: string;
  country: string;
  rows: Map<string, SkillRow>;
}

let metaPromise: Promise<OccMeta | null> | null = null;

/** The occupational-forecasting meta, cached for the session; null if the pipeline isn't built. */
function loadMeta(): Promise<OccMeta | null> {
  if (!metaPromise) metaPromise = fetchOccMeta().catch(() => null);
  return metaPromise;
}

/** The occupation slug (e.g. "software_engineer") that an O*NET code is tracked under, or null if none. */
function occupationFor(meta: OccMeta, onetCode: string): string | null {
  for (const sector of meta.taxonomy.sectors) {
    for (const occ of sector.occupations) {
      if (occ.onet_codes.includes(onetCode)) return occ.id;
    }
  }
  return null;
}

/** Loosely comparable form of a skill name, for matching roadmap labels against forecast skill names. */
export function normalizeSkillName(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '');
}

/** This role's forecast, matched by normalized skill name; null if the role isn't tracked or has no data. */
export async function loadRoleForecast(onetCode: string): Promise<RoleForecast | null> {
  const meta = await loadMeta();
  const occupation = meta && occupationFor(meta, onetCode);
  if (!occupation) return null;
  try {
    const res = await fetchSkills(COUNTRY, occupation, ROADMAP_FORECAST_H);
    if (res.mode !== 'latest') return null;
    const rows = new Map<string, SkillRow>();
    for (const row of res.rows) rows.set(normalizeSkillName(row.skill_name), row);
    return { occupation, country: COUNTRY, rows };
  } catch {
    return null;
  }
}
