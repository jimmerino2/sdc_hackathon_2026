<script setup lang="ts">
/**
 * Robbee the Hornet Foreman: the challenges' boss. A red hornet in a cap, with a headset and a staff badge.
 * pose: idle, hit (eyes squeezed shut, shaking) or defeated (X eyes, tumbling over).
 */
withDefaults(defineProps<{ size?: number; bob?: boolean; pose?: 'idle' | 'hit' | 'defeated' }>(), { size: 160, bob: true, pose: 'idle' });
</script>

<template>
  <svg class="robbee" :class="[{ bob: bob && pose === 'idle' }, `pose-${pose}`]" :width="size" :height="size * 1.1" viewBox="0 0 200 220" role="img" aria-label="Robbee the Hornet Foreman">
    <defs>
      <clipPath id="robbee-body"><rect x="45" y="80" width="110" height="110" rx="30" /></clipPath>
    </defs>
    <!-- wings -->
    <ellipse cx="42" cy="128" rx="22" ry="36" transform="rotate(-14 42 128)" fill="#fff" stroke="#d9cfae" stroke-width="3" />
    <ellipse cx="158" cy="128" rx="22" ry="36" transform="rotate(14 158 128)" fill="#fff" stroke="#d9cfae" stroke-width="3" />
    <!-- antennae -->
    <path d="M84 74 L72 36 M116 74 L128 36" stroke="#1e1e1e" stroke-width="4" stroke-linecap="round" />
    <circle cx="72" cy="35" r="6" fill="#1e1e1e" /><circle cx="128" cy="35" r="6" fill="#1e1e1e" />
    <!-- stinger -->
    <path d="M91 186 L100 214 L109 186 Z" fill="#1e1e1e" />
    <!-- body and stripes -->
    <rect x="45" y="80" width="110" height="110" rx="30" fill="#d93a35" />
    <g clip-path="url(#robbee-body)" fill="#4a1616">
      <rect x="40" y="164" width="120" height="10" /><rect x="40" y="180" width="120" height="10" />
    </g>
    <!-- cap -->
    <path d="M47 104 C47 52 153 52 153 104 Z" fill="#1e1e1e" />
    <path d="M47 94 H153 V104 H47 Z" fill="#ffc107" />
    <path d="M138 96 C162 88 188 96 186 108 C172 112 152 108 138 104 Z" fill="#1e1e1e" />
    <circle cx="100" cy="66" r="4.5" fill="#ffc107" />
    <text x="100" y="89" text-anchor="middle" font-family="Nunito, sans-serif" font-weight="900" font-size="28" fill="#ffc107">R</text>
    <!-- face -->
    <path d="M128 110 L137 140" stroke="#8a1f1f" stroke-width="3" stroke-linecap="round" />
    <path d="M129 120 L136 118 M131 129 L138 127" stroke="#8a1f1f" stroke-width="2" stroke-linecap="round" />
    <path d="M66 116 L91 127 M134 116 L109 127" stroke="#1e1e1e" stroke-width="7" stroke-linecap="round" />
    <template v-if="pose === 'idle'">
      <circle cx="80" cy="135" r="9" fill="#1e1e1e" /><circle cx="120" cy="135" r="9" fill="#1e1e1e" />
      <circle cx="83" cy="132" r="3" fill="#fff" /><circle cx="123" cy="132" r="3" fill="#fff" />
    </template>
    <path v-else-if="pose === 'hit'" d="M71 127 L88 135 L71 143 M129 127 L112 135 L129 143" stroke="#1e1e1e" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round" />
    <path v-else d="M72 127 L88 143 M88 127 L72 143 M112 127 L128 143 M128 127 L112 143" stroke="#1e1e1e" stroke-width="6" fill="none" stroke-linecap="round" />
    <ellipse cx="64" cy="148" rx="8" ry="4.5" fill="#ff9a9a" opacity=".85" />
    <ellipse cx="136" cy="148" rx="8" ry="4.5" fill="#ff9a9a" opacity=".85" />
    <path d="M83 152 Q92 145 100 150 Q108 145 117 152 Q108 158 100 154 Q92 158 83 152 Z" fill="#1e1e1e" />
    <path v-if="pose === 'idle'" d="M92 163 Q100 158 108 163" stroke="#1e1e1e" stroke-width="3" fill="none" stroke-linecap="round" />
    <path v-else d="M91 164 Q100 173 109 164" stroke="#1e1e1e" stroke-width="3" fill="none" stroke-linecap="round" />
    <!-- headset -->
    <rect x="38" y="122" width="13" height="24" rx="5" fill="#1e1e1e" />
    <path d="M46 146 Q50 170 80 168" stroke="#1e1e1e" stroke-width="4" fill="none" stroke-linecap="round" />
    <circle cx="82" cy="168" r="4.5" fill="#1e1e1e" />
    <!-- staff badge -->
    <rect x="113" y="165" width="27" height="19" rx="3" fill="#fff" stroke="#1e1e1e" stroke-width="2" />
    <rect x="117" y="169" width="8" height="8" fill="#ff9800" />
    <rect x="128" y="170" width="8" height="2.5" fill="#cfcabb" /><rect x="128" y="175" width="8" height="2.5" fill="#cfcabb" />
  </svg>
</template>

<style scoped>
.robbee { display: block; overflow: visible; }
.robbee { transform-origin: 50% 70%; }
.bob { animation: robbee-bob 2.4s ease-in-out infinite; transform-origin: 50% 100%; }
.pose-hit { animation: robbee-hit .5s ease-out both; }
.pose-defeated { animation: robbee-fall 1.4s cubic-bezier(.4, 0, .6, 1) forwards; }
@keyframes robbee-hit {
  0% { transform: translateX(0) scale(1); filter: brightness(1); }
  15% { transform: translateX(-10px) rotate(-6deg) scale(.94); filter: brightness(2.2) saturate(.4); }
  35% { transform: translateX(9px) rotate(5deg); }
  60% { transform: translateX(-5px) rotate(-2deg); filter: brightness(1.1); }
  100% { transform: translateX(0) rotate(0); filter: brightness(1); }
}
@keyframes robbee-fall {
  0% { transform: translateY(0) rotate(0); }
  35% { transform: translateY(-18px) rotate(-14deg); }
  100% { transform: translateY(46px) rotate(98deg) scale(.92); }
}
@keyframes robbee-bob { 0%, 100% { transform: translateY(0) rotate(0); } 50% { transform: translateY(-4px) rotate(-2deg); } }
@media (prefers-reduced-motion: reduce) { .bob, .pose-hit { animation: none; } .pose-defeated { animation: none; transform: rotate(98deg) translateY(30px); } }
</style>
