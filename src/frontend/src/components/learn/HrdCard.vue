<script setup lang="ts">
import { computed, ref } from 'vue';
import Icon from '../Icon.vue';
import type { Programme } from '../../api/hrd';

const props = defineProps<{
  /** null while loading; the card only shows once there is at least one course. */
  programmes: Programme[] | null;
}>();

/** Open by default, like the free and may-cost bands. */
const open = ref(true);
const count = computed(() => props.programmes?.length ?? 0);

const money = (n: number) => `RM ${n.toLocaleString('en-MY', { minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: 2 })}`;
</script>

<template>
  <section v-if="count" class="jb-res jb-hrd" aria-label="HRD Corp Verified courses">
    <button type="button" class="jb-res__head" :aria-expanded="open" aria-controls="hrd-body" @click="open = !open">
      <span class="jb-res__seal" aria-hidden="true"><Icon name="landmark" :size="16" :stroke="2.6" /></span>
      <span class="jb-res__titles">
        <span class="jb-res__eyebrow">Paid</span>
        <span class="jb-res__title">HRD Corp Verified</span>
      </span>
      <span class="jb-res__count">{{ count }}</span>
      <span class="jb-res__chev" aria-hidden="true"><Icon name="chevron" :size="16" :class="{ 'jb-collapse__icon--up': open }" /></span>
    </button>

    <div v-show="open" id="hrd-body" class="jb-res__body">
      <ul class="jb-hrd__list">
        <li v-for="p in programmes" :key="p.course_id">
          <a :href="p.source_url" target="_blank" rel="noopener noreferrer" :title="`Opens HRD Corp’s course list where ${p.course_name} is`">
            <span class="jb-hrd__main">
              <b>{{ p.course_name }}</b>
              <small>{{ p.training_provider }}</small>
              <span v-if="p.certification === 'Professional Certification'" class="jb-hrd__tags">
                <em class="jb-hrd__tag jb-hrd__tag--cert" title="Professional certification"><Icon name="grad" :size="12" :stroke="2.6" aria-hidden="true" /> Certification</em>
              </span>
              <span class="jb-hrd__price">
                <b>{{ p.fee_after_discount_rm === 0 ? 'RM 0' : money(p.fee_after_discount_rm) }}</b>
                <s v-if="p.discount_pct > 0">{{ money(p.fee_rm) }}</s>
                <em v-if="p.discount_pct > 0" class="jb-hrd__tag jb-hrd__off">-{{ p.discount_pct }}%</em>
              </span>
            </span>
            <Icon name="external" :size="14" class="jb-hrd__out" aria-hidden="true" />
            <span class="sr-only">(opens in a new tab)</span>
          </a>
        </li>
      </ul>
    </div>
  </section>
</template>
