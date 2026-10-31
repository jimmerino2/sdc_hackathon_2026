<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import Icon from './Icon.vue';
import type { QuarterInfo, Retrained } from '../api/forecast';
import {
  byYear, excludeAll, excludeAllBut, excludeBefore, keptCount, quarterSpan, rangeBetween, sameSet, toggleQuarter, toggleYear, yearSpan, yearState,
  type Span,
} from '../data/quarterPick';
import { month } from '../occupational/format';

const props = defineProps<{
  quarters: QuarterInfo[];
  /** The quarters left out of the forecast now. */
  excluded: ReadonlySet<string>;
  busy: boolean;
  error: string | null;
  /** The answer for the applied choice, once there is one. */
  result: Retrained | null;
  canRefresh: boolean;
}>();
const emit = defineEmits<{ apply: [excluded: Set<string>]; refresh: [] }>();

/** What is being picked: nothing changes the forecast until Done. */
const draft = ref(new Set(props.excluded));
watch(() => props.excluded, (e) => { draft.value = new Set(e); anchor.value = null; });

const rows = computed(() => byYear(props.quarters));
const kept = computed(() => keptCount(props.quarters, draft.value));
const dirty = computed(() => !sameSet(draft.value, props.excluded));
const canApply = computed(() => dirty.value && kept.value > 0 && !props.busy);

/** With nothing kept, taps pick a range (start, then end) instead of toggling one quarter. */
const ranging = computed(() => kept.value === 0);
const anchor = ref<Span | null>(null);
const hover = ref<Span | null>(null);
const preview = computed(() => {
  if (!anchor.value) return new Set<string>();
  return new Set(rangeBetween(anchor.value, hover.value ?? anchor.value, props.quarters));
});
const previewEnds = computed(() => {
  const list = props.quarters.filter((q) => preview.value.has(q.quarter));
  return list.length ? `${list[0].quarter} to ${list.at(-1)!.quarter}` : '';
});
/** How far a quarter is from the start of the range, so the fade can ripple out from it. */
function distance(i: number): number {
  const a = anchor.value;
  if (!a) return 0;
  return Math.min(14, i < a.lo ? a.lo - i : i > a.hi ? i - a.hi : 0);
}
const indexOf = (q: string) => props.quarters.findIndex((x) => x.quarter === q);

function pickSpan(span: Span | null) {
  if (!span || props.busy) return;
  if (!anchor.value) {
    anchor.value = span;
    hover.value = span;
    return;
  }
  draft.value = excludeAllBut(rangeBetween(anchor.value, span, props.quarters), props.quarters);
  anchor.value = hover.value = null;
}
function tapQuarter(q: string) {
  if (ranging.value) pickSpan(quarterSpan(q, props.quarters));
  else draft.value = toggleQuarter(draft.value, q);
}
function tapYear(year: string) {
  if (ranging.value) pickSpan(yearSpan(year, props.quarters));
  else draft.value = toggleYear(year, props.quarters, draft.value);
}
const aim = (span: Span | null) => { if (anchor.value && span) hover.value = span; };

function setDraft(next: Set<string>) {
  draft.value = next;
  anchor.value = hover.value = null;
}
const reset = () => setDraft(new Set(props.excluded));
const apply = () => canApply.value && emit('apply', new Set(draft.value));

/** Quarters before 2022 are the pandemic years: the model treats them as a separate period. */
const POST_PANDEMIC = 2022;
const afterPandemic = computed(() => sameSet(draft.value, excludeBefore(POST_PANDEMIC, props.quarters)));
const stateWord = { all: 'every quarter kept', some: 'some quarters kept', none: 'left out' } as const;

const hint = computed(() => {
  if (!ranging.value) return 'Tap quarters or years to keep or leave them out, as many as you like. Nothing changes until you press Done.';
  if (!anchor.value) return 'Everything is left out. Tap the first quarter or year of the range you want to keep.';
  return `${previewEnds.value}. Tap the last quarter or year to finish. Esc cancels.`;
});

