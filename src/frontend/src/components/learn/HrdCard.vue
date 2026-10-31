<script setup lang="ts">
import { computed, ref } from 'vue';
import Icon from '../Icon.vue';
import { HRD_LIST_URL, type Programme } from '../../api/hrd';

const props = defineProps<{
  /** The skill's display name. */
  skill: string;
  /** null while loading. */
  programmes: Programme[] | null;
}>();

/** Closed by default; the free links come first and these cost money. */
const open = ref(false);
const count = computed(() => props.programmes?.length ?? 0);

const money = (n: number) => `RM ${n.toLocaleString('en-MY', { minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: 2 })}`;
</script>

<template>
  <section class="jb-res jb-hrd" aria-label="HRD Corp Verified courses">
    <button type="button" class="jb-res__head" :aria-expanded="open" aria-controls="hrd-body" @click="open = !open">
      <span class="jb-res__seal jb-hrd__seal" aria-hidden="true"><Icon name="landmark" :size="16" :stroke="2.3" /><i class="jb-hrd__verified"><Icon name="check" :size="10" :stroke="4" /></i></span>
      <span class="jb-res__titles">
        <span class="jb-res__eyebrow">Paid · employer claims the fee</span>
        <span class="jb-res__title">HRD Corp Verified</span>
      </span>
      <span v-if="programmes" class="jb-res__count">{{ count }} {{ count === 1 ? 'course' : 'courses' }}</span>
      <span class="jb-res__chev" aria-hidden="true"><Icon name="chevron" :size="16" :class="{ 'jb-collapse__icon--up': open }" /></span>
    </button>

    <div v-show="open" id="hrd-body" class="jb-res__body">
      <div v-if="programmes === null" class="jb-hrd__skel" aria-hidden="true"><span class="skel" /><span class="skel" /></div>

      <template v-else-if="programmes.length">
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
      </template>

      <p v-else class="jb-hrd__none">No HRD Corp-claimable course for {{ skill }} turned up in HRD Corp’s <a :href="HRD_LIST_URL" target="_blank" rel="noopener noreferrer">public list</a>. We don’t guess.</p>
    </div>
  </section>
</template>
