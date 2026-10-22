<script setup lang="ts">
import { computed } from 'vue';
import {
  Briefcase, Bug, Check, Cloud, Code2, Cpu, Database, GraduationCap, Layers, Search, Shield, Sparkles, Target,
  TrendingDown, TrendingUp, ArrowRight, Lock, Star, Trophy, BookOpen, User, Route, X, Flame, Upload, FileText,
  Play, RefreshCw, Megaphone, Users, Boxes, ClipboardList, ChartPie, Calculator, ShieldCheck, Landmark, Monitor,
  Headset, Palette, Sigma, Brain, ChartBar, Zap, Leaf, Factory, Microscope, HandHeart, Scale, Baby, School, PenTool,
  Languages, Activity, Stethoscope, Pill, ClipboardPlus, HeartHandshake, ShieldAlert, ChefHat, ShoppingBag, Receipt,
  Banknote, Headphones, Keyboard, Plug, Sun, Wrench, Wind, Truck, Package, Pencil,
} from 'lucide-vue-next';

const map = {
  briefcase: Briefcase, bug: Bug, check: Check, cloud: Cloud, code: Code2, cpu: Cpu, database: Database,
  grad: GraduationCap, layers: Layers, search: Search, shield: Shield, sparkles: Sparkles, target: Target,
  tdown: TrendingDown, tup: TrendingUp, arrow: ArrowRight, lock: Lock, star: Star, trophy: Trophy, book: BookOpen,
  user: User, route: Route, x: X, flame: Flame, upload: Upload, file: FileText, play: Play, refresh: RefreshCw,
  // Role icons (onet_roles.icon, migration 0006)
  megaphone: Megaphone, users: Users, boxes: Boxes, 'clipboard-list': ClipboardList, 'chart-pie': ChartPie,
  calculator: Calculator, 'shield-check': ShieldCheck, landmark: Landmark, monitor: Monitor, headset: Headset,
  palette: Palette, sigma: Sigma, brain: Brain, 'chart-bar': ChartBar, zap: Zap, leaf: Leaf, factory: Factory,
  microscope: Microscope, 'hand-heart': HandHeart, scale: Scale, baby: Baby, school: School, 'pen-tool': PenTool,
  languages: Languages, activity: Activity, stethoscope: Stethoscope, pill: Pill, 'clipboard-plus': ClipboardPlus,
  'heart-handshake': HeartHandshake, 'shield-alert': ShieldAlert, 'chef-hat': ChefHat, 'shopping-bag': ShoppingBag,
  receipt: Receipt, banknote: Banknote, headphones: Headphones, keyboard: Keyboard, plug: Plug, sun: Sun,
  wrench: Wrench, wind: Wind, truck: Truck, package: Package, pencil: Pencil,
} as const;

const props = withDefaults(defineProps<{ name: string; size?: number; stroke?: number }>(), { size: 20, stroke: 2.2 });
const comp = computed(() => map[props.name as keyof typeof map] ?? Sparkles);
</script>

<template>
  <component :is="comp" :size="size" :stroke-width="stroke" />
</template>
