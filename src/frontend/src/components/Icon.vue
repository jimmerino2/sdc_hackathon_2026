<script setup lang="ts">
import { computed } from 'vue';
import {
  Briefcase, Bug, Check, Cloud, Code2, Cpu, Database, GraduationCap, Layers, Search, Shield, Sparkles, Target,
  TrendingDown, TrendingUp, ArrowRight, Lock, Star, Trophy, BookOpen, User, Route, X, Flame, Upload, FileText,
  Play,
} from 'lucide-vue-next';

const map = {
  briefcase: Briefcase, bug: Bug, check: Check, cloud: Cloud, code: Code2, cpu: Cpu, database: Database,
  grad: GraduationCap, layers: Layers, search: Search, shield: Shield, sparkles: Sparkles, target: Target,
  tdown: TrendingDown, tup: TrendingUp, arrow: ArrowRight, lock: Lock, star: Star, trophy: Trophy, book: BookOpen,
  user: User, route: Route, x: X, flame: Flame, upload: Upload, file: FileText, play: Play,
} as const;

const props = withDefaults(defineProps<{ name: string; size?: number; stroke?: number }>(), { size: 20, stroke: 2.2 });
const comp = computed(() => map[props.name as keyof typeof map] ?? Sparkles);
</script>

<template>
  <component :is="comp" :size="size" :stroke-width="stroke" />
</template>
