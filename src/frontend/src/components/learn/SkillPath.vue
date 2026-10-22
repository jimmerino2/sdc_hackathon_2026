<script setup lang="ts">
import { computed } from 'vue';
import SkillNode from './SkillNode.vue';
import { useFit } from '../../composables/useFit';
import { CENTER_X, layoutPath, STAGE_W, trailPath, type ResolvedSkill, type ResolvedUnit } from '../../learn/skillState';

const props = defineProps<{
  units: ResolvedUnit[];
  selectedId: string | null;
  /** The node that carries the START tag. */
  startId?: string | null;
  busyId?: string | null;
  label: (s: ResolvedSkill) => string;
  kind: (s: ResolvedSkill) => string;
}>();
defineEmits<{ select: [skill: ResolvedSkill] }>();

const layout = computed(() => layoutPath(props.units));
const { el, scale } = useFit(STAGE_W);
</script>

<template>
  <div ref="el" class="jb jb-path" :style="{ height: layout.height * scale + 'px' }">
    <div class="jb-path__stage" :style="{ width: STAGE_W + 'px', height: layout.height + 'px', transform: `scale(${scale})` }">
      <svg class="jb-path__svg" :width="STAGE_W" :height="layout.height" :viewBox="`0 0 ${STAGE_W} ${layout.height}`" aria-hidden="true">
        <path class="jb-path__line" :d="trailPath(layout.pts)" />
      </svg>
      <template v-for="(it, i) in layout.items" :key="it.type === 'node' ? it.skill.id : `unit-${i}`">
        <div v-if="it.type === 'unit'" class="jb-unit" :style="{ top: it.y + 'px', left: CENTER_X - 100 + 'px' }"><span>{{ it.label }}</span></div>
        <SkillNode
          v-else
          :style="{ left: it.x + 'px', top: it.y + 'px', '--i': it.k }"
          :name="label(it.skill)"
          :kind="kind(it.skill)"
          :resources="it.skill.node.sources.length || (it.skill.node.source ? 1 : 0)"
          :state="it.skill.state"
          :selected="selectedId === it.skill.id"
          :tag="it.skill.id === startId ? 'START' : null"
          :busy="busyId === it.skill.id"
          @select="$emit('select', it.skill)"
        />
      </template>
    </div>
  </div>
</template>
