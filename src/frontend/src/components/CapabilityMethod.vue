<script setup lang="ts">
import { computed } from 'vue';
import type { EngineDetail } from '../api/outlook';

/** Compact methodology and diagnostics for the AI capability forecast: data, method, backtest, pace skill, limits. */
const props = defineProps<{ detail: EngineDetail; unit: string }>();

const u = computed(() => props.detail.units[props.unit]);
const bt = computed(() => props.detail.backtest);
const hs = computed(() => u.value?.horizons.map((h) => h.h) ?? []);
const date = (s: string) => new Date(s).toLocaleDateString('en', { day: 'numeric', month: 'short', year: 'numeric' });
const month = (p: string) => new Date(`${p}-01`).toLocaleDateString('en', { month: 'short', year: 'numeric' });
const x = (v: number | null | undefined) => (v == null ? '–' : `×${v.toFixed(2)}`);
const pct = (v: number | null | undefined) => (v == null ? '–' : `${Math.round(v * 100)}%`);
const f2 = (v: number | null | undefined) => (v == null ? '–' : v.toFixed(2));

const NAMES: Record<string, string> = {
  ensemble: 'Ensemble (shown)', damped_trend: 'Damped trend', robust_local_trend: 'Robust local trend',
  jump_process: 'Jump model', drift: 'Continue last year’s trend', naive: '“No change”',
};
const ROWS = ['ensemble', 'damped_trend', 'robust_local_trend', 'jump_process', 'drift', 'naive'];
const point = (h: number, role: string, c: string) => bt.value.point.find((p) => p.h === h && p.role === role && p.candidate === c);
const pace = (h: number, role: string) => bt.value.pace.find((p) => p.h === h && p.role === role && p.candidate === 'ensemble');
const skill = (h: number, role: string) => {
  const p = pace(h, role);
  if (!p?.n || p.brier_served == null) return null;
  return p.brier_served < (p.brier_uniform ?? 1) && p.brier_served < (p.brier_climatology ?? 1);
};
const doubling = computed(() => {
  const j = u.value?.components.jump_process as { doubling_time_months?: number } | undefined;
  return j?.doubling_time_months ?? null;
});
const metrDoubling = computed(() => props.detail.data.metr_published_doubling_days?.from_2023_on ?? null);
</script>

