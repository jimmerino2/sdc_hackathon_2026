import { fetchOutlook } from '../api/outlook';
import type { ScenarioKey } from './flows';

/** A metric from /outlook the "If AI accelerates/steady/slows" picker can draw its percentages from. */
export interface ScenarioMetric {
  target: string;
  /** The unit (country, sector, occupation group…) whose forecast the picker reads; same default as the Outlook page. */
  unit: string;
  /** Short label for the metric picker. */
  label: string;
}

export const SCENARIO_METRICS: ScenarioMetric[] = [
  { target: 'frontier_time_horizon', unit: 'v1.1', label: 'AI capability' },
  { target: 'btos_ai_use_rate', unit: 'US|new', label: 'Business adoption' },
  { target: 'worker_genai_use_rate', unit: '00', label: 'Worker adoption' },
];

export const DEFAULT_SCENARIO_METRIC = 'frontier_time_horizon';

export type ScenarioProbabilities = Record<ScenarioKey, number>;

const cache = new Map<string, Promise<ScenarioProbabilities | null>>();

/**
 * The chance of each AI future, for one /outlook metric, read off its nearest-horizon forecast row
 * (p_acceleration/p_stable/p_slowdown). Null when that metric has no regime data yet, or the unit isn't tracked.
 */
export function scenarioProbabilities(metric: ScenarioMetric): Promise<ScenarioProbabilities | null> {
  const key = `${metric.target}::${metric.unit}`;
  if (!cache.has(key)) {
    cache.set(
      key,
      fetchOutlook(metric.target)
        .then((rows) => {
          const row = rows
            .filter((r) => r.unit.toLowerCase() === metric.unit.toLowerCase())
            .sort((a, b) => a.h - b.h)[0];
          if (!row || row.p_acceleration == null || row.p_stable == null || row.p_slowdown == null) return null;
          return { accelerates: row.p_acceleration, steady: row.p_stable, slows: row.p_slowdown };
        })
        .catch(() => null),
    );
  }
  return cache.get(key)!;
}
