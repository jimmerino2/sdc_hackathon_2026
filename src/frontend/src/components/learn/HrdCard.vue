<script setup lang="ts">
import { computed, ref } from 'vue';
import Icon from '../Icon.vue';
import { HRD_LIST_URL, type Programme } from '../../api/hrd';
import { day } from '../../occupational/format';

const props = defineProps<{
  /** The skill's display name. */
  skill: string;
  /** null while loading. */
  programmes: Programme[] | null;
}>();

/** Open by default; the header folds the card away. */
const collapsed = ref(false);
const count = computed(() => props.programmes?.length ?? 0);

const money = (n: number) => `RM ${n.toLocaleString('en-MY', { minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: 2 })}`;
/** The day the list was read; every course comes from the same read. */
const readOn = computed(() => (props.programmes?.length ? day(props.programmes[0].fetched) : ''));
</script>

<template>
  <section class="jb jb-card jb-hrd" aria-labelledby="hrd-title">
    <div class="jb-hrd__head" @click="collapsed = !collapsed">
      <span class="jb-hrd__seal" aria-hidden="true"><Icon name="landmark" :size="18" :stroke="2.3" /><i class="jb-hrd__verified"><Icon name="check" :size="10" :stroke="4" /></i></span>
      <div class="jb-hrd__heading">
        <p class="jb-hrd__eyebrow">Paid · employer claims the fee</p>
        <h3 id="hrd-title" class="jb-hrd__title">HRD Corp Verified</h3>
      </div>
      <span v-if="count" class="jb-hrd__count">{{ count }} {{ count === 1 ? 'course' : 'courses' }}</span>
      <button type="button" class="jb-hrd__toggle" :aria-expanded="!collapsed" aria-controls="hrd-body" :aria-label="collapsed ? 'Show HRD Corp courses' : 'Hide HRD Corp courses'">
        <Icon name="chevron" :size="18" :class="{ 'jb-collapse__icon--up': !collapsed }" />
      </button>
    </div>

    <div v-show="!collapsed" id="hrd-body">
      <div v-if="programmes === null" class="jb-hrd__skel" aria-hidden="true"><span class="skel" /><span class="skel" /></div>

      <template v-else-if="programmes.length">
        <p class="jb-hrd__lede">Courses for {{ skill }} on HRD Corp’s claimable list. These cost money. A company registered with HRD Corp can claim the fee back, so ask your employer. You can’t claim it yourself.</p>
        <ul class="jb-hrd__list">
          <li v-for="p in programmes" :key="p.course_id">
            <a :href="p.source_url" target="_blank" rel="noopener noreferrer" :title="`Opens HRD Corp’s course list where ${p.course_name} is`">
              <span class="jb-hrd__tick" aria-hidden="true"><Icon name="check" :size="12" :stroke="3.6" /></span>
              <span class="jb-hrd__main">
                <b>{{ p.course_name }}</b>
                <small>{{ p.training_provider }}</small>
                <span v-if="p.certification === 'Professional Certification' || p.discount_pct > 0" class="jb-hrd__tags">
                  <em v-if="p.certification === 'Professional Certification'" class="jb-hrd__tag jb-hrd__tag--cert" title="Professional certification"><Icon name="grad" :size="12" :stroke="2.6" aria-hidden="true" /> Certification</em>
                  <em v-if="p.discount_pct > 0" class="jb-hrd__tag">{{ p.discount_pct }}% off</em>
                </span>
              </span>
              <span class="jb-hrd__price">
                <b>{{ p.fee_after_discount_rm === 0 ? 'RM 0' : money(p.fee_after_discount_rm) }}</b>
                <s v-if="p.discount_pct > 0">{{ money(p.fee_rm) }}</s>
              </span>
              <Icon name="external" :size="14" class="jb-hrd__out" aria-hidden="true" />
              <span class="sr-only">(opens in a new tab)</span>
            </a>
          </li>
        </ul>
        <p class="jb-hrd__foot">Fees are from <a :href="HRD_LIST_URL" target="_blank" rel="noopener noreferrer">HRD Corp’s public course list</a>, read on {{ readOn }}. A course opens that list on the page it was found, so look for its name there. Fees change, so confirm with the provider.</p>
      </template>

      <p v-else class="jb-hrd__none">No HRD Corp-claimable course for {{ skill }} turned up in HRD Corp’s <a :href="HRD_LIST_URL" target="_blank" rel="noopener noreferrer">public list</a>. We don’t guess.</p>
    </div>
  </section>
</template>
