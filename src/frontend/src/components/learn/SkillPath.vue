<script setup lang="ts">
import { computed } from 'vue';
import SkillNode from './SkillNode.vue';
import { useFit } from '../../composables/useFit';
import { groupStyle } from '../../data/skillGroups';
import { layoutGraph, type ResolvedSkill, type ResolvedUnit } from '../../learn/skillState';

const props = defineProps<{
  units: ResolvedUnit[];
  selectedId: string | null;
  /** The node that carries the START tag. */
  startId?: string | null;
  busyId?: string | null;
  label: (s: ResolvedSkill) => string;
  /** The skill's category: it picks the column, the shade and the icon. */
  kind: (s: ResolvedSkill) => string;
  /** The skill's demand-forecast direction, when one was matched. */
  forecast?: (s: ResolvedSkill) => 'rising' | 'falling' | 'flat' | null | undefined;
}>();
defineEmits<{ select: [skill: ResolvedSkill] }>();

const layout = computed(() => layoutGraph(props.units, props.kind));
const { el, scale } = useFit(() => layout.value.width);
</script>

<template>
  <div ref="el" class="jb jb-path" :style="{ height: layout.height * scale + 'px' }">
    <div class="jb-path__stage" :style="{ width: layout.width + 'px', height: layout.height + 'px', transform: `scale(${scale})` }">
      <svg class="jb-path__svg" :width="layout.width" :height="layout.height" :viewBox="`0 0 ${layout.width} ${layout.height}`" aria-hidden="true">
        <path v-for="(e, i) in layout.edges" :key="i" class="jb-path__line" :class="{ 'jb-path__line--done': e.done }" :d="e.d" />
      </svg>
      <template v-for="(it, i) in layout.items" :key="it.type === 'node' ? it.skill.id : `${it.type}-${i}`">
        <div v-if="it.type === 'unit'" class="jb-unit" :style="{ top: it.y + 'px', left: layout.width / 2 - 100 + 'px' }"><span>{{ it.label }}</span></div>
        <SkillNode
          v-else
          :style="{ left: it.x + 'px', top: it.y + 'px', width: it.w + 'px', '--i': it.k }"
          :name="label(it.skill)"
          stack
          :icon="groupStyle(kind(it.skill)).icon"
          :shade="groupStyle(kind(it.skill)).shade"
          :state="it.skill.state"
          :selected="selectedId === it.skill.id"
          :tag="it.skill.id === startId ? 'START' : null"
          :busy="busyId === it.skill.id"
          :forecast-direction="forecast?.(it.skill)"
          @select="$emit('select', it.skill)"
        />
      </template>
    </div>
  </div>
</template>