<template>
  <details v-if="u" class="meth">
    <summary>How this forecast is made, and how well it has done</summary>

    <h4>Data</h4>
    <ul class="facts">
      <li><b>Source:</b> METR’s 50% time horizons (Time Horizon {{ unit.replace('v', '') }}), as published in Epoch AI’s data. Each monthly archive copy is used only from the date it was available.
        <template v-if="detail.data.metr_official_check">Cross-checked against METR’s own file: {{ detail.data.metr_official_check.matched_within_1pct }} of {{ detail.data.metr_official_check.models_compared }} models match.</template></li>
      <li><b>Latest data:</b> {{ date(detail.data.data_as_of) }}. Complete through {{ month(detail.data.latest_complete_month) }}: METR measures models weeks to months after release, so the last {{ detail.data.measurement_lag_months }} months are treated as not yet measured, not as “no progress”.</li>
      <li><b>Measured models:</b> {{ u.n_observed }} on this suite.
        <template v-if="u.bridge.applied">
          <b>Bridge applied:</b> {{ u.n_bridged }} models measured only on METR’s older suite are mapped onto this one through {{ u.bridge.n_pairs }} models measured on both
          (slope {{ f2(u.bridge.slope) }}, 80% range {{ f2(u.bridge.slope_ci80?.[0]) }}–{{ f2(u.bridge.slope_ci80?.[1]) }}{{ u.bridge.credible ? '' : '; too uncertain, used only as a weak prior' }}).
          They inform the trend at half weight and are never counted as measurements.
        </template>
        <template v-else>No bridge ({{ u.bridge.reason ?? 'not needed' }}).</template></li>
    </ul>

    <h4>Method</h4>
    <ul class="facts">
      <li>Modelled in doublings (log₂ of hours). Three approaches each simulate {{ detail.config.n_sims.toLocaleString('en') }} possible futures:
        a <b>damped trend</b> (last year’s pace, possibly slowing), a <b>robust local trend</b> (a level and growth rate that drift slowly; one outsized jump cannot dominate),
        and a <b>jump model</b> (new frontier-level models arrive at random and score around a trend, so some months bring no new record and some bring big jumps).</li>
      <li>The forecast mixes them with weights from their past errors, kept close to equal so a few lucky tests cannot dominate:
        <span v-for="h in u.horizons" :key="h.h" class="w">{{ h.h }} mo: {{ Object.entries(h.weights).map(([k, v]) => `${NAMES[k] ?? k} ${pct(v)}`).join(', ') }}</span></li>
      <li v-if="doubling">The jump model’s trend implies a doubling every {{ doubling.toFixed(1) }} months<template v-if="metrDoubling"> (METR’s own fit since 2023: {{ (metrDoubling.point_estimate / 30.44).toFixed(1) }} months, {{ (metrDoubling.ci_low / 30.44).toFixed(1) }}–{{ (metrDoubling.ci_high / 30.44).toFixed(1) }}; not used as an input)</template>.</li>
      <li>The faster / same / slower chances are shares of those same simulated futures, compared with the past 12 months’ pace (“same” = within ±max({{ detail.config.pace_tol_abs }} doublings/year, {{ Math.round(detail.config.pace_tol_rel * 100) }}%)).</li>
    </ul>

    <h4>Tested on past months it hadn’t seen</h4>
    <p class="small">Typical miss as a factor (×1.5 = typically 50% too high or too low) and how often the actual value fell inside the 80% range.
      {{ bt.n_origins }} forecast dates; recent tests are the held-back ones, never used to set anything.</p>
    <div class="scroll">
      <table>
        <thead>
          <tr><th scope="col">Method</th><th v-for="h in hs" :key="h" scope="col" colspan="2">{{ h }} months</th></tr>
          <tr><th scope="col" /><template v-for="h in hs" :key="h"><th scope="col">miss</th><th scope="col">in 80%</th></template></tr>
        </thead>
        <tbody>
          <tr v-for="c in ROWS" :key="c" :class="{ shown: c === 'ensemble', base: c === 'naive' || c === 'drift' }">
            <td>{{ NAMES[c] }}</td>
            <template v-for="h in hs" :key="h">
              <td>{{ x(point(h, 'holdout', c)?.typical_factor) }}</td>
              <td>{{ pct(point(h, 'holdout', c)?.coverage_80) }}</td>
            </template>
          </tr>
          <tr class="n"><td>Recent test cases</td><template v-for="h in hs" :key="h"><td colspan="2">{{ point(h, 'holdout', 'ensemble')?.n ?? 0 }}</td></template></tr>
          <tr class="n"><td>Earlier tests: ensemble (drift)</td><template v-for="h in hs" :key="h"><td>{{ x(point(h, 'selection', 'ensemble')?.typical_factor) }} ({{ x(point(h, 'selection', 'drift')?.typical_factor) }})</td><td>{{ pct(point(h, 'selection', 'ensemble')?.coverage_80) }}</td></template></tr>
        </tbody>
      </table>
    </div>
    <p class="small">The 80% range is not proven calibrated: it held the actual value more often than 80% in the recent tests and less often in the
      earlier ones, when growth outran every method.</p>

    <h4>Have the faster / same / slower chances shown skill?</h4>
    <p class="small">Brier score of the chances (0 = perfect; a ⅓-each guess scores 0.67) against the base rate of past outcomes.</p>
    <div class="scroll">
      <table>
        <thead><tr><th scope="col">Horizon</th><th scope="col">Tests</th><th scope="col">Chances</th><th scope="col">Base rate</th><th scope="col">⅓ guess</th><th scope="col">Verdict</th></tr></thead>
        <tbody>
          <template v-for="h in hs" :key="h">
            <tr v-for="role in ['selection', 'holdout']" :key="role">
              <td>{{ h }} mo, {{ role === 'holdout' ? 'recent' : 'earlier' }}</td>
              <td>{{ pace(h, role)?.n ?? 0 }}</td>
              <td>{{ f2(pace(h, role)?.brier_served) }}</td>
              <td>{{ f2(pace(h, role)?.brier_climatology) }}</td>
              <td>{{ f2(pace(h, role)?.brier_uniform) }}</td>
              <td :class="skill(h, role) ? 'ok' : 'bad'">{{ skill(h, role) == null ? '–' : skill(h, role) ? 'better than both' : 'not better' }}</td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <h4>Checks of the jump model’s assumptions</h4>
    <ul class="facts">
      <li>Month-to-month frontier changes: lag-1 correlation {{ f2(u.iid_checks.increment_lag1_autocorrelation) }} (near 0 = roughly independent); {{ u.iid_checks.months_with_new_record }} of {{ u.iid_checks.months }} months set a new record.</li>
      <li>Releases per month: dispersion {{ f2(u.iid_checks.release_dispersion_index) }} (1 = random arrivals; above 1 is absorbed by drawing the rate per simulated future).</li>
    </ul>

    <h4>Limits</h4>
    <ul class="facts"><li v-for="l in detail.limitations" :key="l">{{ l }}</li></ul>
    <p class="small">{{ bt.note }}</p>
  </details>
</template>

<style scoped>
.meth { font-size: 12.5px; border-top: 2px solid var(--line); padding-top: 10px; }
summary { cursor: pointer; font-weight: 800; color: var(--ink); font-size: 13px; }
h4 { font-size: 12.5px; margin: 14px 0 4px; }
.facts { margin: 0 0 0 16px; display: flex; flex-direction: column; gap: 4px; line-height: 1.5; color: var(--ink); }
.w { display: block; color: var(--muted); }
.small { color: var(--muted); line-height: 1.45; margin-bottom: 4px; }
.scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; font-size: 12px; min-width: 420px; }
th, td { text-align: right; padding: 4px 6px; border-bottom: 1px solid var(--line); }
th:first-child, td:first-child { text-align: left; }
th { font-weight: 800; color: var(--muted); font-size: 11px; }
tr.shown td { font-weight: 800; }
tr.base td { background: #faf9f6; }
tr.n td { color: var(--muted); font-size: 11px; }
.ok { color: #1e5e30; font-weight: 800; }
.bad { color: #a12a22; font-weight: 800; }
</style>
