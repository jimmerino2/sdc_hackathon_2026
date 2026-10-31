<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import Icon from '../Icon.vue';
import { fetchSkill, type SkillDetail, type SkillRow } from '../../api/occupational';
import { pct } from '../../occupational/format';
import { ROADMAP_FORECAST_H } from '../../occupational/forecastMatch';

const props = defineProps<{ name: string; row: SkillRow; occupation: string; country: string }>();

const DIR_ICON = { rising: 'tup', falling: 'tdown' } as const;
const DIR_LABEL = { rising: 'Rising demand', falling: 'Falling demand' } as const;
const EVIDENCE_LABEL = { high: 'Strong evidence', medium: 'Some evidence', low: 'Early signal' } as const;

const collapsed = ref(false);
const detail = ref<SkillDetail | null>(null);

/** Too few job ads in this occupation to say anything reliable, whatever the headline number reads. */
const noData = computed(() => props.row.evidence === 'low');

watch(() => props.row.skill_id, async (skillId) => {
  detail.value = null;
  if (noData.value) return; // nothing to chart
  try {
    detail.value = await fetchSkill(skillId, props.country, props.occupation);
  } catch {
    // The headline number and delta don't need this; the sparkline just stays off.
  }
}, { immediate: true });

/** Up to 11 months of observed share, plus the forecast point: a 12-point sparkline. */
const points = computed(() => {
  const hist = (detail.value?.history ?? [])
    .filter((p) => !p.is_partial && p.share_3m != null)
    .slice(-11)
    .map((p) => ({ v: p.share_3m!, forecast: false }));
  return [...hist, { v: props.row.forecast, forecast: true }];
});

const W = 100, H = 40, PAD = 4;
const spark = computed(() => {
  const vals = points.value.map((p) => p.v);
  if (points.value.length < 3) return null;
  const lo = Math.min(...vals), hi = Math.max(...vals, lo + 1e-6);
  const x = (i: number) => (i / (points.value.length - 1)) * W;
  const y = (v: number) => H - PAD - ((v - lo) / (hi - lo)) * (H - PAD * 2);
  const histPts = points.value.filter((p) => !p.forecast);
  const histPath = histPts.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.v).toFixed(1)}`).join(' ');
  const last = points.value.length - 2;
  const fc = points.value.at(-1)!;
  return {
    histPath,
    fcLine: `M${x(last).toFixed(1)},${y(histPts.at(-1)!.v).toFixed(1)} L${x(last + 1).toFixed(1)},${y(fc.v).toFixed(1)}`,
    fcX: x(last + 1), fcY: y(fc.v),
  };
});
</script>

<template>
  <section class="jb jb-card jb-forecast" :data-direction="row.direction">
    <div class="jb-card__head">
      <p class="jb-eyebrow">Demand forecast</p>
      <button type="button" class="jb-collapse" :aria-expanded="!collapsed" aria-label="Toggle demand forecast" @click="collapsed = !collapsed">
        <Icon name="chevron" :size="16" :class="{ 'jb-collapse__icon--up': !collapsed }" />
      </button>
    </div>
    <h3 class="jb-card__title">{{ name }}</h3>
    <!-- Flat gets no label: at the 6-month horizon the served model is the 12-month average, so every skill is flat. -->
    <p v-if="noData || row.direction !== 'flat'" class="jb-forecast__dir">
      <Icon v-if="!noData && row.direction !== 'flat'" :name="DIR_ICON[row.direction]" :size="16" />
      {{ noData ? 'Not enough data yet' : DIR_LABEL[row.direction as 'rising' | 'falling'] }}
    </p>

    <div v-show="!collapsed" class="jb-next__body">
      <template v-if="noData">
        <p class="jb-forecast__hint">Too few job ads for this role mention it yet for a reliable trend.</p>
      </template>
      <template v-else>
        <div class="jb-forecast__stat">
          <span class="jb-forecast__value">{{ pct(row.last_share_3m ?? row.forecast) }}</span>
          <span v-if="row.last_share_3m != null" class="jb-forecast__delta">→ {{ pct(row.forecast) }} in {{ ROADMAP_FORECAST_H }} mo</span>
        </div>
        <p class="jb-forecast__hint">
          {{ row.last_share_3m != null ? 'of job ads ask for this skill now' : `of job ads ask for this skill, forecast ${ROADMAP_FORECAST_H} months out` }}
        </p>

        <svg v-if="spark" class="jb-forecast__spark" viewBox="0 0 100 40" preserveAspectRatio="none" role="img" aria-label="Recent trend, leading into the forecast">
          <path :d="spark.histPath" class="jb-forecast__sparkline" vector-effect="non-scaling-stroke" />
          <path :d="spark.fcLine" class="jb-forecast__sparkline jb-forecast__sparkline--fc" vector-effect="non-scaling-stroke" />
          <circle :cx="spark.fcX" :cy="spark.fcY" r="3" class="jb-forecast__sparkdot">
            <title>Forecast: {{ pct(row.forecast) }} of job ads in {{ ROADMAP_FORECAST_H }} months</title>
          </circle>
        </svg>
      </template>

      <span class="jb-forecast__evidence">{{ EVIDENCE_LABEL[row.evidence] }}</span>
    </div>
  </section>
</template>
