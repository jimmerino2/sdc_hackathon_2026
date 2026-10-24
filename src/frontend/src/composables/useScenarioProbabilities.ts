import { computed, ref, watch } from 'vue';
import { useFlow } from '../state';
import { SCENARIO_METRICS, scenarioProbabilities, type ScenarioProbabilities } from '../data/outlookScenarios';
import type { ScenarioKey } from '../data/flows';

/** Drives the "If AI accelerates/steady/slows" picker's percentages: which /outlook metric is chosen (persisted
 * on state, shared by onboarding and the Roles page), and that metric's nearest-horizon chances. */
export function useScenarioProbabilities() {
  const { state } = useFlow();
  const probs = ref<ScenarioProbabilities | null>(null);

  const metric = computed(() => SCENARIO_METRICS.find((m) => m.target === state.value.scenarioMetric) ?? SCENARIO_METRICS[0]!);

  watch(
    metric,
    async (m) => {
      probs.value = null; // don't show the previous metric's numbers while the new one loads
      probs.value = await scenarioProbabilities(m);
    },
    { immediate: true },
  );

  /** Rounded percent for a scenario, or null while loading or when this metric has no regime data yet. */
  function pct(key: ScenarioKey): number | null {
    return probs.value ? Math.round(probs.value[key] * 100) : null;
  }

  /** The 3 scenarios, most likely first; the fixed order when there's nothing to rank them by yet. */
  const ranked = computed<ScenarioKey[]>(() => {
    const p = probs.value;
    const order: ScenarioKey[] = ['accelerates', 'steady', 'slows'];
    return p ? [...order].sort((a, b) => p[b] - p[a]) : order;
  });

  /** Green/amber/red by how likely a scenario is relative to the other two; null until ranked. */
  const RANK_COLOR = ['#2e7d4f', 'var(--amber-ink)', '#c62828'] as const;
  function rankColor(key: ScenarioKey): string | null {
    if (!probs.value) return null;
    return RANK_COLOR[ranked.value.indexOf(key)] ?? null;
  }

  return {
    metrics: SCENARIO_METRICS,
    metricTarget: computed({
      get: () => state.value.scenarioMetric,
      set: (target: string) => { state.value.scenarioMetric = target; },
    }),
    pct,
    ranked,
    rankColor,
  };
}