/** One honest line about what the applied choice did to the model. */
const summary = computed(() => {
  const r = props.result;
  if (!r || !props.excluded.size) return '';
  const start = `Forecast from ${month(r.forecast_from)}`;
  const base = r.default_trained_rows;
  if (base == null) return `${start} · trained on ${r.trained_rows.toLocaleString()} samples`;
  if (r.trained_rows >= base) return `${start} · same training data. What you left out has no known outcome yet, so only the start moved`;
  return `${start} · trained on ${r.trained_rows.toLocaleString()} samples, ${(base - r.trained_rows).toLocaleString()} fewer than with every quarter`;
});
</script>

<template>
  <section class="qp" aria-labelledby="qp-title" @keydown.esc="anchor = hover = null">
    <div class="head">
      <h2 id="qp-title">Training data</h2>
      <p class="count"><b>{{ kept }}</b> of {{ quarters.length }} quarters<template v-if="dirty"> · not applied</template></p>
    </div>

    <div class="presets">
      <button type="button" class="chip-btn" :class="{ on: !draft.size }" :disabled="busy" @click="setDraft(new Set())">All</button>
      <button type="button" class="chip-btn" :class="{ on: ranging }" :disabled="busy" @click="setDraft(excludeAll(quarters))">Exclude all</button>
      <button type="button" class="chip-btn" :class="{ on: afterPandemic }" :disabled="busy" title="Leave out 2020 and 2021" @click="setDraft(excludeBefore(POST_PANDEMIC, quarters))">{{ POST_PANDEMIC }} onwards</button>
    </div>

    <p id="qp-hint" class="hint" aria-live="polite">{{ hint }}</p>

    <div class="grid" :class="{ ranging }" role="group" aria-describedby="qp-hint" @mouseleave="hover = anchor">
      <div v-for="row in rows" :key="row.year" class="row" role="group" :aria-label="`Quarters of ${row.year}`">
        <button
          type="button"
          class="year"
          :class="[yearState(row.year, quarters, draft), {
            preview: ranging && quarters.filter((q) => q.quarter.startsWith(row.year)).every((q) => preview.has(q.quarter)) && anchor,
            anchor: ranging && anchor && anchor.lo === yearSpan(row.year, quarters)?.lo && anchor.hi === yearSpan(row.year, quarters)?.hi,
          }]"
          :disabled="busy"
          :aria-label="ranging ? `${row.year}: use as an end of the range` : `${row.year}: ${stateWord[yearState(row.year, quarters, draft)]}`"
          :aria-pressed="ranging ? undefined : yearState(row.year, quarters, draft) !== 'none'"
          :style="{ '--d': distance(yearSpan(row.year, quarters)?.lo ?? 0) }"
          @click="tapYear(row.year)"
          @mouseenter="aim(yearSpan(row.year, quarters))"
          @focus="aim(yearSpan(row.year, quarters))"
        >{{ row.year }}</button>
        <template v-for="(q, i) in row.quarters" :key="i">
          <button
            v-if="q"
            type="button"
            class="q"
            :class="{
              off: draft.has(q.quarter) && !preview.has(q.quarter),
              pending: !q.has_outcome,
              preview: preview.has(q.quarter),
              anchor: anchor && indexOf(q.quarter) >= anchor.lo && indexOf(q.quarter) <= anchor.hi,
            }"
            :aria-pressed="ranging ? undefined : !draft.has(q.quarter)"
            :aria-label="q.quarter"
            :disabled="busy"
            :style="{ '--d': distance(indexOf(q.quarter)) }"
            :title="q.has_outcome ? q.quarter : `${q.quarter}: its outcome isn’t known yet, so leaving it out only moves where the forecast starts`"
            @click="tapQuarter(q.quarter)"
            @mouseenter="aim(quarterSpan(q.quarter, quarters))"
            @focus="aim(quarterSpan(q.quarter, quarters))"
          >Q{{ i + 1 }}</button>
          <span v-else class="q none" aria-hidden="true">Q{{ i + 1 }}</span>
        </template>
      </div>
    </div>

    <div class="actions">
      <button type="button" class="btn btn-primary done" :disabled="!canApply" @click="apply">Done</button>
      <button v-if="dirty || anchor" type="button" class="link" :disabled="busy" @click="reset">Cancel</button>
    </div>

    <p class="line" aria-live="polite">
      <template v-if="busy"><span class="dots" aria-hidden="true" />Re-forecasting…</template>
      <template v-else-if="error"><span class="bad">{{ error }}</span></template>
      <template v-else-if="dirty && kept === 0">Keep at least one quarter to train on.</template>
      <template v-else-if="summary && !dirty">{{ summary }}</template>
    </p>
    <button v-if="canRefresh" type="button" class="link" :disabled="busy" @click="emit('refresh')"><Icon name="refresh" :size="13" :stroke="3" /> Re-read data</button>
  </section>
</template>

<style scoped>
.qp { padding: 16px; border-radius: 20px; background: #fff; border: 2px solid var(--line); box-shadow: 0 8px 24px rgba(30, 30, 30, .06); }
.head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
h2 { margin: 0; font-size: 17px; font-weight: 900; }
.count { margin: 0; font-size: 12px; font-weight: 800; color: var(--muted); white-space: nowrap; }
.count b { color: var(--amber-ink); font-size: 14px; }
.presets { display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0 8px; }
.hint { margin: 0 0 10px; min-height: 3.9em; font-size: 12px; line-height: 1.4; font-weight: 700; color: var(--muted); }

.chip-btn, .year, .q { border: 2px solid var(--line-strong); background: #fff; color: var(--ink); font-weight: 900; line-height: 1.2;
  transition: background .18s ease, border-color .18s ease, color .18s ease, opacity .15s, transform .1s; }
.chip-btn { padding: 6px 12px; border-radius: 999px; font-size: 12px; }
.chip-btn.on { background: var(--ink); border-color: var(--ink); color: var(--yellow); }

.grid { display: grid; gap: 6px; }
.row { display: grid; grid-template-columns: 56px repeat(4, minmax(0, 1fr)); gap: 6px; }
.year { padding: 8px 0; border-radius: 10px; font-size: 13px; }
.year.all { background: var(--yellow); border-color: var(--ink); }
.year.some { background: linear-gradient(90deg, var(--yellow) 50%, #fff 50%); border-color: var(--ink); }
.year.none { color: var(--muted); text-decoration: line-through; }
.q { padding: 8px 0; border-radius: 10px; font-size: 12px; background: var(--yellow); border-color: var(--ink); }
.q.pending { border-style: dashed; }
.q.off { background: #fff; border-color: var(--line-strong); color: var(--muted); text-decoration: line-through; }
.q.none { display: grid; place-items: center; border-style: dotted; background: transparent; color: var(--line-strong); }

/* Picking a range: nothing is kept, so the grid is plain until the range lights up, fading in from its start. */
.ranging .q, .ranging .year { background: #fff; border-color: var(--line-strong); color: var(--ink); text-decoration: none; }
.ranging .q.pending { border-style: dashed; }
.ranging .q.preview, .ranging .year.preview { background: color-mix(in srgb, var(--yellow) 42%, #fff); border-color: var(--yellow); transition-delay: calc(var(--d) * 14ms); }
.ranging .q.anchor, .ranging .year.anchor { background: var(--yellow); border-color: var(--ink); box-shadow: 0 0 0 2px var(--ink); transition-delay: 0s; }
.ranging .q.none { background: transparent; border-color: var(--line-strong); color: var(--line-strong); }

button:active:not(:disabled) { transform: translateY(1px); }
button:disabled { opacity: .5; cursor: not-allowed; }
.actions { display: flex; align-items: center; gap: 14px; margin-top: 14px; }
.done { padding: 11px 26px; font-size: 14px; }
.link { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 900; color: var(--amber-ink); text-decoration: underline; text-underline-offset: 3px; }
.line { min-height: 2.8em; margin: 12px 0 0; font-size: 12px; line-height: 1.4; font-weight: 700; color: var(--muted); }
.bad { color: #b3261e; }
.dots { display: inline-block; width: 10px; height: 10px; margin-right: 6px; border-radius: 50%; border: 2px solid var(--line-strong); border-top-color: var(--yellow); vertical-align: -1px; animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .dots { animation: none; } .chip-btn, .year, .q { transition: none; } .ranging .q.preview, .ranging .year.preview { transition-delay: 0s; } }
@media (max-width: 420px) { .row { grid-template-columns: 48px repeat(4, minmax(0, 1fr)); } }
</style>
